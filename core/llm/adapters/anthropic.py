"""Adapter: Anthropic SDK → LLMProvider."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, TypeVar

from pydantic import BaseModel

from core.llm.base import LLMProvider
from core.llm.types import LLMMessage, LLMResponse, Tool, ToolCall

T = TypeVar("T", bound=BaseModel)

# Modele Anthropic — drabina eskalacji od 28.07.2026 (patrz strategy/llm-selection.md).
# Używaj przez LLMClient, nie bezpośrednio przez ten adapter.
ANTHROPIC_MODELS = {
    "fast": "claude-haiku-4-5-20251001",   # domyślny start — najtańszy w rodzinie
    "balanced": "claude-sonnet-5",          # Haiku zawodzi — złożone zadania, function calling
    "powerful": "claude-opus-5",             # Sonnet nie wystarcza
    "flagship": "claude-fable-5",            # ostateczność w rodzinie Claude
}


class AnthropicAdapter(LLMProvider):
    """Adapter konwertujący Anthropic SDK do interfejsu LLMProvider."""

    def __init__(self, api_key: str, model: str = ANTHROPIC_MODELS["fast"]) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    def complete_structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        system: str | None = None,
    ) -> LLMResponse:
        schema_str = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        system_prompt = (
            (system or "")
            + f"\n\nRespond ONLY with valid JSON matching this schema. No markdown, no explanation:\n{schema_str}"
        )
        response = self.complete(messages, system=system_prompt, max_tokens=4096)

        # Strip markdown fences if model wraps JSON in ```json ... ``` — case-insensitive
        # prefix check (`` ```JSON `` is legal and otherwise leaves "JSON\n" in `content`,
        # breaking `model_validate_json()`; same fix as `adapters/openai.py`).
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content[:4].lower() == "json":
                content = content[4:]
            content = content.strip()

        parsed = schema.model_validate_json(content)
        # `replace()` zachowuje model/tokeny z `self.complete()` — jedyne co dokładamy
        # to `parsed`, żeby LLMResponse niosło oba (surowy JSON w `content` do podglądu,
        # sparsowany model do rozpakowania przez LLMClient.structured()).
        return replace(response, parsed=parsed)

    def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[Tool],
        *,
        system: str | None = None,
    ) -> LLMResponse:
        anthropic_tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "tools": anthropic_tools,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)

        tool_calls = [
            ToolCall(id=block.id, name=block.name, arguments=block.input)
            for block in response.content
            if block.type == "tool_use"
        ]
        text = " ".join(block.text for block in response.content if block.type == "text")

        return LLMResponse(
            content=text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            tool_calls=tool_calls,
        )
