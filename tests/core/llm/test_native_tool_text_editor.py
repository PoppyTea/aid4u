from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.llm.native_tool_text_editor import TextEditorToolExecutor, run_text_editor_tool_loop


class FakeBlock(SimpleNamespace):
    def model_dump(self) -> dict:
        return dict(self.__dict__)


def _fake_response(blocks, model="claude-test", input_tokens=10, output_tokens=5):
    return SimpleNamespace(
        content=blocks,
        model=model,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


# ─── TextEditorToolExecutor ────────────────────────────────────────────────


def test_create_and_view_roundtrip(tmp_path):
    executor = TextEditorToolExecutor(root=str(tmp_path))

    create_result = executor({"command": "create", "path": "notes.txt", "file_text": "linia 1\nlinia 2"})
    assert "notes.txt" in create_result

    view_result = executor({"command": "view", "path": "notes.txt"})
    assert view_result == "1: linia 1\n2: linia 2"


def test_view_respects_view_range(tmp_path):
    executor = TextEditorToolExecutor(root=str(tmp_path))
    executor({"command": "create", "path": "f.txt", "file_text": "a\nb\nc\nd"})

    result = executor({"command": "view", "path": "f.txt", "view_range": [2, 3]})

    assert result == "2: b\n3: c"


def test_str_replace_unique_match(tmp_path):
    executor = TextEditorToolExecutor(root=str(tmp_path))
    executor({"command": "create", "path": "f.txt", "file_text": "hello wrold"})

    executor({"command": "str_replace", "path": "f.txt", "old_str": "wrold", "new_str": "world"})

    assert (tmp_path / "f.txt").read_text() == "hello world"


def test_str_replace_raises_when_old_str_missing(tmp_path):
    executor = TextEditorToolExecutor(root=str(tmp_path))
    executor({"command": "create", "path": "f.txt", "file_text": "hello"})

    with pytest.raises(ValueError, match="nie znaleziony"):
        executor({"command": "str_replace", "path": "f.txt", "old_str": "xyz", "new_str": "abc"})


def test_str_replace_raises_when_old_str_not_unique(tmp_path):
    executor = TextEditorToolExecutor(root=str(tmp_path))
    executor({"command": "create", "path": "f.txt", "file_text": "abc abc"})

    with pytest.raises(ValueError, match="unikalny"):
        executor({"command": "str_replace", "path": "f.txt", "old_str": "abc", "new_str": "xyz"})


def test_insert_adds_line_at_position(tmp_path):
    executor = TextEditorToolExecutor(root=str(tmp_path))
    executor({"command": "create", "path": "f.txt", "file_text": "a\nb\nc"})

    executor({"command": "insert", "path": "f.txt", "insert_line": 1, "new_str": "NEW"})

    assert (tmp_path / "f.txt").read_text() == "a\nNEW\nb\nc\n"


def test_path_traversal_outside_root_is_blocked(tmp_path):
    executor = TextEditorToolExecutor(root=str(tmp_path))

    with pytest.raises(ValueError, match="poza dozwolonym katalogiem"):
        executor({"command": "view", "path": "../../etc/passwd"})


def test_view_directory_lists_names(tmp_path):
    (tmp_path / "b.txt").write_text("")
    (tmp_path / "a.txt").write_text("")
    executor = TextEditorToolExecutor(root=str(tmp_path))

    result = executor({"command": "view", "path": "."})

    assert result == "a.txt\nb.txt"


def test_unknown_command_raises(tmp_path):
    executor = TextEditorToolExecutor(root=str(tmp_path))

    with pytest.raises(ValueError, match="Nieznane polecenie"):
        executor({"command": "delete", "path": "f.txt"})


# ─── run_text_editor_tool_loop ─────────────────────────────────────────────


@pytest.fixture
def mock_anthropic_client():
    with patch("anthropic.Anthropic") as mock_anthropic:
        yield mock_anthropic


def test_returns_immediately_when_no_tool_use(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [FakeBlock(type="text", text="Nie trzeba edytować plików.")]
    )

    response = run_text_editor_tool_loop("test-key", "Cześć", executor=lambda inp: "unused")

    assert response.content == "Nie trzeba edytować plików."
    assert mock_client.messages.create.call_count == 1


def test_executes_tool_and_sends_tool_result_back(mock_anthropic_client, tmp_path):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    tool_use = FakeBlock(
        type="tool_use",
        id="toolu_1",
        name="str_replace_based_edit_tool",
        input={"command": "create", "path": "notes.txt", "file_text": "hi"},
    )
    mock_client.messages.create.side_effect = [
        _fake_response([tool_use]),
        _fake_response([FakeBlock(type="text", text="Plik utworzony.")]),
    ]

    executor = TextEditorToolExecutor(root=str(tmp_path))
    response = run_text_editor_tool_loop("test-key", "Utwórz notes.txt", executor=executor)

    assert response.content == "Plik utworzony."
    assert (tmp_path / "notes.txt").read_text() == "hi"

    second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result_turn = second_call_messages[-1]["content"][0]
    assert tool_result_turn["tool_use_id"] == "toolu_1"
    assert "notes.txt" in tool_result_turn["content"]


def test_executor_exception_becomes_error_tool_result(mock_anthropic_client, tmp_path):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    tool_use = FakeBlock(
        type="tool_use",
        id="toolu_2",
        name="str_replace_based_edit_tool",
        input={"command": "view", "path": "missing.txt"},
    )
    mock_client.messages.create.side_effect = [
        _fake_response([tool_use]),
        _fake_response([FakeBlock(type="text", text="done")]),
    ]

    run_text_editor_tool_loop(
        "test-key", "prompt", executor=TextEditorToolExecutor(root=str(tmp_path))
    )

    second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result = second_call_messages[-1]["content"][0]
    assert tool_result["is_error"] is True


def test_stops_after_max_iterations(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    tool_use = FakeBlock(
        type="tool_use",
        id="toolu_loop",
        name="str_replace_based_edit_tool",
        input={"command": "view", "path": "f.txt"},
    )
    mock_client.messages.create.return_value = _fake_response([tool_use])

    run_text_editor_tool_loop(
        "test-key", "loop forever", executor=lambda inp: "x", max_iterations=3
    )

    assert mock_client.messages.create.call_count == 3
