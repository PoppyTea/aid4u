"""Testy dla core/llm/factory.py — routing model→adapter i wybór tier dla Gemini."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.llm.factory import create_provider


def _fake_config(**overrides) -> MagicMock:
    cfg = MagicMock()
    cfg.gemini_key = overrides.get("gemini_key", "standard_key")
    cfg.gemini_key_premium = overrides.get("gemini_key_premium", "premium_key")
    cfg.anthropic_key = overrides.get("anthropic_key", "anthropic_key")
    cfg.openai_key = overrides.get("openai_key", "openai_key")
    # gemini_key_for_tier to prawdziwa metoda w Config (nie property) — MagicMock
    # domyślnie nie wie, że ma delegować do gemini_key/gemini_key_premium, więc
    # odtwarzamy tu jej rzeczywistą logikę.
    cfg.gemini_key_for_tier.side_effect = (
        lambda tier="standard": cfg.gemini_key_premium if tier == "premium" else cfg.gemini_key
    )
    return cfg


class TestGeminiTierRouting:
    def test_default_tier_uses_standard_key(self):
        cfg = _fake_config()
        with patch("core.llm.adapters.gemini.GeminiAdapter.__init__", return_value=None) as mock_init:
            create_provider("gemini-2.5-flash", cfg)
            mock_init.assert_called_once_with(api_key="standard_key", model="gemini-2.5-flash")

    def test_explicit_standard_tier_uses_standard_key(self):
        cfg = _fake_config()
        with patch("core.llm.adapters.gemini.GeminiAdapter.__init__", return_value=None) as mock_init:
            create_provider("gemini-2.5-flash", cfg, tier="standard")
            mock_init.assert_called_once_with(api_key="standard_key", model="gemini-2.5-flash")

    def test_premium_tier_uses_premium_key(self):
        cfg = _fake_config()
        with patch("core.llm.adapters.gemini.GeminiAdapter.__init__", return_value=None) as mock_init:
            create_provider("gemini-3.5-flash", cfg, tier="premium")
            mock_init.assert_called_once_with(api_key="premium_key", model="gemini-3.5-flash")

    def test_premium_tier_missing_key_raises(self):
        cfg = _fake_config(gemini_key_premium="")
        with pytest.raises(ValueError, match="GEMINI_API_KEY_PREMIUM"):
            create_provider("gemini-3.5-flash", cfg, tier="premium")

    def test_missing_standard_key_raises(self):
        cfg = _fake_config(gemini_key="")
        with pytest.raises(ValueError, match="GEMINI_API_KEY nie jest ustawiony"):
            create_provider("gemini-2.5-flash", cfg)


class TestTierIgnoredByOtherProviders:
    """tier dotyczy wyłącznie Gemini — inni providerzy mają jeden klucz, bez tier."""

    def test_anthropic_ignores_tier(self):
        cfg = _fake_config()
        with patch("core.llm.adapters.anthropic.AnthropicAdapter.__init__", return_value=None) as mock_init:
            create_provider("claude-haiku-4-5-20251001", cfg, tier="premium")
            mock_init.assert_called_once_with(api_key="anthropic_key", model="claude-haiku-4-5-20251001")

    def test_openai_ignores_tier(self):
        cfg = _fake_config()
        with patch("core.llm.adapters.openai.OpenAIAdapter.__init__", return_value=None) as mock_init:
            create_provider("gpt-5.4-nano", cfg, tier="premium")
            mock_init.assert_called_once_with(api_key="openai_key", model="gpt-5.4-nano")
