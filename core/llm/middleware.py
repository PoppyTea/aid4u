"""
Chain of Responsibility — pipeline wywołań LLM.

Każde wywołanie przechodzi przez łańcuch handlerów:
    RateLimitMiddleware → CostTrackMiddleware → ProviderCallMiddleware

Dodanie nowego kroku (np. cache'owanie odpowiedzi, prompt guard):
    1. Utwórz klasę dziedziczącą po LLMMiddleware
    2. Dodaj ją do łańcucha w LLMClient.__init__()
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.llm.types import LLMMessage, LLMResponse


class LLMMiddleware(ABC):
    """Bazowy handler w łańcuchu odpowiedzialności."""

    def __init__(self) -> None:
        self._next: LLMMiddleware | None = None

    def set_next(self, handler: "LLMMiddleware") -> "LLMMiddleware":
        """Ustawia następny handler i zwraca go (umożliwia chaining)."""
        self._next = handler
        return handler

    @abstractmethod
    def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse: ...

    def call_next(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        if self._next is None:
            raise RuntimeError("Brak terminalnego handlera w łańcuchu middleware")
        return self._next.handle(messages, **kwargs)


class RateLimitMiddleware(LLMMiddleware):
    """
    Obsługuje rate limiting i błędy 429/503 przez exponential backoff.
    Szczególnie ważne dla zadania 'railway' (celowe przeciążenie API).
    """

    def __init__(self, max_attempts: int = 5) -> None:
        super().__init__()
        self._max_attempts = max_attempts

    def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        from tenacity import (
            retry,
            retry_if_exception_type,
            stop_after_attempt,
            wait_exponential,
        )

        @retry(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=1, min=2, max=60),
            retry=retry_if_exception_type((Exception,)),
            reraise=True,
        )
        def _call() -> LLMResponse:
            return self.call_next(messages, **kwargs)

        return _call()


class CostTrackMiddleware(LLMMiddleware):
    """
    Liczy koszt wywołania (genai-prices), loguje do Logfire i tworzy
    generation w Langfuse.

    To jedyny punkt przez który przechodzi KAŻDE wywołanie LLM niezależnie
    od providera — stąd tu, nie w adapterach. Ważne dla Gemini (domyślny
    provider projektu): Logfire ma natywną auto-instrumentację tylko dla
    Anthropic (`instrument_anthropic()`), więc bez tego miejsca żadne
    wywołanie Gemini nigdy nie trafiało do żadnego systemu obserwability.

    Błędy telemetrii (koszt, Langfuse) są nieblokujące — nigdy nie przerywają
    właściwego wywołania LLM. Znane ograniczenie: jeśli call_next() rzuci
    wyjątkiem, generation w Langfuse zostaje niezamknięta (brak .end()) —
    akceptowalne dla pierwszej wersji, do poprawy gdyby okazało się problemem.
    """

    def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        import time
        import logfire

        # `prompt_name=` nie jest parametrem żadnego adaptera — pop() PRZED
        # call_next(), inaczej ProviderCallMiddleware/adapter dostałby
        # nieznany kwarg. Łączy generację z wersją promptu zarejestrowaną
        # przez core.observability.prompts.sync_prompt() (patrz
        # strategy/observability.md, sekcja "Rejestr promptów").
        prompt_name = kwargs.pop("prompt_name", None)

        start = time.perf_counter()
        generation = self._start_langfuse_generation(messages, prompt_name=prompt_name)

        response = self.call_next(messages, **kwargs)
        elapsed = time.perf_counter() - start

        cost: float | None = None
        try:
            from genai_prices import Usage, calc_price

            # `genai_prices.calculate(model=, input_tokens=, output_tokens=)` był API
            # z wcześniejszej wersji paczki — dzisiejsza to `calc_price(usage, model_ref)`,
            # zwraca `PriceCalculation.total_price` (Decimal). Błąd nazwy atrybutu
            # (`AttributeError: no attribute 'calculate'`) był tu od zawsze, ale nigdy
            # nie ujawnił się w praktyce: przed naprawą łańcucha middleware (2026-08-16)
            # ten kod uruchamiał się tylko dla chat(), które w realnych zadaniach prawie
            # się nie używa — .structured()/run_agent_loop() dopiero teraz przechodzą
            # tędy i odsłoniły martwy kod. Złapane przez `except Exception` niżej —
            # cost tracking jest best-effort, nigdy nie przerywa właściwego wywołania.
            price = calc_price(
                Usage(input_tokens=response.input_tokens, output_tokens=response.output_tokens),
                response.model,
            )
            cost = float(price.total_price)
            logfire.info(
                "llm_call_completed",
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=round(cost, 6),
                elapsed_s=round(elapsed, 3),
            )
        except Exception:
            logfire.warning("Failed to track cost", exc_info=True)  # cost tracking jest best-effort

        self._end_langfuse_generation(generation, response, cost)

        return response

    @staticmethod
    def _start_langfuse_generation(messages: list[LLMMessage], *, prompt_name: str | None = None):
        """
        Zwraca observation Langfuse albo None (no-op), jeśli cokolwiek pójdzie nie tak.

        `prompt_name`, gdy podane, jest wyszukiwane w rejestrze
        (`core.observability.prompts.get_prompt_ref`) — jeśli synchronizacja
        tego promptu powiodła się w tym procesie, generacja zostaje z nim
        podpięta (`prompt=`), więc panel Langfuse pokazuje wersja→trace'y→koszt
        obok siebie. Brak wpisu w rejestrze (nie zsynchronizowano / fallback)
        po prostu pomija `prompt=` — nie jest to błąd.
        """
        try:
            from langfuse import get_client

            prompt_client = None
            if prompt_name:
                from core.observability.prompts import get_prompt_ref

                ref = get_prompt_ref(prompt_name)
                if ref is not None and not ref.is_fallback:
                    prompt_client = ref.client

            return get_client().start_observation(
                as_type="generation",
                name="llm_call",
                input=[{"role": m.role, "content": m.content} for m in messages],
                prompt=prompt_client,
            )
        except Exception:
            import logfire

            logfire.warning("Failed to start Langfuse generation", exc_info=True)
            return None

    @staticmethod
    def _end_langfuse_generation(generation, response: LLMResponse, cost: float | None) -> None:
        if generation is None:
            return
        try:
            generation.update(
                model=response.model,
                output=response.content,
                usage_details={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
                metadata={"cost_usd": str(round(cost, 6))} if cost is not None else None,
            )
            generation.end()
        except Exception:
            import logfire

            logfire.warning("Failed to finalize Langfuse generation", exc_info=True)


class ProviderCallMiddleware(LLMMiddleware):
    """
    Terminal handler — jedyne miejsce w łańcuchu, które faktycznie robi I/O
    (wywołuje adapter). RateLimit/CostTrack owijają to wywołanie, ale go nie
    zawierają — ten podział jest celowy: przyszła wersja asynchroniczna
    (`ahandle()`) potrzebowałaby zamienić tylko tę jedną metodę na `await`,
    bez ruszania logiki wzbogacania w pozostałych middleware (patrz decyzja
    o async w `strategy/observability.md`).

    Dispatch po rodzaju wywołania — `kwargs["schema"]`/`kwargs["tools"]`
    obecne wtedy i tylko wtedy, gdy `LLMClient.structured()`/`run_agent_loop()`
    je przekazały (patrz `client.py`). Domyślnie: zwykłe `complete()`.
    """

    def __init__(self, provider) -> None:
        super().__init__()
        self._provider = provider

    def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        schema = kwargs.pop("schema", None)
        tools = kwargs.pop("tools", None)

        if schema is not None:
            return self._provider.complete_structured(messages, schema, **kwargs)
        if tools is not None:
            return self._provider.complete_with_tools(messages, tools, **kwargs)
        return self._provider.complete(messages, **kwargs)
