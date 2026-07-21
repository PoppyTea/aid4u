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

        start = time.perf_counter()
        generation = self._start_langfuse_generation(messages)

        response = self.call_next(messages, **kwargs)
        elapsed = time.perf_counter() - start

        cost: float | None = None
        try:
            import genai_prices

            cost = genai_prices.calculate(
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
            logfire.info(
                "llm_call_completed",
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=round(cost, 6) if cost else None,
                elapsed_s=round(elapsed, 3),
            )
        except Exception:
            logfire.warning("Failed to track cost", exc_info=True)  # cost tracking jest best-effort

        self._end_langfuse_generation(generation, response, cost)

        return response

    @staticmethod
    def _start_langfuse_generation(messages: list[LLMMessage]):
        """Zwraca observation Langfuse albo None (no-op), jeśli cokolwiek pójdzie nie tak."""
        try:
            from langfuse import get_client

            return get_client().start_observation(
                as_type="generation",
                name="llm_call",
                input=[{"role": m.role, "content": m.content} for m in messages],
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
    """Terminal handler — wywołuje właściwy adapter LLM."""

    def __init__(self, provider) -> None:
        super().__init__()
        self._provider = provider

    def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        return self._provider.complete(messages, **kwargs)
