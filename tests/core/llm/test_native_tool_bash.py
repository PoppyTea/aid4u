from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.llm.native_tool_bash import (
    AgentLoopIncomplete,
    BashToolExecutor,
    _get_client,
    run_bash_tool_loop,
)


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


@pytest.fixture(autouse=True)
def _clear_client_cache():
    _get_client.cache_clear()
    yield
    _get_client.cache_clear()


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

    with pytest.raises(AgentLoopIncomplete, match="max_iterations=3"):
        run_bash_tool_loop("test-key", "loop forever", executor=lambda cmd: "x", max_iterations=3)

    assert mock_client.messages.create.call_count == 3


def test_missing_input_attribute_is_treated_as_noop_not_a_crash(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    # No `.input` attribute at all — pre-fix, `block.input.get(...)` crashed here
    # with AttributeError instead of reaching the try/except.
    no_input = FakeBlock(type="tool_use", id="toolu_bad", name="bash")
    mock_client.messages.create.side_effect = [
        _fake_response([no_input]),
        _fake_response([FakeBlock(type="text", text="done")]),
    ]

    response = run_bash_tool_loop("test-key", "prompt", executor=lambda cmd: "unused")

    assert response.content == "done"  # loop completed instead of crashing
    second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result = second_call_messages[-1]["content"][0]
    assert tool_result["tool_use_id"] == "toolu_bad"
    assert "is_error" not in tool_result  # no command → noop, not an error


def test_non_dict_input_becomes_error_result_not_a_crash(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    # `.input` present but not dict-like — pre-fix this also crashed outside the try.
    bad_shape = FakeBlock(type="tool_use", id="toolu_bad2", name="bash", input="not-a-dict")
    mock_client.messages.create.side_effect = [
        _fake_response([bad_shape]),
        _fake_response([FakeBlock(type="text", text="done")]),
    ]

    run_bash_tool_loop("test-key", "prompt", executor=lambda cmd: "unused")

    second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result = second_call_messages[-1]["content"][0]
    assert tool_result["is_error"] is True
    assert tool_result["tool_use_id"] == "toolu_bad2"


def test_default_model_comes_from_anthropic_models_fast(mock_anthropic_client):
    from core.llm.adapters.anthropic import ANTHROPIC_MODELS

    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [FakeBlock(type="text", text="ok")]
    )

    run_bash_tool_loop("test-key", "prompt", executor=lambda cmd: "unused")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == ANTHROPIC_MODELS["fast"]


def test_temperature_is_never_sent(mock_anthropic_client):
    """
    anthropic 1.0.0 usunęło `temperature` z metod `messages` — wysłanie go daje
    `TypeError: Messages.create() got an unexpected keyword argument 'temperature'`
    (zmierzone 2026-08-23). Kontrakt odwrócony: wcześniej ten test wymagał, żeby
    parametr był przekazywany.
    """
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [FakeBlock(type="text", text="ok")]
    )

    run_bash_tool_loop("test-key", "prompt", executor=lambda cmd: "unused")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "temperature" not in call_kwargs


def test_client_is_reused_across_calls_with_same_api_key(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [FakeBlock(type="text", text="ok")]
    )

    run_bash_tool_loop("same-key", "prompt 1", executor=lambda cmd: "unused")
    run_bash_tool_loop("same-key", "prompt 2", executor=lambda cmd: "unused")

    mock_anthropic_client.assert_called_once_with(api_key="same-key")


def test_bash_tool_executor_invokes_bash_explicitly_not_shell_true(tmp_path):
    executor = BashToolExecutor(cwd=str(tmp_path), timeout=5.0)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = SimpleNamespace(stdout="", stderr="", returncode=0)
        executor("echo hi")

    args, kwargs = mock_run.call_args
    assert args[0] == ["bash", "-c", "echo hi"]
    assert "shell" not in kwargs


def test_bash_tool_executor_defaults_to_fresh_tempdir_not_none(tmp_path):
    executor = BashToolExecutor(timeout=5.0)

    assert executor.cwd is not None
    assert executor.cwd != str(tmp_path)  # sanity: not accidentally reusing the test's tmp_path

    output = executor("pwd")

    assert executor.cwd in output


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
