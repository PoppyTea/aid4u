"""Adapter: Google GenAI SDK → LLMProvider."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from core.llm.base import LLMProvider
from core.llm.types import LLMMessage, LLMResponse, Tool

T = TypeVar("T", bound=BaseModel)


class GeminiAdapter(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
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
        from google.genai import types

        # Zachowujemy dotychczasową logikę łączenia wiadomości w jeden prompt,
        # aby zminimalizować zmiany w zachowaniu modułu.
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)

        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=config,
        )

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
        from google.genai import types

        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)

        # Nowy SDK wspiera natywnie response_schema (Pydantic),
        # co eliminuje potrzebę ręcznego parsowania JSON-a z Markdowna.
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=4096,
            response_mime_type="application/json",
            response_schema=schema,
        )

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=config,
        )

        # Jeżeli SDK sparsowało odpowiedź do modelu Pydantic (response.parsed), używamy go.
        # W przeciwnym razie parsujemy surowy tekst.
        if response.parsed:
            return response.parsed  # type: ignore
        elif response.text is None:
            raise TypeError("Response text is None")
        return schema.model_validate_json(response.text)

    def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[Tool],
        *,
        system: str | None = None,
    ) -> LLMResponse:
        from google.genai import types
        from core.llm.types import ToolCall

        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)

        function_declarations = []
        for t in tools:
            # Pydantic dict (schema) -> types.FunctionDeclaration
            # Pydantic schemas often use types like 'string', 'object' etc. in lowercase.
            # Types.FunctionDeclaration parameter supports a dict representation of the schema.
            # We can map core.llm.types.Tool to it.
            fd = types.FunctionDeclaration(
                name=t.name, description=t.description, parameters=t.parameters
            )
            function_declarations.append(fd)

        gemini_tools = [types.Tool(function_declarations=function_declarations)]

        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=gemini_tools,
            max_output_tokens=4096,
        )

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=config,
        )

        tool_calls: list[ToolCall] = []
        content_text = ""

        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    tool_calls.append(
                        ToolCall(
                            id=part.function_call.id
                            or part.function_call.name,  # id might be optional in old SDKs, fallback to name
                            name=part.function_call.name,
                            arguments=part.function_call.args if part.function_call.args else {},
                        )
                    )
                elif part.text:
                    content_text += part.text

        usage = response.usage_metadata
        return LLMResponse(
            content=content_text.strip(),
            model=self._model_name,
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
            tool_calls=tool_calls,
        )
