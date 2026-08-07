import os
import pytest
from unittest.mock import patch, MagicMock

import keyring
import keyring.errors

import core.secrets as secrets_module
from core.secrets import SecretsManager, get_secrets, default_keys


@pytest.fixture
def secrets_manager():
    return SecretsManager("test_service")


# Reset autouse dla _keyring_unavailable_until żyje w repo-root conftest.py —
# obejmuje całe tests/ + tasks/, nie tylko ten plik (patrz jego docstring).


def test_get_from_keyring(secrets_manager):
    with patch("keyring.get_password", return_value="secret_key") as mock_get:
        assert secrets_manager.get("MY_KEY") == "secret_key"
        mock_get.assert_called_once_with("test_service", "MY_KEY")


def test_get_from_env(secrets_manager):
    with patch("keyring.get_password", return_value=None):
        with patch.dict(os.environ, {"MY_KEY": "env_secret"}):
            assert secrets_manager.get("MY_KEY") == "env_secret"


def test_get_keyring_exception_fallback_to_env(secrets_manager):
    with patch("keyring.get_password", side_effect=Exception("keyring failed")):
        with patch.dict(os.environ, {"MY_KEY": "env_fallback"}):
            assert secrets_manager.get("MY_KEY") == "env_fallback"


def test_get_not_found_not_required(secrets_manager):
    with patch("keyring.get_password", return_value=None):
        with patch.dict(os.environ, {}, clear=True):
            assert secrets_manager.get("MISSING_KEY") is None


def test_get_not_found_required(secrets_manager):
    with patch("keyring.get_password", return_value=None):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Secret not found: MISSING_KEY"):
                secrets_manager.get("MISSING_KEY", required=True)


def test_set(secrets_manager):
    with patch("keyring.set_password") as mock_set:
        secrets_manager.set("NEW_KEY", "new_value")
        mock_set.assert_called_once_with("test_service", "NEW_KEY", "new_value")


def test_delete_success(secrets_manager):
    with patch("keyring.delete_password") as mock_delete:
        secrets_manager.delete("KEY_TO_DELETE")
        mock_delete.assert_called_once_with("test_service", "KEY_TO_DELETE")


def test_delete_not_found(secrets_manager):
    with patch("keyring.delete_password", side_effect=keyring.errors.PasswordDeleteError):
        # Should not raise exception
        secrets_manager.delete("MISSING_KEY")


def test_list(secrets_manager):
    def mock_get_password(service, key):
        if key == "EXISTING_KEY":
            return "value"
        elif key == "ERROR_KEY":
            raise Exception("error")
        return None

    with patch("keyring.get_password", side_effect=mock_get_password):
        result = secrets_manager.list(["EXISTING_KEY", "MISSING_KEY", "ERROR_KEY"])
        assert result == {"EXISTING_KEY": True, "MISSING_KEY": False, "ERROR_KEY": False}


def test_info(secrets_manager):
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "MockKeyringBackend"

    with patch("keyring.get_keyring", return_value=mock_backend):
        with patch.object(secrets_manager, "list", return_value={"A": True}):
            info = secrets_manager.info()
            assert info["backend"] == "MockKeyringBackend"
            assert info["service"] == "test_service"
            assert info["available_secrets"] == {"A": True}


def test_get_secrets_singleton():
    get_secrets.cache_clear()
    sm1 = get_secrets()
    sm2 = get_secrets()
    assert sm1 is sm2
    assert sm1.service == "aid4u"
    get_secrets.cache_clear()


def test_get_from_env_file_fallback(secrets_manager):
    # Test step 3 fallback (it uses os.getenv again currently)
    with patch("keyring.get_password", return_value=None):

        def mock_getenv(k, default=None):
            if k == "MY_KEY":
                return "env_file_secret"
            return None

        with patch("os.getenv", side_effect=mock_getenv):
            assert secrets_manager.get("MY_KEY") == "env_file_secret"


class TestKeyringTimeoutCircuitBreaker:
    """core.secrets._keyring_get_with_timeout — timeout + circuit breaker.

    _KEYRING_TIMEOUT_SECONDS/_KEYRING_BACKOFF_SECONDS są monkeypatchowane do
    milisekund — te testy weryfikują logikę, nie czekają na prawdziwe sekundy.
    """

    def _hang_forever(self, *_args, **_kwargs):
        import time as _time

        _time.sleep(10)  # dłużej niż jakikolwiek testowy timeout; wątek to daemon

    def test_timeout_raises_and_falls_back_to_env(self, secrets_manager, monkeypatch):
        monkeypatch.setattr(secrets_module, "_KEYRING_TIMEOUT_SECONDS", 0.05)
        with patch("keyring.get_password", side_effect=self._hang_forever):
            with patch.dict(os.environ, {"MY_KEY": "env_fallback"}):
                assert secrets_manager.get("MY_KEY") == "env_fallback"

    def test_timeout_trips_breaker_and_skips_next_keyring_call(self, secrets_manager, monkeypatch):
        monkeypatch.setattr(secrets_module, "_KEYRING_TIMEOUT_SECONDS", 0.05)
        monkeypatch.setattr(secrets_module, "_KEYRING_BACKOFF_SECONDS", 60.0)

        with patch("keyring.get_password", side_effect=self._hang_forever) as mock_get:
            with patch.dict(os.environ, {"MY_KEY": "env_fallback", "ANOTHER_KEY": "env_fallback2"}):
                secrets_manager.get("MY_KEY")  # trips the breaker
                assert secrets_manager.get("ANOTHER_KEY") == "env_fallback2"

        # Drugie wywołanie (inny klucz!) nie powinno w ogóle odpalić nowego wątku/
        # keyring.get_password — breaker aktywny globalnie, od razu fallback do env.
        mock_get.assert_called_once()

    def test_breaker_resets_after_backoff_window_expires(self, secrets_manager, monkeypatch):
        monkeypatch.setattr(secrets_module, "_KEYRING_TIMEOUT_SECONDS", 0.05)
        monkeypatch.setattr(secrets_module, "_KEYRING_BACKOFF_SECONDS", 0.0)

        with patch("keyring.get_password", side_effect=self._hang_forever) as mock_get:
            with patch.dict(os.environ, {"MY_KEY": "env_fallback"}):
                secrets_manager.get("MY_KEY")  # trips the breaker, backoff window = 0s
                secrets_manager.get("ANOTHER_KEY")  # window already elapsed, retries keyring

        assert mock_get.call_count == 2
