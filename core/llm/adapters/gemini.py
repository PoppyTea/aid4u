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
# Weryfikacja: `deprecation-watch` diffuje ten roster cotygodniowo — realnym wywołaniem
# per klucz, nie samym `models.list()` (powód niżej).
GEMINI_MODELS = {
    "standard": {
        "fast": "gemini-3.5-flash-lite",
        "balanced": "gemini-2.5-flash",  # domyślny model projektu
        "powerful": "gemini-3.7-flash",
    },
    "premium": {
        "fast": "gemini-3.5-flash-lite",
        "balanced": "gemini-3.7-flash",
        # Jedyny pro powyżej rodziny 2.5; istnieje wyłącznie jako `-preview`, więc Google
        # może go zmienić albo wycofać bez zapowiedzi — `deprecation-watch` wyłapie to
        # w tygodniu, w którym nastąpi. Na kluczu darmowym zwraca 429 (brak quoty), stąd
        # inny `powerful` po stronie standard.
        "powerful": "gemini-3.1-pro-preview",
    },
}

# Rodzina 2.5 jest wygaszana i NIE nadaje się na nowe wpisy w rosterze. Zmierzone
# 2026-08-23 realnym wywołaniem na obu kluczach: `gemini-2.5-flash-lite` i
# `gemini-2.5-pro` dają 404 wszędzie, a `gemini-2.5-flash` żyje wyłącznie na starym
# projekcie darmowym — na kluczu premium zwraca 404 z komunikatem "no longer available
# to new users". Zostaje jako `standard`/`balanced`, bo to domyślny model projektu i
# znana linia bazowa kosztu, ale jest grandfatherowany, nie wspierany.
#
# Lekcja szersza niż ten wpis: `client.models.list()` wymieniał wszystkie sześć modeli,
# łącznie z tymi dającymi 404. Katalog globalny NIE odpowiada na pytanie "czy tym
# kluczem to zawołam" — weryfikacja rostera musi iść realnym wywołaniem per klucz.


class GeminiAdapter(LLMProvider):
    """
    Adapter Gemini — domyślny model `GEMINI_MODELS["standard"]["balanced"]`, ten sam,
    który `run.py` podaje jako domyślną wartość `--model`.

    Poprzedni default (`gemini-3.1-flash`) był nieistniejącym identyfikatorem —
    sprawdzone 2026-08-16 przez `client.models.list()` na żywym kluczu: rodzina 3.1 ma
    `-flash-lite`, `-flash-image`, `-pro-preview`, ale nie gołe `-flash`. Ten epizod jest
    powodem, dla którego `create_provider()` waliduje dziś ID wobec `GEMINI_MODELS`.
    """

    def __init__(self, api_key: str, model: str = GEMINI_MODELS["standard"]["balanced"]) -> None:
        """Tworzy klienta google-genai dla podanego klucza i identyfikatora modelu."""
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
    ) -> LLMResponse:
        from google.genai import types

        # Zachowujemy dotychczasową logikę łączenia wiadomości w jeden prompt,
        # aby zminimalizować zmiany w zachowaniu modułu.
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)

        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            # Przypięte 0.0, nie parametr: warstwa nigdy nie potrzebowała innej wartości
            # (`LLMClient` nawet jej nie przekazywał), ale samo 0.0 pracuje — zdejmij je,
            # a przebiegi przestaną być porównywalne kosztowo i wynikowo. Sterowanie
            # samplingiem to osobna sprawa, patrz AID-52.
            temperature=0.0,
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

    def _thinking_config(self):
        """
        Wybiera sposób sterowania myśleniem wg rodziny modelu — te dwa kontrakty się
        wykluczają i zmieszanie ich w jednym zapytaniu daje 400.

        Rodzina 2.5 przyjmuje `thinking_budget=0` (wyłączenie myślenia). Rodzina 3.x
        oczekuje `thinking_level`, a `gemini-3.1-pro-preview` odrzuca budżet zerowy
        wprost: *"Budget 0 is invalid. This model only works in thinking mode."*
        (zmierzone realnym wywołaniem 2026-08-23). `"low"` to najbliższy odpowiednik
        dawnej intencji — myślenie zjada tę samą pulę co `max_output_tokens`, więc przy
        wsadowym structured output potrafiło uciąć JSON w połowie.
        """
        from google.genai import types

        if self._model_name.startswith("gemini-2."):
            return types.ThinkingConfig(thinking_budget=0)
        return types.ThinkingConfig(thinking_level="low")

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
        # Sterowanie myśleniem — patrz `_thinking_config()`.
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=schema,
            thinking_config=self._thinking_config(),
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
