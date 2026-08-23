"""Adapter: Google GenAI SDK → LLMProvider."""

from __future__ import annotations

from typing import Any, TypeVar, cast

from pydantic import BaseModel

from core.llm.base import LLMProvider
from core.llm.types import LLMMessage, LLMResponse, Tool

T = TypeVar("T", bound=BaseModel)

# Drabina eskalacji Gemini. Jedyny provider o DWÓCH osiach: tier rozliczeniowy
# (standard/premium — osobne projekty Google Cloud, osobne klucze, patrz `factory.py`)
# krzyżuje się z tierem zdolności (lite → flash → pro). Stąd zagnieżdżenie, którego nie
# mają `ANTHROPIC_MODELS`/`OPENAI_MODELS`.
#
# To jest BARIERA ANTYHALUCYNACYJNA, nie ściągawka — `create_provider()` odrzuca każde ID
# spoza tego słownika. Powód nie jest teoretyczny: domyślnym modelem tego repo był kiedyś
# nieistniejący `gemini-3.1-flash`, wykryty dopiero przez `client.models.list()`
# 2026-08-16 (patrz docstring klasy niżej).
#
# Standard zostaje na 2.5 — darmowy tier ma tam znane limity i to jest linia bazowa
# kosztu, według której planujemy sezon. Weryfikacja: `deprecation-watch` diffuje to
# cotygodniowo wobec `client.models.list()`.
GEMINI_MODELS = {
    "standard": {
        "fast": "gemini-2.5-flash-lite",
        "balanced": "gemini-2.5-flash",  # domyślny model projektu
        "powerful": "gemini-2.5-pro",
    },
    "premium": {
        "fast": "gemini-3.5-flash-lite",
        "balanced": "gemini-3.7-flash",
        # Jedyny pro powyżej rodziny 2.5 istnieje wyłącznie jako `-preview`; Google może
        # go zmienić albo wycofać bez zapowiedzi. Świadomy wybór "najwyższy numer" —
        # `deprecation-watch` wyłapie zniknięcie w tygodniu, w którym nastąpi.
        "powerful": "gemini-3.1-pro-preview",
    },
}


class GeminiAdapter(LLMProvider):
    """
    Adapter Gemini — domyślny model `gemini-2.5-flash`, zgodnie z `run.py` i
    `strategy/llm-models.md` ("to jest wartość domyślna --model w run.py i
    startowy punkt dla każdego zadania"). Poprzedni default (`gemini-3.1-flash`)
    był nieistniejącym identyfikatorem — sprawdzone 2026-08-16 przez
    `client.models.list()` na żywym kluczu: rodzina 3.1 ma `-flash-lite`,
    `-flash-image`, `-pro-preview`, ale nie gołe `-flash`. Nawet gdyby istniał,
    complete_structured() poniżej steruje myśleniem przez `thinking_budget`
    (kontrakt 2.5.x) — model 3.x wymaga `thinking_level` i Google zwraca 400
    przy zmieszaniu obu w jednym zapytaniu (patrz `strategy/llm-models.md`).
    """

    def __init__(self, api_key: str, model: str = GEMINI_MODELS["standard"]["balanced"]) -> None:
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
            for index, part in enumerate(response.candidates[0].content.parts):
                if part.function_call and part.function_call.name:
                    tool_calls.append(
                        ToolCall(
                            # Fallback zawiera INDEKS części, nie samą nazwę: gdy SDK nie
                            # poda `id`, a model wywoła to samo narzędzie dwa razy w jednej
                            # odpowiedzi, oba wywołania dostawały identyczny identyfikator
                            # i łamały kontrakt „`id` jednoznacznie identyfikuje wywołanie",
                            # trzymany przez adaptery Anthropic i OpenAI (AID-18).
                            id=part.function_call.id or f"{part.function_call.name}-{index}",
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
