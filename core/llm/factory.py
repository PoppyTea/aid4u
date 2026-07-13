"""
Factory pattern — tworzy właściwy adapter na podstawie nazwy modelu.

⚠️  DOMYŚLNY MODEL PROJEKTU: gemini-2.5-flash
    NIE zmieniaj domyślnych na gpt-4o, gpt-4o-mini ani modele gemini-2.0/1.5 (wycofane).
    Eskalacja: Gemini (standard→premium) → OpenAI → Anthropic
    Szczegóły: strategy/llm-models.md i strategy/llm-selection.md

Mapowanie prefixów (router):
    claude-*                      → AnthropicAdapter
    gemini-*                      → GeminiAdapter  (gemini-2.5-*, gemini-3-*, gemini-3.1-*, gemini-3.5-*)
    gpt-* / o1-* / o3-* / o4-*   → OpenAIAdapter  (gpt-5.4-*, gpt-5-*, gpt-4.1-*, o4-mini...)
    openrouter/*                  → OpenRouterAdapter (TODO)

Tier (tylko Gemini):
    Free i paid tier Gemini API są związane z osobnymi projektami Google Cloud
    (billing wyłączony / włączony) — jeden klucz API obsługuje tylko jeden tier.
    Stąd dwa osobne klucze (GEMINI_API_KEY / GEMINI_API_KEY_PREMIUM) i parametr
    `tier`. Pozostali providerzy (OpenAI, Anthropic) mają jeden klucz — nie mają
    koncepcji tier w tym projekcie, więc `tier` jest dla nich no-opem.
    Decyzja o wyborze klucza żyje TYLKO tutaj — adaptery o tier nic nie wiedzą.
"""
from __future__ import annotations

from core.config import Config
from core.llm.base import LLMProvider


def create_provider(model: str, config: Config, *, tier: str = "standard") -> LLMProvider:
    """
    Fabryka adapterów. Wywołaj przez LLMClient, nie bezpośrednio.

    Args:
        model: Pełna nazwa modelu, np. 'gemini-2.5-flash'
        config: Singleton konfiguracji z kluczami API
        tier: 'standard' (domyślny, darmowy) lub 'premium' (płatny) — dotyczy
            wyłącznie modeli gemini-*, ignorowane przez pozostałych providerów.
    """
    model_lower = model.lower()

    if model_lower.startswith("claude"):
        from core.llm.adapters.anthropic import AnthropicAdapter
        return AnthropicAdapter(api_key=config.anthropic_key, model=model)

    if model_lower.startswith(("gpt-", "o1-", "o3-", "o4-", "o3", "o4")):
        from core.llm.adapters.openai import OpenAIAdapter
        if not config.openai_key:
            raise ValueError("OPENAI_API_KEY nie jest ustawiony")
        return OpenAIAdapter(api_key=config.openai_key, model=model)

    if model_lower.startswith("gemini"):
        from core.llm.adapters.gemini import GeminiAdapter
        api_key = config.gemini_key_for_tier(tier)
        if not api_key:
            key_name = "GEMINI_API_KEY_PREMIUM" if tier == "premium" else "GEMINI_API_KEY"
            raise ValueError(f"{key_name} nie jest ustawiony (tier='{tier}')")
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
