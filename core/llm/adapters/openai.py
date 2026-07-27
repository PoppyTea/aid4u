"""Adapter: OpenAI SDK → LLMProvider."""
from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from core.llm.base import LLMProvider
from core.llm.types import LLMMessage, LLMResponse, Tool, ToolCall

T = TypeVar("T", bound=BaseModel)


class OpenAIAdapter(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-5.4-nano") -> None:
        import openai
        self._client = openai.OpenAI(api_key=api_key)
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
        oai_messages: list[dict] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages += [{"role": m.role, "content": m.content} for m in messages]

        response = self._client.chat.completions.create(
            model=self._model,
            messages=oai_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

    def complete_structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        schema_str = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        system_prompt = (system or "") + f"\nRespond ONLY with JSON: {schema_str}"
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
        oai_messages: list[dict] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages += [{"role": m.role, "content": m.content} for m in messages]

        oai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

        response = self._client.chat.completions.create(
            model=self._model,
            messages=oai_messages,
            tools=oai_tools,
            max_tokens=4096,
        )
        msg = response.choices[0].message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
            for tc in (msg.tool_calls or [])
        ]
        return LLMResponse(
            content=msg.content or "",
            model=response.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            tool_calls=tool_calls,
        )
