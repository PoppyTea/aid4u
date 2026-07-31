from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.llm.native_tool_bash import BashToolExecutor, run_bash_tool_loop


class FakeBlock(SimpleNamespace):
    def model_dump(self) -> dict:
        return dict(self.__dict__)


def _fake_response(blocks, model="claude-test", input_tokens=10, output_tokens=5):
    return SimpleNamespace(
        content=blocks,
        model=model,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


@pytest.fixture
def mock_anthropic_client():
    with patch("anthropic.Anthropic") as mock_anthropic:
        yield mock_anthropic


def test_returns_immediately_when_no_tool_use(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [FakeBlock(type="text", text="Cześć, w czym mogę pomóc?")]
    )

    response = run_bash_tool_loop("test-key", "Cześć", executor=lambda cmd: "unused")

    assert response.content == "Cześć, w czym mogę pomóc?"
    assert mock_client.messages.create.call_count == 1


def test_executes_bash_command_and_sends_tool_result_back(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    tool_use = FakeBlock(type="tool_use", id="toolu_1", name="bash", input={"command": "echo hi"})
    mock_client.messages.create.side_effect = [
        _fake_response([tool_use]),
        _fake_response([FakeBlock(type="text", text="Wypisano 'hi'.")]),
    ]

    executor = MagicMock(return_value="hi\n")
    response = run_bash_tool_loop("test-key", "Wypisz hi", executor=executor)

    executor.assert_called_once_with("echo hi")
    assert response.content == "Wypisano 'hi'."
    assert mock_client.messages.create.call_count == 2

    second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result_turn = second_call_messages[-1]
    assert tool_result_turn["role"] == "user"
    assert tool_result_turn["content"] == [
        {"type": "tool_result", "tool_use_id": "toolu_1", "content": "hi\n"}
    ]


def test_executor_exception_becomes_error_tool_result(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    tool_use = FakeBlock(type="tool_use", id="toolu_2", name="bash", input={"command": "boom"})
    mock_client.messages.create.side_effect = [
        _fake_response([tool_use]),
        _fake_response([FakeBlock(type="text", text="done")]),
    ]

    def failing_executor(command: str) -> str:
        raise RuntimeError("sandbox unavailable")

    run_bash_tool_loop("test-key", "prompt", executor=failing_executor)

    second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result = second_call_messages[-1]["content"][0]
    assert tool_result["is_error"] is True
    assert "sandbox unavailable" in tool_result["content"]


def test_restart_input_without_command_is_a_noop(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    tool_use = FakeBlock(type="tool_use", id="toolu_3", name="bash", input={"restart": True})
    mock_client.messages.create.side_effect = [
        _fake_response([tool_use]),
        _fake_response([FakeBlock(type="text", text="ok")]),
    ]

    executor = MagicMock(return_value="should not be called")
    run_bash_tool_loop("test-key", "restart the shell", executor=executor)

    executor.assert_not_called()


def test_stops_after_max_iterations(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    tool_use = FakeBlock(type="tool_use", id="toolu_loop", name="bash", input={"command": "date"})
    mock_client.messages.create.return_value = _fake_response([tool_use])

    run_bash_tool_loop("test-key", "loop forever", executor=lambda cmd: "x", max_iterations=3)

    assert mock_client.messages.create.call_count == 3


def test_bash_tool_executor_runs_real_subprocess(tmp_path):
    executor = BashToolExecutor(cwd=str(tmp_path), timeout=5.0)

    output = executor("echo hello-from-bash-tool")

    assert "hello-from-bash-tool" in output


def test_bash_tool_executor_reports_nonzero_exit_code(tmp_path):
    executor = BashToolExecutor(cwd=str(tmp_path), timeout=5.0)

    output = executor("exit 7")

    assert "[exit code 7]" in output


def test_bash_tool_executor_times_out(tmp_path):
    executor = BashToolExecutor(cwd=str(tmp_path), timeout=0.2)

    output = executor("sleep 5")

    assert "timed out" in output
