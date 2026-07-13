"""Adapter: Google GenAI SDK → LLMProvider."""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel
from pydantic_core.core_schema import ErrorType

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

        # Jeżeli SDK sparsowało odpowiedź do modelu Pydantic (response.parsed), używamy go.
        # W przeciwnym razie parsujemy surowy tekst.
        if response.parsed:
            return response.parsed  # type: ignore

        finish_reason = None
        if response.candidates:
            finish_reason = response.candidates[0].finish_reason

        if response.text is None:
            raise TypeError(
                f"Response text is None (finish_reason={finish_reason}). "
                "Model prawdopodobnie nie wygenerował żadnej treści."
            )

        try:
            return schema.model_validate_json(response.text)
        except Exception as e:
            if finish_reason and getattr(finish_reason, "name", str(finish_reason)).upper() != "STOP":
                raise ValueError(
                    f"Odpowiedź modelu wygląda na ucięty JSON (finish_reason={finish_reason}). "
                    f"Prawdopodobnie zabrakło max_output_tokens. Oryginalny błąd: {e}"
                ) from e
            raise

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
