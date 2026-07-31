from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.llm.native_tool_code_execution import complete_with_code_execution
from core.llm.types import LLMMessage


def _fake_response(blocks, model="claude-test", input_tokens=20, output_tokens=8):
    return SimpleNamespace(
        content=blocks,
        model=model,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


@pytest.fixture
def mock_anthropic_client():
    with patch("anthropic.Anthropic") as mock_anthropic:
        yield mock_anthropic


def test_builds_code_execution_tool_payload(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [SimpleNamespace(type="text", text="Wynik: 1060.")]
    )

    complete_with_code_execution(
        "test-key", [LLMMessage.user("Zsumuj liczby pierwsze poniżej 100.")]
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tools"] == [
        {"type": "code_execution_20260521", "name": "code_execution"}
    ]


def test_parses_stdout_stderr_return_code_from_result_block(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    result_content = SimpleNamespace(
        type="code_execution_result", stdout="1060\n", stderr="", return_code=0
    )
    mock_client.messages.create.return_value = _fake_response(
        [
            SimpleNamespace(type="server_tool_use", id="srv_1", name="code_execution", input={}),
            SimpleNamespace(
                type="code_execution_tool_result", tool_use_id="srv_1", content=result_content
            ),
            SimpleNamespace(type="text", text="Suma wynosi 1060."),
        ]
    )

    outcome = complete_with_code_execution(
        "test-key", [LLMMessage.user("Zsumuj liczby pierwsze poniżej 100.")]
    )

    assert outcome.response.content == "Suma wynosi 1060."
    assert outcome.executions == [{"stdout": "1060\n", "stderr": "", "return_code": 0}]


def test_parses_execution_error_block(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    error_content = SimpleNamespace(
        type="code_execution_tool_result_error", error_code="execution_time_exceeded"
    )
    mock_client.messages.create.return_value = _fake_response(
        [
            SimpleNamespace(
                type="code_execution_tool_result", tool_use_id="srv_1", content=error_content
            ),
            SimpleNamespace(type="text", text="Wykonanie przekroczyło limit czasu."),
        ]
    )

    outcome = complete_with_code_execution("test-key", [LLMMessage.user("Uruchom pętlę.")])

    assert outcome.executions == [{"error_code": "execution_time_exceeded"}]


def test_no_execution_blocks_yields_empty_executions_list(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [SimpleNamespace(type="text", text="Cześć!")]
    )

    outcome = complete_with_code_execution("test-key", [LLMMessage.user("Cześć")])

    assert outcome.executions == []
    assert outcome.response.content == "Cześć!"


def test_system_prompt_and_max_tokens_passed_through(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [SimpleNamespace(type="text", text="ok")]
    )

    complete_with_code_execution(
        "test-key",
        [LLMMessage.user("Pytanie")],
        system="Jesteś asystentem do obliczeń.",
        max_tokens=2048,
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "Jesteś asystentem do obliczeń."
    assert call_kwargs["max_tokens"] == 2048
