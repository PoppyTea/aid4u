"""Adapter: OpenAI SDK → LLMProvider."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import TYPE_CHECKING, TypeVar, cast

from pydantic import BaseModel

from core.llm.base import LLMProvider
from core.llm.thinking import ThinkingLevel, openai_reasoning_effort
from core.llm.types import LLMMessage, LLMResponse, Tool, ToolCall

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

T = TypeVar("T", bound=BaseModel)

# Drabina eskalacji OpenAI. Rodzina 5.6 rozdziela generację od zdolności: numer mówi,
# które to pokolenie, a Luna/Terra/Sol to trwałe tiery, które awansują własnym tempem.
#
# To jest BARIERA ANTYHALUCYNACYJNA, nie ściągawka — `create_provider()` odrzuca każde ID
# spoza tego słownika. Modele z korpusu treningowego (`gpt-4o`, `gpt-4-turbo`) wchodzą
# agentom pod palce odruchowo; ten słownik jest jedynym miejscem, które je zatrzymuje.
# Zmiana wartości = świadoma decyzja o koszcie każdego przebiegu, nie porządki.
# Weryfikacja: `deprecation-watch` diffuje to cotygodniowo wobec `client.models.list()`.
OPENAI_MODELS = {
    "fast": "gpt-5.6-luna",      # domyślny start — najtańszy ($0.20/$1.20 za 1M)
    "balanced": "gpt-5.6-terra",  # Luna zawodzi — produkcyjne obciążenia ($2/$12)
    "powerful": "gpt-5.6-sol",    # flagowiec ($5/$30)
    "flagship": "gpt-5.6-sol",    # rodzina 5.6 nie ma czwartego stopnia
}


class OpenAIAdapter(LLMProvider):
    """Adapter konwertujący OpenAI SDK do interfejsu LLMProvider."""

    def __init__(self, api_key: str, model: str = OPENAI_MODELS["fast"]) -> None:
        """Tworzy klienta OpenAI dla podanego klucza i identyfikatora modelu."""
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
        temperature: float | None = 0.0,
        thinking: ThinkingLevel | None = None,
    ) -> LLMResponse:
        """Uzupełnia rozmowę jednym wywołaniem; `None` zostawia domyślne providera."""
        import openai

        oai_messages: list[dict] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages += [{"role": m.role, "content": m.content} for m in messages]

        # `oai_messages`/`oai_tools` budujemy jako gołe `dict`, a SDK oczekuje TypedDict-ów
        # (`ChatCompletionMessageParam`), więc bez zawężenia żadne przeciążenie nie pasuje.
        response = self._client.chat.completions.create(
            model=self._model,
            messages=cast("list[ChatCompletionMessageParam]", oai_messages),
            max_tokens=max_tokens,
            temperature=temperature,
            # Sentinel SDK zamiast rozpakowania `**{...}` — dict o typie `Any` gubi
            # rozpoznanie przeciążenia i cała sygnatura schodzi do `no-matching-overload`.
            reasoning_effort=(
                openai_reasoning_effort(thinking) if thinking is not None else openai.omit
            ),
        )
        # `usage` jest opcjonalne w schemacie OpenAI — ten sam wzorzec obronny co
        # w adapterze Gemini; brak licznika to 0, nie AttributeError w środku przebiegu.
        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    def complete_structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        system: str | None = None,
        thinking: ThinkingLevel | None = None,
    ) -> LLMResponse:
        schema_str = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        system_prompt = (system or "") + f"\nRespond ONLY with JSON: {schema_str}"
        response = self.complete(
            messages, system=system_prompt, max_tokens=4096, thinking=thinking
        )

        # Usuwa fence markdown jako DELIMITER, nie jako zbiór znaków do strip() —
        # `.lstrip("```json")` (poprzednia wersja) strippuje dowolny znak z ` ```json `,
        # więc dla fence'a `` ```JSON `` (wielkie litery) zostawia literalne "JSON\n"
        # przed danymi i psuje model_validate_json(). Split na "```" + case-insensitive
        # sprawdzenie prefiksu językowego naprawia oba przypadki.
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content[:4].lower() == "json":
                content = content[4:]
            content = content.strip()

        parsed = schema.model_validate_json(content)
        return replace(response, parsed=parsed)

    def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[Tool],
        *,
        system: str | None = None,
        thinking: ThinkingLevel | None = None,
    ) -> LLMResponse:
        """Wywołanie z narzędziami; `thinking=None` zostawia domyślne providera."""
        import openai

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
            messages=cast("list[ChatCompletionMessageParam]", oai_messages),
            tools=cast("list[ChatCompletionToolParam]", oai_tools),
            max_tokens=4096,
            reasoning_effort=(
                openai_reasoning_effort(thinking) if thinking is not None else openai.omit
            ),
        )
        msg = response.choices[0].message
        # `msg.tool_calls` to unia: wywołania funkcyjne mają `.function`, ale custom tools
        # (nowość schematu OpenAI) już nie. Filtrujemy po `type`, zamiast zakładać.
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
            for tc in (msg.tool_calls or [])
            if tc.type == "function"
        ]
        usage = response.usage
        return LLMResponse(
            content=msg.content or "",
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            tool_calls=tool_calls,
        )
