"""
Testy tłumaczenia poziomów myślenia na kontrakty dostawców.

Regresja realna, nie hipotetyczna: `complete_structured()` hardkodował
`thinking_budget=0`, co dla `gemini-3.1-pro-preview` daje HTTP 400
("Budget 0 is invalid. This model only works in thinking mode.") — zmierzone realnym
wywołaniem 2026-08-23. Kontrakty `thinking_budget` i `thinking_level` wykluczają się.

Wszystkie wartości progowe i wspierane poziomy w tym pliku pochodzą z sond realnymi
wywołaniami (2026-08-23), nie z dokumentacji — tabela w `core/llm/thinking.py`.
"""

from __future__ import annotations

import pytest

from core.llm.adapters.gemini import GEMINI_MODELS, GeminiAdapter
from core.llm.thinking import (
    ANTHROPIC_MIN_BUDGET,
    GEMINI_25_MAX_BUDGET,
    THINKING_LEVELS,
    ThinkingNotSupported,
    anthropic_thinking,
    gemini_thinking,
    openai_reasoning_effort,
    validate,
)

PRO_PREVIEW = GEMINI_MODELS["premium"]["powerful"]
GEMINI_25 = GEMINI_MODELS["free"]["balanced"]
GEMINI_3X = GEMINI_MODELS["free"]["powerful"]


def _level_value(level) -> str:
    """SDK koeruje `"low"` do enuma `ThinkingLevel.LOW` — porównujemy po wartości."""
    return str(getattr(level, "value", level)).lower()


class TestLadder:
    def test_ladder_is_ordered_ascending(self):
        """Kolejność ma znaczenie — komunikaty błędów cytują drabinę w tej postaci."""
        assert THINKING_LEVELS == ("none", "minimal", "low", "medium", "high", "xhigh", "max")

    @pytest.mark.parametrize("bad", ["", "None", "LOW", "extra", "maksymalny", "1"])
    def test_validate_rejects_unknown_level(self, bad):
        with pytest.raises(ValueError, match="Nieznany poziom myślenia"):
            validate(bad)


class TestAnthropic:
    def test_none_disables_thinking(self):
        assert anthropic_thinking("none", max_tokens=1024) == {"type": "disabled"}

    def test_budget_is_percentage_of_max_tokens(self):
        """`medium` to 40% budżetu odpowiedzi."""
        cfg = anthropic_thinking("medium", max_tokens=10_000)
        assert cfg == {"type": "enabled", "budget_tokens": 4000}

    def test_budget_is_floored_at_api_minimum(self):
        """10% z 5000 to 500, a API wymaga >= 1024 — podłoga podnosi, nie przycina."""
        cfg = anthropic_thinking("minimal", max_tokens=5000)
        assert cfg["budget_tokens"] == ANTHROPIC_MIN_BUDGET

    def test_max_is_80_percent_not_100(self):
        """Model musi mieć z czego napisać odpowiedź po zakończeniu myślenia."""
        cfg = anthropic_thinking("max", max_tokens=10_000)
        assert cfg["budget_tokens"] == 8000

    def test_raises_when_max_tokens_too_small_to_fit_budget(self):
        """
        Przy domyślnym `max_tokens=1024` żaden poziom poza `none` nie jest osiągalny:
        podłoga budżetu to 1024, a API wymaga `max_tokens > budget_tokens`.
        Komunikat musi podać konkretną liczbę — samo „za mało" nie mówi ile trzeba.
        """
        with pytest.raises(ThinkingNotSupported, match="1025"):
            anthropic_thinking("low", max_tokens=1024)

    @pytest.mark.parametrize("level", [lvl for lvl in THINKING_LEVELS if lvl != "none"])
    def test_every_level_fits_in_a_large_budget(self, level):
        cfg = anthropic_thinking(level, max_tokens=100_000)
        assert cfg["type"] == "enabled"
        assert ANTHROPIC_MIN_BUDGET <= cfg["budget_tokens"] < 100_000


class TestOpenAI:
    @pytest.mark.parametrize("level", THINKING_LEVELS)
    def test_mapping_is_identity(self, level):
        """Drabina została celowo zapożyczona z `openai.types.shared.ReasoningEffort`."""
        assert openai_reasoning_effort(level) == level

    def test_matches_sdk_literal_exactly(self):
        """
        Gdyby OpenAI dołożyło albo usunęło poziom, ten test padnie i wymusi decyzję,
        zamiast pozwolić drabinie po cichu rozjechać się ze źródłem, z którego pochodzi.
        """
        from typing import get_args

        from openai.types.shared.reasoning_effort import ReasoningEffort

        sdk_levels = {a for a in get_args(get_args(ReasoningEffort)[0])}
        assert sdk_levels == set(THINKING_LEVELS)


class TestGemini:
    def test_25_family_uses_budget_not_level(self):
        cfg = gemini_thinking("medium", GEMINI_25, max_output_tokens=10_000)
        assert cfg.thinking_budget == 4000
        assert cfg.thinking_level is None

    def test_25_budget_capped_at_api_maximum(self):
        """Zmierzone: 24576 przechodzi, 30000 daje 400."""
        cfg = gemini_thinking("max", GEMINI_25, max_output_tokens=1_000_000)
        assert cfg.thinking_budget == GEMINI_25_MAX_BUDGET

    def test_3x_family_uses_level_not_budget(self):
        cfg = gemini_thinking("low", GEMINI_3X, max_output_tokens=8192)
        assert _level_value(cfg.thinking_level) == "low"
        assert cfg.thinking_budget is None

    def test_3x_none_uses_zero_budget(self):
        """
        Zaskoczenie zmierzone: rodzina 3.x przyjmuje `thinking_budget=0` mimo że steruje
        się ją poziomem — czyli `none` jest osiągalne, choć `thinking_level` go nie ma.
        """
        cfg = gemini_thinking("none", GEMINI_3X, max_output_tokens=8192)
        assert cfg.thinking_budget == 0
        assert cfg.thinking_level is None

    def test_pro_refuses_to_disable_thinking(self):
        """Sedno regresji z PR #77: ten model odrzuca zerowy budżet czterystką."""
        with pytest.raises(ThinkingNotSupported, match="thinking mode"):
            gemini_thinking("none", PRO_PREVIEW, max_output_tokens=8192)

    @pytest.mark.parametrize("level", ["minimal", "xhigh", "max"])
    def test_3x_rejects_levels_it_does_not_support(self, level):
        """
        `minimal` jest tu najważniejszy: **istnieje w enumie SDK**, ale modele odrzucają
        go czterystką („Thinking level MINIMAL is not supported"). Obecność w enumie nie
        oznacza wsparcia — bez tej bramki błąd wyszedłby dopiero z API.
        """
        with pytest.raises(ThinkingNotSupported, match="3.x nie wspiera"):
            gemini_thinking(level, GEMINI_3X, max_output_tokens=8192)

    def test_never_sets_both_across_whole_roster(self):
        """Zmieszanie obu kontraktów w jednym zapytaniu to 400 — sprawdzamy cały roster."""
        models = {m for tier in GEMINI_MODELS.values() for m in tier.values()}
        for model in models:
            for level in THINKING_LEVELS:
                try:
                    cfg = gemini_thinking(level, model, max_output_tokens=8192)
                except ThinkingNotSupported:
                    continue  # bramka zadziałała — to też poprawny wynik
                ustawiony_budzet = cfg.thinking_budget is not None
                ustawiony_poziom = cfg.thinking_level is not None
                assert ustawiony_budzet ^ ustawiony_poziom, f"{model} / {level}: oba albo żaden"


class TestAdapterWiring:
    @pytest.fixture
    def adapter_factory(self, monkeypatch):
        """Buduje GeminiAdapter bez sieci — `genai.Client` podmieniony na atrapę."""

        def _make(model: str) -> GeminiAdapter:
            from google import genai

            monkeypatch.setattr(genai, "Client", lambda **_kw: object())
            return GeminiAdapter(api_key="not-a-real-key", model=model)

        return _make

    def test_adapter_delegates_to_shared_module(self, adapter_factory):
        """Adapter nie powtarza logiki rodzin — pyta `thinking.py` i tyle."""
        cfg = adapter_factory(GEMINI_3X)._thinking_config("high", 8192)
        assert _level_value(cfg.thinking_level) == "high"

    def test_structured_output_defaults_to_no_thinking(self, adapter_factory):
        """
        Myślenie zjada tę samą pulę co `max_output_tokens`, więc przy structured output
        potrafiło uciąć JSON w połowie — domyślnie zostaje wyłączone.
        """
        cfg = adapter_factory(GEMINI_25)._thinking_config("none", 8192)
        assert cfg.thinking_budget == 0
