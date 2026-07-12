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
    Liczy koszt wywołania (genai-prices) i loguje do Logfire.
    Nieblokujący — błędy trackowania kosztu nie przerywają wywołania.
    """

    def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        import time
        import logfire

        start = time.perf_counter()
        response = self.call_next(messages, **kwargs)
        elapsed = time.perf_counter() - start

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
        except Exception as e:
            logfire.warning(f"Failed to track cost: {e}")  # cost tracking jest best-effort

        return response


class ProviderCallMiddleware(LLMMiddleware):
    """Terminal handler — wywołuje właściwy adapter LLM."""

    def __init__(self, provider) -> None:
        super().__init__()
        self._provider = provider

    def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        return self._provider.complete(messages, **kwargs)
