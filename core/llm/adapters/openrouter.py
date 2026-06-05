from __future__ import annotations

from core.llm.adapters.openai import OpenAIAdapter

class OpenRouterAdapter(OpenAIAdapter):
    def __init__(self, api_key: str, model: str) -> None:
        import openai
        self._client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        # OpenRouter models often have the `openrouter/` prefix stripped if we just use the rest,
        # but the OpenRouter API accepts the full model name e.g. "anthropic/claude-3-opus",
        # so we strip the 'openrouter/' prefix.
        if model.lower().startswith("openrouter/"):
            model = model[11:]
        self._model = model
