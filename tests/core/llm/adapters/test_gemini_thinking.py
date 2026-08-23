"""
Testy wyboru ThinkingConfig w adapterze Gemini wg rodziny modelu.

Regresja realna, nie hipotetyczna: `complete_structured()` hardkodował
`thinking_budget=0`, co dla `gemini-3.1-pro-preview` daje HTTP 400
("Budget 0 is invalid. This model only works in thinking mode.") — zmierzone realnym
wywołaniem 2026-08-23, gdy model wszedł do `GEMINI_MODELS["premium"]["powerful"]`.
Kontrakty `thinking_budget` i `thinking_level` wykluczają się wzajemnie.
"""

from __future__ import annotations

import pytest

from core.llm.adapters.gemini import GEMINI_MODELS, GeminiAdapter


def _is_low(level) -> bool:
    """SDK koeruje `"low"` do enuma `ThinkingLevel.LOW` — porównujemy po wartości."""
    return getattr(level, "value", level) == "LOW"


@pytest.fixture
def adapter_factory(monkeypatch):
    """Buduje GeminiAdapter bez dotykania sieci — genai.Client jest podmieniony na atrapę."""

    def _make(model: str) -> GeminiAdapter:
        from google import genai

        monkeypatch.setattr(genai, "Client", lambda **_kw: object())
        return GeminiAdapter(api_key="not-a-real-key", model=model)

    return _make


class TestThinkingConfigByModelFamily:
    def test_gemini_25_uses_thinking_budget(self, adapter_factory):
        """Rodzina 2.5 wyłącza myślenie budżetem zerowym — kontrakt sprzed rodziny 3.x."""
        cfg = adapter_factory("gemini-2.5-flash")._thinking_config()
        assert cfg.thinking_budget == 0
        assert cfg.thinking_level is None

    def test_gemini_3x_uses_thinking_level(self, adapter_factory):
        """Rodzina 3.x oczekuje `thinking_level`; budżet MUSI zostać pusty."""
        cfg = adapter_factory("gemini-3.7-flash")._thinking_config()
        assert _is_low(cfg.thinking_level)
        assert cfg.thinking_budget is None

    def test_pro_preview_never_gets_zero_budget(self, adapter_factory):
        """Sedno regresji: ten model odrzuca `thinking_budget=0` z HTTP 400."""
        cfg = adapter_factory(GEMINI_MODELS["premium"]["powerful"])._thinking_config()
        assert cfg.thinking_budget is None
        assert _is_low(cfg.thinking_level)

    def test_never_sets_both(self, adapter_factory):
        """Zmieszanie obu w jednym zapytaniu to 400 — sprawdzamy cały roster."""
        models = {m for tier in GEMINI_MODELS.values() for m in tier.values()}
        for model in models:
            cfg = adapter_factory(model)._thinking_config()
            assert (cfg.thinking_budget is None) != (cfg.thinking_level is None), model
