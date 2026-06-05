"""
Factory pattern — tworzy właściwy adapter na podstawie nazwy modelu.

⚠️  DOMYŚLNY MODEL PROJEKTU: gemini-2.5-flash
    NIE zmieniaj domyślnych na gpt-4o, gpt-4o-mini ani modele gemini-2.0/1.5 (wycofane).
    Hierarchia: gemini-2.5-flash → gemini-3-flash → claude-haiku → claude-sonnet
    Szczegóły: models-reference.md i llm-strategy.md

Mapowanie prefixów (router):
    claude-*                      → AnthropicAdapter
    gemini-*                      → GeminiAdapter  (gemini-2.5-*, gemini-3-*, gemini-3.1-*)
    gpt-* / o1-* / o3-* / o4-*   → OpenAIAdapter  (gpt-5.4-*, gpt-5-*, gpt-4.1-*, o4-mini...)
    openrouter/*                  → OpenRouterAdapter (TODO)
"""
from __future__ import annotations

from core.config import Config
from core.llm.base import LLMProvider


def create_provider(model: str, config: Config) -> LLMProvider:
    """
    Fabryka adapterów. Wywołaj przez LLMClient, nie bezpośrednio.

    Args:
        model: Pełna nazwa modelu, np. 'gemini-2.5-flash'
        config: Singleton konfiguracji z kluczami API
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
        if not config.gemini_key:
            raise ValueError("GEMINI_API_KEY nie jest ustawiony")
        return GeminiAdapter(api_key=config.gemini_key, model=model)

    if model_lower.startswith("openrouter/"):
        from core.llm.adapters.openrouter import OpenRouterAdapter
        if not config.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY nie jest ustawiony")
        return OpenRouterAdapter(api_key=config.openrouter_key, model=model)

    raise ValueError(
        f"Nieznany prefix modelu: '{model}'. "
        "Obsługiwane: claude-*, gemini-*, gpt-*, o1-*, o3-*, o4-*, openrouter/*"
    )
