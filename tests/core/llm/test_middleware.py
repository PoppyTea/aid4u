"""Testy CostTrackMiddleware — telemetria (koszt/Langfuse) nie może przerywać wywołania LLM."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.llm.middleware import CostTrackMiddleware, LLMMiddleware
from core.llm.types import LLMMessage, LLMResponse


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
