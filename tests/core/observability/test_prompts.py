"""
Testy rejestru promptów (`core/observability/prompts.py`).

Kontrakt do pilnowania: jednostronna synchronizacja kod→Langfuse (push tylko gdy
treść się zmieniła, nigdy odwrotnie) i "observability nigdy nie blokuje flagi" —
każdy błąd (brak kluczy, sieć, wyjątek SDK) musi kończyć się fallbackiem, nie
wyjątkiem propagującym się do wywołującego zadania.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from core.observability import prompts as prompts_module
from core.observability.prompts import PromptRef, get_prompt_ref, sync_prompt


@pytest.fixture(autouse=True)
def _isolate_module_state(tmp_path, monkeypatch):
    """Każdy test dostaje własny plik stanu i pusty rejestr referencji w procesie —
    inaczej testy zanieczyszczałyby się nawzajem przez moduł-level `_prompt_refs`."""
    monkeypatch.setattr(prompts_module, "_STATE_FILE", tmp_path / ".langfuse-prompt-state.json")
    prompts_module._prompt_refs.clear()
    yield
    prompts_module._prompt_refs.clear()


def _configured_config(*, public_key: str = "pub", secret_key: str = "sec") -> MagicMock:
    cfg = MagicMock()
    cfg.langfuse_public_key = public_key
    cfg.langfuse_secret_key = secret_key
    return cfg


def test_no_langfuse_keys_returns_fallback_without_touching_network():
    with patch("core.config.get_config", return_value=_configured_config(public_key="", secret_key="")):
        ref = sync_prompt("my-prompt", "treść promptu")

    assert ref == PromptRef(name="my-prompt", version=None, client=None, is_fallback=True)


def test_first_sync_pushes_prompt_and_caches_ref():
    created = MagicMock(version=1)
    prompt_client = MagicMock()
    langfuse_client = MagicMock()
    langfuse_client.create_prompt.return_value = created
    langfuse_client.get_prompt.return_value = prompt_client

    with (
        patch("core.config.get_config", return_value=_configured_config()),
        patch("langfuse.get_client", return_value=langfuse_client),
    ):
        ref = sync_prompt("my-prompt", "treść v1", tags=["agent-template"])

    langfuse_client.create_prompt.assert_called_once_with(
        name="my-prompt", prompt="treść v1", labels=["production"], tags=["agent-template"], type="text"
    )
    assert ref.name == "my-prompt"
    assert ref.version == 1
    assert ref.client is prompt_client
    assert ref.is_fallback is False


def test_unchanged_content_skips_push_but_still_fetches_client():
    """Jednostronna synchronizacja: push TYLKO gdy treść się zmieniła. Referencję do
    podpięcia pod generację i tak trzeba dociągnąć, bo obiekt klienta nie przeżywa
    między procesami (stan na dysku trzyma tylko hash+wersję, nie sam obiekt SDK)."""
    langfuse_client = MagicMock()
    langfuse_client.create_prompt.return_value = MagicMock(version=1)
    langfuse_client.get_prompt.return_value = MagicMock()

    with (
        patch("core.config.get_config", return_value=_configured_config()),
        patch("langfuse.get_client", return_value=langfuse_client),
    ):
        sync_prompt("my-prompt", "treść v1")
        langfuse_client.create_prompt.reset_mock()

        ref = sync_prompt("my-prompt", "treść v1")  # identyczna treść, drugi proces/run

    langfuse_client.create_prompt.assert_not_called()
    langfuse_client.get_prompt.assert_called_with(name="my-prompt", version=1, type="text")
    assert ref.version == 1
    assert ref.is_fallback is False


def test_changed_content_pushes_new_version():
    langfuse_client = MagicMock()
    langfuse_client.create_prompt.side_effect = [MagicMock(version=1), MagicMock(version=2)]
    langfuse_client.get_prompt.return_value = MagicMock()

    with (
        patch("core.config.get_config", return_value=_configured_config()),
        patch("langfuse.get_client", return_value=langfuse_client),
    ):
        sync_prompt("my-prompt", "treść v1")
        ref = sync_prompt("my-prompt", "treść v2 — inna")

    assert langfuse_client.create_prompt.call_count == 2
    assert ref.version == 2


def test_state_file_persists_content_hash_and_version(tmp_path):
    langfuse_client = MagicMock()
    langfuse_client.create_prompt.return_value = MagicMock(version=3)
    langfuse_client.get_prompt.return_value = MagicMock()

    with (
        patch("core.config.get_config", return_value=_configured_config()),
        patch("langfuse.get_client", return_value=langfuse_client),
    ):
        sync_prompt("my-prompt", "treść")

    state = json.loads(prompts_module._STATE_FILE.read_text(encoding="utf-8"))
    assert state["my-prompt"]["version"] == 3
    assert len(state["my-prompt"]["content_hash"]) == 64  # sha256 hex digest


def test_sdk_exception_returns_fallback_not_raises():
    with (
        patch("core.config.get_config", return_value=_configured_config()),
        patch("langfuse.get_client", side_effect=RuntimeError("langfuse down")),
    ):
        ref = sync_prompt("my-prompt", "treść")

    assert ref.is_fallback is True
    assert ref.client is None


def test_get_prompt_ref_returns_ref_synced_earlier_in_process():
    langfuse_client = MagicMock()
    langfuse_client.create_prompt.return_value = MagicMock(version=1)
    langfuse_client.get_prompt.return_value = MagicMock()

    with (
        patch("core.config.get_config", return_value=_configured_config()),
        patch("langfuse.get_client", return_value=langfuse_client),
    ):
        synced = sync_prompt("my-prompt", "treść")

    assert get_prompt_ref("my-prompt") is synced


def test_get_prompt_ref_returns_none_for_unknown_name():
    assert get_prompt_ref("never-synced") is None
