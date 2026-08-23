"""Testy dla core/llm/factory.py — routing model→adapter i wybór tier dla Gemini."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.llm.factory import create_provider


def _fake_config(**overrides) -> MagicMock:
    cfg = MagicMock()
    cfg.gemini_key = overrides.get("gemini_key", "free_key")
    cfg.gemini_key_premium = overrides.get("gemini_key_premium", "premium_key")
    cfg.anthropic_key = overrides.get("anthropic_key", "anthropic_key")
    cfg.openai_key = overrides.get("openai_key", "openai_key")
    cfg.openrouter_key = overrides.get("openrouter_key", "openrouter_key")
    # gemini_key_for_tier to prawdziwa metoda w Config (nie property) — MagicMock
    # domyślnie nie wie, że ma delegować do gemini_key/gemini_key_premium, więc
    # odtwarzamy tu jej rzeczywistą logikę.
    cfg.gemini_key_for_tier.side_effect = lambda tier="free": (
        cfg.gemini_key_premium if tier == "premium" else cfg.gemini_key
    )
    return cfg


class TestGeminiTierRouting:
    def test_default_tier_uses_free_key(self):
        cfg = _fake_config()
        with patch(
            "core.llm.adapters.gemini.GeminiAdapter.__init__", return_value=None
        ) as mock_init:
            create_provider("gemini-2.5-flash", cfg)
            mock_init.assert_called_once_with(api_key="free_key", model="gemini-2.5-flash")

    def test_explicit_free_tier_uses_free_key(self):
        cfg = _fake_config()
        with patch(
            "core.llm.adapters.gemini.GeminiAdapter.__init__", return_value=None
        ) as mock_init:
            create_provider("gemini-2.5-flash", cfg, tier="free")
            mock_init.assert_called_once_with(api_key="free_key", model="gemini-2.5-flash")

    def test_premium_tier_uses_premium_key(self):
        cfg = _fake_config()
        with patch(
            "core.llm.adapters.gemini.GeminiAdapter.__init__", return_value=None
        ) as mock_init:
            create_provider("gemini-3.7-flash", cfg, tier="premium")
            mock_init.assert_called_once_with(api_key="premium_key", model="gemini-3.7-flash")

    def test_premium_tier_missing_key_raises(self):
        cfg = _fake_config(gemini_key_premium="")
        with pytest.raises(ValueError, match="GEMINI_API_KEY_PREMIUM"):
            create_provider("gemini-3.7-flash", cfg, tier="premium")

    def test_missing_free_key_raises(self):
        cfg = _fake_config(gemini_key="")
        with pytest.raises(ValueError, match="GEMINI_API_KEY nie jest ustawiony"):
            create_provider("gemini-2.5-flash", cfg)


class TestOpenRouterRouting:
    def test_openrouter_missing_key_raises(self):
        cfg = _fake_config(openrouter_key="")
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY nie jest ustawiony"):
            create_provider("openrouter/meta-llama/llama-3-8b", cfg)


class TestTierIgnoredByOtherProviders:
    """tier dotyczy wyłącznie Gemini — inni providerzy mają jeden klucz, bez tier."""

    def test_anthropic_ignores_tier(self):
        cfg = _fake_config()
        with patch(
            "core.llm.adapters.anthropic.AnthropicAdapter.__init__", return_value=None
        ) as mock_init:
            create_provider("claude-haiku-4-5-20251001", cfg, tier="premium")
            mock_init.assert_called_once_with(
                api_key="anthropic_key", model="claude-haiku-4-5-20251001"
            )

    def test_openai_ignores_tier(self):
        cfg = _fake_config()
        with patch(
            "core.llm.adapters.openai.OpenAIAdapter.__init__", return_value=None
        ) as mock_init:
            create_provider("gpt-5.6-luna", cfg, tier="premium")
            mock_init.assert_called_once_with(api_key="openai_key", model="gpt-5.6-luna")

    def test_openrouter_ignores_tier(self):
        cfg = _fake_config()
        with patch(
            "core.llm.adapters.openrouter.OpenRouterAdapter.__init__", return_value=None
        ) as mock_init:
            create_provider("openrouter/meta-llama/llama-3-8b", cfg, tier="premium")
            mock_init.assert_called_once_with(
                api_key="openrouter_key", model="openrouter/meta-llama/llama-3-8b"
            )


class TestModelAllowlist:
    """
    Bariera antyhalucynacyjna: sam prefix nie odsiewa martwych ID.

    `gemini-1.5-pro` przechodzi router jako poprawny `gemini-*`, więc bez tej warstwy
    trafiłby do API i dał błąd dopiero po kilkunastu sekundach, opakowany przez SDK.
    Regresja realna, nie hipotetyczna — domyślnym modelem repo był kiedyś nieistniejący
    `gemini-3.1-flash` (patrz docstring `GeminiAdapter`).
    """

    def test_hallucinated_gemini_model_rejected(self):
        """Martwe ID przechodzi router jako poprawny `gemini-*` — musi paść tutaj."""
        cfg = _fake_config()
        with pytest.raises(ValueError, match="Nieznany model Gemini"):
            create_provider("gemini-1.5-pro", cfg)

    def test_hallucinated_openai_model_rejected(self):
        """`gpt-4o` to najczęstszy odruch z korpusu treningowego."""
        cfg = _fake_config()
        with pytest.raises(ValueError, match="Nieznany model OpenAI"):
            create_provider("gpt-4o", cfg)

    def test_hallucinated_anthropic_model_rejected(self):
        """Rodzina claude-3 zniknęła z drabiny, ale nie z pamięci modeli."""
        cfg = _fake_config()
        with pytest.raises(ValueError, match="Nieznany model Anthropic"):
            create_provider("claude-3-5-sonnet-20241022", cfg)

    def test_error_lists_allowed_ids(self):
        """Komunikat musi podać poprawną odpowiedź, nie tylko odmówić."""
        cfg = _fake_config()
        with pytest.raises(ValueError, match="Nieznany model OpenAI") as exc:
            create_provider("gpt-4o", cfg)
        assert "gpt-5.6-luna" in str(exc.value)
        assert "gpt-5.6-sol" in str(exc.value)

    def test_allow_unknown_model_bypasses_check(self):
        """Furtka na model nowszy niż roster."""
        cfg = _fake_config()
        with patch(
            "core.llm.adapters.gemini.GeminiAdapter.__init__", return_value=None
        ) as mock_init:
            create_provider("gemini-9.9-flash", cfg, allow_unknown_model=True)
            mock_init.assert_called_once_with(api_key="free_key", model="gemini-9.9-flash")

    def test_premium_only_model_passes_on_free_tier(self):
        """
        Roster jest sprawdzany jako jeden zbiór, nie per tier rozliczeniowy.

        Tier decyduje o KLUCZU (osobny projekt Google Cloud), nie o tym, czy model
        istnieje. Rozdzielanie allowlisty per tier dałoby fałszywe odrzucenia przy
        ręcznym `--model`, a prawdziwy błąd (brak quoty) i tak przychodzi z API.
        """
        cfg = _fake_config()
        with patch(
            "core.llm.adapters.gemini.GeminiAdapter.__init__", return_value=None
        ) as mock_init:
            create_provider("gemini-3.7-flash", cfg)
            mock_init.assert_called_once_with(api_key="free_key", model="gemini-3.7-flash")

    def test_unknown_prefix_message_unchanged(self):
        """Nieznany prefix to inna klasa błędu niż nieznany model — nie mieszać."""
        cfg = _fake_config()
        with pytest.raises(ValueError, match="Nieznany prefix modelu"):
            create_provider("llama-3-70b", cfg)

    def test_openrouter_skips_model_check(self):
        """OpenRouter nie ma rostera — adapter niezaimplementowany (AID-61)."""
        cfg = _fake_config()
        with patch(
            "core.llm.adapters.openrouter.OpenRouterAdapter.__init__", return_value=None
        ) as mock_init:
            create_provider("openrouter/cokolwiek/model", cfg)
            mock_init.assert_called_once_with(
                api_key="openrouter_key", model="openrouter/cokolwiek/model"
            )
