"""Adapter: Google GenAI SDK → LLMProvider."""

from __future__ import annotations

from typing import Any, TypeVar, cast

from pydantic import BaseModel

from core.llm.base import LLMProvider
from core.llm.types import LLMMessage, LLMResponse, Tool

T = TypeVar("T", bound=BaseModel)


class GeminiAdapter(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-3.1-flash") -> None:
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

        if response.text is None:
            finish_reason = response.candidates[0].finish_reason if response.candidates else None
            raise TypeError(
                f"Response text is None (finish_reason={finish_reason}). "
                "Model prawdopodobnie nie wygenerował żadnej treści."
            )

        usage = response.usage_metadata
        input_tokens = (usage.prompt_token_count or 0) if usage else 0
        output_tokens = (usage.candidates_token_count or 0) if usage else 0
        return LLMResponse(
            content=response.text,
            model=self._model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def complete_structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        system: str | None = None,
    ) -> LLMResponse:
        from google.genai import types

        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)

        # Nowy SDK wspiera natywnie response_schema (Pydantic),
        # co eliminuje potrzebę ręcznego parsowania JSON-a z Markdowna.
        #
        # thinking_budget=0: gemini-2.5-flash domyślnie ma włączone dynamiczne
        # "myślenie" (thinkingBudget=-1), które zużywa TĘ SAMĄ pulę tokenów co
        # max_output_tokens. Przy dłuższych/wsadowych odpowiedziach (np. tagowanie
        # kilkudziesięciu rekordów) model potrafi zużyć cały budżet na wewnętrzne
        # rozumowanie i urwać się w połowie JSON-a (patrz: dokumentacja Google,
        # sekcja "Task complexity" — klasyfikacja to podręcznikowy przykład
        # zadania, gdzie myślenie można i należy wyłączyć).
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=schema,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=config,
        )

        usage = response.usage_metadata
        input_tokens = (usage.prompt_token_count or 0) if usage else 0
        output_tokens = (usage.candidates_token_count or 0) if usage else 0

        # Jeżeli SDK sparsowało odpowiedź do modelu Pydantic (response.parsed), używamy go.
        # W przeciwnym razie parsujemy surowy tekst.
        if isinstance(response.parsed, schema):
            parsed = response.parsed
        else:
            finish_reason = None
            if response.candidates:
                finish_reason = response.candidates[0].finish_reason

            if response.text is None:
                raise TypeError(
                    f"Response text is None (finish_reason={finish_reason}). "
                    "Model prawdopodobnie nie wygenerował żadnej treści."
                )

            try:
                parsed = schema.model_validate_json(response.text)
            except Exception as e:
                if (
                    finish_reason
                    and getattr(finish_reason, "name", str(finish_reason)).upper() != "STOP"
                ):
                    raise ValueError(
                        f"Odpowiedź modelu wygląda na ucięty JSON (finish_reason={finish_reason}). "
                        f"Prawdopodobnie zabrakło max_output_tokens. Oryginalny błąd: {e}"
                    ) from e
                raise

        return LLMResponse(
            content=parsed.model_dump_json(),
            model=self._model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            parsed=parsed,
        )

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
                name=t.name, description=t.description, parameters_json_schema=t.parameters
            )
            function_declarations.append(fd)

        gemini_tools = [types.Tool(function_declarations=function_declarations)]

        config = types.GenerateContentConfig(
            system_instruction=system,
            # google-genai definiuje ToolListUnion warunkowo (zależnie od tego, czy
            # `mcp` jest zainstalowane), więc Pyright nie potrafi go użyć jako
            # wyrażenia typu do adnotacji ani do cast() — stąd cast na Any zamiast
            # ponownego budowania tej unii ręcznie.
            tools=cast(Any, gemini_tools),
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
                if part.function_call and part.function_call.name:
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
        input_tokens = (usage.prompt_token_count or 0) if usage else 0
        output_tokens = (usage.candidates_token_count or 0) if usage else 0
        return LLMResponse(
            content=content_text.strip(),
            model=self._model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_calls=tool_calls,
        )
