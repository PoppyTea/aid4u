"""Testy CostTrackMiddleware — telemetria (koszt/Langfuse) nie może przerywać wywołania LLM."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from core.llm.middleware import CostTrackMiddleware, LLMMiddleware, ProviderCallMiddleware
from core.llm.types import LLMMessage, LLMResponse, Tool


def make_response() -> LLMResponse:
    return LLMResponse(content="odpowiedź", model="gemini-test", input_tokens=10, output_tokens=5)


class _StubTerminal(LLMMiddleware):
    """Terminal handler zwracający ustaloną odpowiedź, bez realnego providera."""

    def __init__(self, response: LLMResponse) -> None:
        super().__init__()
        self._response = response

    def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        return self._response


class _RaisingTerminal(LLMMiddleware):
    """Terminal handler symulujący awarię providera (np. wyczerpany retry w RateLimitMiddleware)."""

    def __init__(self, error: BaseException) -> None:
        super().__init__()
        self._error = error

    def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        raise self._error


def _build(response: LLMResponse) -> CostTrackMiddleware:
    mw = CostTrackMiddleware()
    mw.set_next(_StubTerminal(response))
    return mw


def _build_raising(error: BaseException) -> CostTrackMiddleware:
    mw = CostTrackMiddleware()
    mw.set_next(_RaisingTerminal(error))
    return mw


def test_returns_response_unchanged():
    response = make_response()
    mw = _build(response)

    result = mw.handle([LLMMessage.user("pytanie")])

    assert result is response


@patch("langfuse.get_client")
def test_langfuse_failure_does_not_break_the_call(mock_get_client):
    mock_get_client.side_effect = RuntimeError("langfuse down")
    response = make_response()
    mw = _build(response)

    result = mw.handle([LLMMessage.user("pytanie")])

    assert result is response


# ─── Bezpieczeństwo wyjątków — generacja Langfuse zamknięta, gdy provider padnie ──
#
# Do 2026-08-16, jeśli call_next() rzucił (np. provider wyczerpał retry), handle()
# kończył się wyjątkiem PRZED wywołaniem _end_langfuse_generation() — generacja
# zostawała otwarta w Langfuse na zawsze. To był udokumentowany, świadomy dług
# ("akceptowalne dla pierwszej wersji"), zamknięty tutaj.


@patch("langfuse.get_client")
def test_provider_exception_still_propagates_unchanged(mock_get_client):
    error = RuntimeError("provider wyczerpał retry")
    mw = _build_raising(error)

    import pytest

    with pytest.raises(RuntimeError, match="provider wyczerpał retry") as exc_info:
        mw.handle([LLMMessage.user("pytanie")])

    assert exc_info.value is error  # dokładnie ten sam obiekt — telemetria nie owija/maskuje


@patch("langfuse.get_client")
def test_provider_exception_closes_generation_with_error_status(mock_get_client):
    generation = MagicMock()
    mock_get_client.return_value.start_observation.return_value = generation
    mw = _build_raising(RuntimeError("boom"))

    import pytest

    with pytest.raises(RuntimeError):
        mw.handle([LLMMessage.user("pytanie")])

    generation.update.assert_called_once_with(level="ERROR", status_message="boom")
    generation.end.assert_called_once()


def test_provider_exception_without_langfuse_configured_still_propagates():
    """Brak Langfuse (start_observation zwraca None przez wewnętrzny except) nie może
    zablokować propagacji prawdziwego błędu providera."""
    error = ValueError("prawdziwy błąd providera")
    mw = _build_raising(error)

    import pytest

    with pytest.raises(ValueError, match="prawdziwy błąd providera"):
        mw.handle([LLMMessage.user("pytanie")])


def test_cost_is_actually_calculated_for_a_known_model():
    """
    Regresja: `genai_prices.calculate(...)` był API z wcześniejszej wersji paczki —
    dzisiejsza wymaga `calc_price(Usage(...), model_ref)`. Błąd nazwy atrybutu był
    tu od zawsze, ale `except Exception` (best-effort, patrz docstring klasy) go
    połykał cicho — żaden test nie wywoływał `genai_prices` naprawdę, więc nikt tego
    nie złapał, dopóki nie ujawnił się na żywym przebiegu s03e01 (2026-08-16).
    Celowo BEZ mocka `genai_prices` — to jest dokładnie to, czego mock by nie złapał.
    """
    response = LLMResponse(
        content="x", model="claude-haiku-4-5-20251001", input_tokens=100, output_tokens=50
    )
    mw = _build(response)

    with patch("logfire.info") as mock_logfire_info:
        mw.handle([LLMMessage.user("pytanie")])

    calls = [c for c in mock_logfire_info.call_args_list if c.args[:1] == ("llm_call_completed",)]
    assert len(calls) == 1, "oczekiwano dokładnie jednego zdarzenia llm_call_completed"
    cost_usd = calls[0].kwargs["cost_usd"]
    assert isinstance(cost_usd, float)
    assert cost_usd > 0


@patch("langfuse.get_client")
def test_creates_and_finalizes_langfuse_generation(mock_get_client):
    generation = MagicMock()
    mock_get_client.return_value.start_observation.return_value = generation
    response = make_response()
    mw = _build(response)

    mw.handle([LLMMessage.user("pytanie")])

    _, kwargs = mock_get_client.return_value.start_observation.call_args
    assert kwargs["as_type"] == "generation"
    assert kwargs["input"] == [{"role": "user", "content": "pytanie"}]

    generation.update.assert_called_once()
    update_kwargs = generation.update.call_args.kwargs
    assert update_kwargs["output"] == "odpowiedź"
    assert update_kwargs["usage_details"] == {"input_tokens": 10, "output_tokens": 5}
    generation.end.assert_called_once()


def test_call_next_without_terminal_handler_raises_runtime_error():
    """Calling call_next on a middleware without _next configured should raise RuntimeError."""
    import pytest

    class SimpleMiddleware(LLMMiddleware):
        def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
            return self.call_next(messages, **kwargs)

    mw = SimpleMiddleware()
    with pytest.raises(RuntimeError, match="Brak terminalnego handlera w łańcuchu middleware"):
        mw.handle([LLMMessage.user("pytanie")])


# ─── ProviderCallMiddleware — dispatch po schema/tools (naprawa 2026-08-16) ────
#
# Do 2026-08-16 tylko complete() szedł przez łańcuch middleware — structured()
# i run_agent_loop() wołały self._provider bezpośrednio, więc cost-tracking
# i generacje Langfuse nigdy ich nie widziały. Te testy pilnują, że dispatch
# faktycznie trafia do właściwej metody adaptera i że schema/tools nie
# przeciekają do complete() jako nieznany kwarg.


class _DummySchema(BaseModel):
    ok: bool


def test_provider_call_dispatches_to_complete_structured_when_schema_present():
    provider = MagicMock()
    provider.complete_structured.return_value = LLMResponse(
        content="{}", model="m", input_tokens=1, output_tokens=1, parsed=_DummySchema(ok=True)
    )
    mw = ProviderCallMiddleware(provider)

    mw.handle([LLMMessage.user("x")], system="sys", schema=_DummySchema)

    provider.complete_structured.assert_called_once_with(
        [LLMMessage.user("x")], _DummySchema, system="sys"
    )
    provider.complete.assert_not_called()


def test_provider_call_dispatches_to_complete_with_tools_when_tools_present():
    provider = MagicMock()
    provider.complete_with_tools.return_value = make_response()
    tools = [Tool("search", "Szuka", {})]
    mw = ProviderCallMiddleware(provider)

    mw.handle([LLMMessage.user("x")], system="sys", tools=tools)

    provider.complete_with_tools.assert_called_once_with([LLMMessage.user("x")], tools, system="sys")
    provider.complete.assert_not_called()


def test_provider_call_falls_back_to_complete_without_schema_or_tools():
    provider = MagicMock()
    provider.complete.return_value = make_response()
    mw = ProviderCallMiddleware(provider)

    mw.handle([LLMMessage.user("x")], system="sys", max_tokens=10)

    provider.complete.assert_called_once_with([LLMMessage.user("x")], system="sys", max_tokens=10)
    provider.complete_structured.assert_not_called()
    provider.complete_with_tools.assert_not_called()


# ─── CostTrackMiddleware — prompt_name popped before call_next ────────────────


def test_cost_track_pops_prompt_name_before_forwarding_to_next_handler():
    """prompt_name musi zniknąć z kwargs przed call_next(), inaczej terminal handler
    (adapter) dostałby nieznany kwarg i wywalił TypeError."""
    received_kwargs: dict = {}

    class _CapturingTerminal(LLMMiddleware):
        def handle(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
            received_kwargs.update(kwargs)
            return make_response()

    mw = CostTrackMiddleware()
    mw.set_next(_CapturingTerminal())

    mw.handle([LLMMessage.user("x")], system="sys", prompt_name="my-prompt")

    assert "prompt_name" not in received_kwargs
    assert received_kwargs == {"system": "sys"}
