import os
import pytest
from unittest.mock import patch

from core.config import Config, get_config


@pytest.fixture
def clean_config():
    """Returns a fresh Config instance with an empty cache."""
    return Config()


def test_config_get_from_keyring(clean_config):
    with patch("core.config.Config._from_keyring", return_value="keyring_value"):
        with patch.dict(os.environ, {}, clear=True):
            assert clean_config.get("SOME_KEY") == "keyring_value"


def test_config_get_from_env(clean_config):
    with patch("core.config.Config._from_keyring", return_value=""):
        with patch.dict(os.environ, {"SOME_KEY": "env_value"}):
            assert clean_config.get("SOME_KEY") == "env_value"


def test_config_get_missing_required(clean_config):
    with patch("core.config.Config._from_keyring", return_value=""):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Brak klucza: SOME_KEY"):
                clean_config.get("SOME_KEY", required=True)


def test_config_get_missing_optional(clean_config):
    with patch("core.config.Config._from_keyring", return_value=""):
        with patch.dict(os.environ, {}, clear=True):
            assert clean_config.get("SOME_KEY", required=False) == ""


def test_config_cache(clean_config):
    with patch("core.config.Config._from_keyring", return_value="first_call_value") as mock_keyring:
        with patch.dict(os.environ, {}, clear=True):
            # First call fetches from keyring
            assert clean_config.get("SOME_KEY") == "first_call_value"

            # Change the mock return value
            mock_keyring.return_value = "second_call_value"

            # Second call should still return the cached value
            assert clean_config.get("SOME_KEY") == "first_call_value"
            assert mock_keyring.call_count == 1


def test_properties_required(clean_config):
    with patch.object(clean_config, "get", return_value="mocked_key") as mock_get:
        assert clean_config.apikey == "mocked_key"
        mock_get.assert_called_with("APIKEY")

        assert clean_config.anthropic_key == "mocked_key"
        mock_get.assert_called_with("ANTHROPIC_API_KEY")


def test_properties_optional(clean_config):
    with patch.object(clean_config, "get", return_value="mocked_optional_key") as mock_get:
        assert clean_config.openai_key == "mocked_optional_key"
        mock_get.assert_called_with("OPENAI_API_KEY", required=False)

        assert clean_config.gemini_key == "mocked_optional_key"
        mock_get.assert_called_with("GEMINI_API_KEY", required=False)

        assert clean_config.langfuse_public_key == "mocked_optional_key"
        mock_get.assert_called_with("LANGFUSE_PUBLIC_KEY", required=False)

        assert clean_config.langfuse_secret_key == "mocked_optional_key"
        mock_get.assert_called_with("LANGFUSE_SECRET_KEY", required=False)

        assert clean_config.logfire_token == "mocked_optional_key"
        mock_get.assert_called_with("LOGFIRE_TOKEN", required=False)

        assert clean_config.vps_host == "mocked_optional_key"
        mock_get.assert_called_with("VPS_HOST", required=False)


def test_properties_env_direct(clean_config):
    with patch.dict(os.environ, {
        "LANGFUSE_HOST": "https://custom.langfuse.com",
        "LANGFUSE_TRACING_ENVIRONMENT": "prod",
        "HUB_BASE_URL": "https://custom.hub.com"
    }):
        assert clean_config.langfuse_host == "https://custom.langfuse.com"
        assert clean_config.langfuse_environment == "prod"
        assert clean_config.hub_base_url == "https://custom.hub.com"


def test_properties_env_direct_defaults(clean_config):
    with patch.dict(os.environ, {}, clear=True):
        assert clean_config.langfuse_host == "https://cloud.langfuse.com"
        assert clean_config.langfuse_environment == "dev"
        assert clean_config.hub_base_url == "https://hub.ag3nts.org"


def test_get_config_singleton():
    # Zwraca ten sam obiekt ze względu na cache
    get_config.cache_clear()
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2
    get_config.cache_clear()


def test_from_keyring_exception(clean_config):
    from unittest.mock import MagicMock
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = Exception("keyring error")
    with patch.dict("sys.modules", {"keyring": mock_keyring}):
        assert clean_config._from_keyring("ANY_KEY") == ""


def test_from_keyring_success(clean_config):
    from unittest.mock import MagicMock
    mock_keyring = MagicMock()
    mock_keyring.get_password.return_value = "secret_key"
    with patch.dict("sys.modules", {"keyring": mock_keyring}):
        assert clean_config._from_keyring("ANY_KEY") == "secret_key"
