"""Adapter: Google Generative AI SDK → LLMProvider."""
from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from core.llm.base import LLMProvider
from core.llm.types import LLMMessage, LLMResponse, Tool

T = TypeVar("T", bound=BaseModel)


class GeminiAdapter(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model

    @property
    def model_name(self) -> str:
        return self._model_name

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system,
        )
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        config = self._genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
        response = model.generate_content(prompt, generation_config=config)
        usage = response.usage_metadata
        return LLMResponse(
            content=response.text,
            model=self._model_name,
            input_tokens=usage.prompt_token_count,
            output_tokens=usage.candidates_token_count,
        )

    def complete_structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        schema_str = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        system_prompt = (system or "") + f"\nRespond ONLY with valid JSON: {schema_str}"
        response = self.complete(messages, system=system_prompt, max_tokens=4096)
        content = response.content.strip().lstrip("```json").rstrip("```").strip()
        return schema.model_validate_json(content)

    def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[Tool],
        *,
        system: str | None = None,
    ) -> LLMResponse:
        # TODO: Gemini function calling — niski priorytet, dodaj gdy zadanie tego wymaga
        raise NotImplementedError(
            "Gemini tool calling not yet implemented. "
            "Użyj AnthropicAdapter lub OpenAIAdapter dla zadań z function calling."
        )
