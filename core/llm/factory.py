"""
Factory pattern — tworzy właściwy adapter na podstawie nazwy modelu.

⚠️  DOMYŚLNY MODEL PROJEKTU: gemini-2.5-flash
    Eskalacja: Gemini (standard→premium) → OpenAI → Anthropic (patrz strategy/llm-selection.md).

    Dopuszczalne identyfikatory NIE są wypisane w tym pliku — źródłem prawdy są rostery
    w adapterach (`ANTHROPIC_MODELS`, `OPENAI_MODELS`, `GEMINI_MODELS`), a `_check_model()`
    niżej je egzekwuje. Lista w dwóch miejscach rozjeżdża się po cichu; lista w jednym,
    sprawdzana przy konstrukcji, nie ma jak.

Mapowanie prefixów (router):
    claude-*                      → AnthropicAdapter
    gemini-*                      → GeminiAdapter
    gpt-* / o1-* / o3-* / o4-*   → OpenAIAdapter
    openrouter/*                  → OpenRouterAdapter (bez rostera — adapter niezaimplementowany,
                                    patrz AID-61; walidacja modelu go nie dotyczy)

Tier (tylko Gemini):
    Free i paid tier Gemini API są związane z osobnymi projektami Google Cloud
    (billing wyłączony / włączony) — jeden klucz API obsługuje tylko jeden tier.
    Stąd dwa osobne klucze (GEMINI_API_KEY / GEMINI_API_KEY_PREMIUM) i parametr
    `tier`. Pozostali providerzy (OpenAI, Anthropic) mają jeden klucz — nie mają
    koncepcji tier w tym projekcie, więc `tier` jest dla nich no-opem.
    Decyzja o wyborze klucza żyje TYLKO tutaj — adaptery o tier nic nie wiedzą.
"""

from __future__ import annotations

from typing import Any

from core.config import Config
from core.llm.base import LLMProvider


def _allowed_ids(roster: dict[str, Any]) -> set[str]:
    """
    Spłaszcza słownik modeli providera do zbioru dopuszczalnych identyfikatorów.

    Przyjmuje oba kształty rosterów: płaski (`ANTHROPIC_MODELS`, `OPENAI_MODELS`) i
    zagnieżdżony po tierze rozliczeniowym (`GEMINI_MODELS`). Sprawdzamy przynależność
    wartości, nie ścieżkę do niej, więc różnica kształtów nie ma tu znaczenia.
    """
    ids: set[str] = set()
    for value in roster.values():
        if isinstance(value, dict):
            ids.update(value.values())
        else:
            ids.add(value)
    return ids


def _check_model(model: str, roster: dict[str, Any], provider: str, allow_unknown: bool) -> None:
    """
    Odrzuca identyfikator modelu spoza rostera providera.

    Bariera antyhalucynacyjna: modele z korpusu treningowego (`gpt-4o`, `gemini-1.5-pro`,
    `claude-3-*`) wchodzą agentom pod palce odruchowo, a sam prefix ich nie odsiewa —
    `gemini-1.5-pro` przechodzi jako poprawny `gemini-*` i martwe ID trafia do API, gdzie
    daje błąd kilkanaście sekund później, opakowany przez SDK i bez wskazania przyczyny.
    Tutaj pada natychmiast, z listą tego, co wolno.

    `allow_unknown=True` przepuszcza wszystko — furtka na model nowszy niż roster.
    Jej użycie jest sygnałem, że roster w adapterze wymaga uzupełnienia.
    """
    if allow_unknown:
        return
    allowed = _allowed_ids(roster)
    if model not in allowed:
        raise ValueError(
            f"Nieznany model {provider}: '{model}'. "
            f"Dopuszczalne: {', '.join(sorted(allowed))}. "
            "Jeśli to nowy model, dopisz go do rostera w adapterze albo użyj "
            "--allow-unknown-model (allow_unknown_model=True)."
        )


def create_provider(
    model: str,
    config: Config,
    *,
    tier: str = "standard",
    allow_unknown_model: bool = False,
) -> LLMProvider:
    """
    Fabryka adapterów. Wywołaj przez LLMClient, nie bezpośrednio.

    Args:
        model: Pełna nazwa modelu, np. 'gemini-2.5-flash'
        config: Singleton konfiguracji z kluczami API
        tier: 'standard' (domyślny, darmowy) lub 'premium' (płatny) — dotyczy
            wyłącznie modeli gemini-*, ignorowane przez pozostałych providerów.
        allow_unknown_model: pomija sprawdzenie modelu wobec rostera adaptera.
            Domyślnie `False` — patrz `_check_model()`.
    """
    model_lower = model.lower()

    if model_lower.startswith("claude"):
        from core.llm.adapters.anthropic import ANTHROPIC_MODELS, AnthropicAdapter

        _check_model(model, ANTHROPIC_MODELS, "Anthropic", allow_unknown_model)
        return AnthropicAdapter(api_key=config.anthropic_key, model=model)

    if model_lower.startswith(("gpt-", "o1-", "o3-", "o4-", "o3", "o4")):
        from core.llm.adapters.openai import OPENAI_MODELS, OpenAIAdapter

        if not config.openai_key:
            raise ValueError("OPENAI_API_KEY nie jest ustawiony")
        _check_model(model, OPENAI_MODELS, "OpenAI", allow_unknown_model)
        return OpenAIAdapter(api_key=config.openai_key, model=model)

    if model_lower.startswith("gemini"):
        from core.llm.adapters.gemini import GEMINI_MODELS, GeminiAdapter

        api_key = config.gemini_key_for_tier(tier)
        if not api_key:
            key_name = "GEMINI_API_KEY_PREMIUM" if tier == "premium" else "GEMINI_API_KEY"
            raise ValueError(f"{key_name} nie jest ustawiony (tier='{tier}')")
        _check_model(model, GEMINI_MODELS, "Gemini", allow_unknown_model)
        return GeminiAdapter(api_key=api_key, model=model)

    if model_lower.startswith("openrouter/"):
        from core.llm.adapters.openrouter import OpenRouterAdapter

        if not config.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY nie jest ustawiony")
        return OpenRouterAdapter(api_key=config.openrouter_key, model=model)

    raise ValueError(
        f"Nieznany prefix modelu: '{model}'. "
        "Obsługiwane: claude-*, gemini-*, gpt-*, o1-*, o3-*, o4-*, openrouter/*"
    )
