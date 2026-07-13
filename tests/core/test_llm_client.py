"""Testy LLMClient z zamockowanym providerem."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

from core.llm.client import LLMClient
from core.llm.types import LLMMessage, LLMResponse, Tool, ToolCall


def make_response(content: str, tool_calls=None) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="claude-test",
        input_tokens=10,
        output_tokens=5,
        tool_calls=tool_calls or [],
    )


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.model_name = "claude-test"
    return provider


@pytest.fixture
def llm(mock_provider):
    # Bypass middleware przy testach — testujemy logikę klienta, nie pipeline
    client = LLMClient.__new__(LLMClient)
    client._provider = mock_provider
    # Prosta chain bez rate limit / cost tracking dla szybkich testów
    from core.llm.middleware import ProviderCallMiddleware
    client._chain = ProviderCallMiddleware(mock_provider)
    return client


class TestLLMClientChat:
    def test_returns_string(self, llm, mock_provider):
        mock_provider.complete.return_value = make_response("Odpowiedź")
        result = llm.chat([LLMMessage.user("Pytanie")])
        assert result == "Odpowiedź"

    def test_passes_system_prompt(self, llm, mock_provider):
        mock_provider.complete.return_value = make_response("ok")
        llm.chat([LLMMessage.user("test")], system="Jesteś pomocnikiem")
        call_kwargs = mock_provider.complete.call_args.kwargs
        assert call_kwargs["system"] == "Jesteś pomocnikiem"


class TestLLMClientStructured:
    def test_parses_pydantic_model(self, llm, mock_provider):
        class MySchema(BaseModel):
            name: str
            age: int

        mock_provider.complete_structured.return_value = MySchema(name="Jan", age=30)
        result = llm.structured([LLMMessage.user("test")], MySchema)
        assert isinstance(result, MySchema)
        assert result.name == "Jan"


class TestAgentLoop:
    def test_stops_when_no_tool_calls(self, llm, mock_provider):
        mock_provider.complete_with_tools.return_value = make_response("Gotowe!")
        result = llm.run_agent_loop(
            [LLMMessage.user("Zadanie")],
            tools=[Tool("search", "Szuka informacji", {})],
            tool_executor=lambda name, args: "wynik",
        )
        assert result == "Gotowe!"
        assert mock_provider.complete_with_tools.call_count == 1

    def test_executes_tool_and_continues(self, llm, mock_provider):
        tool_call = ToolCall(id="c1", name="search", arguments={"query": "test"})
        # Pierwsza iteracja: zwróć tool call
        # Druga iteracja: zakończ bez tool calls
        mock_provider.complete_with_tools.side_effect = [
            make_response("Szukam...", tool_calls=[tool_call]),
            make_response("Znalazłem!"),
        ]
        executor = MagicMock(return_value="wynik wyszukiwania")
        result = llm.run_agent_loop(
            [LLMMessage.user("Szukaj czegoś")],
            tools=[Tool("search", "Szuka", {})],
            tool_executor=executor,
        )
        assert result == "Znalazłem!"
        executor.assert_called_once_with("search", {"query": "test"})

    def test_respects_max_iterations(self, llm, mock_provider):
        tool_call = ToolCall(id="c1", name="loop", arguments={})
        # Zawsze zwracaj tool calls → pętla nieskończona bez limitu
        mock_provider.complete_with_tools.return_value = make_response(
            "...", tool_calls=[tool_call]
        )
        _ = llm.run_agent_loop(
            [LLMMessage.user("test")],
            tools=[Tool("loop", "Zapętla", {})],
            tool_executor=lambda n, a: "ok",
            max_iterations=3,
        )
        assert mock_provider.complete_with_tools.call_count == 3

    @patch('logfire.exception')
    def test_tool_executor_error_doesnt_crash_loop(self, mock_logfire_exception, llm, mock_provider):
        tool_call = ToolCall(id="c1", name="broken", arguments={})
        mock_provider.complete_with_tools.side_effect = [
            make_response("", tool_calls=[tool_call]),
            make_response("Mimo błędu kontynuuję"),
        ]

        def bad_executor(name, args):
            raise RuntimeError("Narzędzie się posypało")

        result = llm.run_agent_loop(
            [LLMMessage.user("test")],
            tools=[Tool("broken", "Zepsute narzędzie", {})],
            tool_executor=bad_executor,
        )
        assert result == "Mimo błędu kontynuuję"
        mock_logfire_exception.assert_called_once_with("Tool broken failed")
