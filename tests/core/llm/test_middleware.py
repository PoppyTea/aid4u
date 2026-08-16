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


def _build(response: LLMResponse) -> CostTrackMiddleware:
    mw = CostTrackMiddleware()
    mw.set_next(_StubTerminal(response))
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
