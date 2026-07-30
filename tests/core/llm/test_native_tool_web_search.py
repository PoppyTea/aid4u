from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.llm.native_tool_web_search import complete_with_web_search
from core.llm.types import LLMMessage


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


def test_builds_web_search_tool_payload(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [SimpleNamespace(type="text", text="Warszawa.")]
    )

    complete_with_web_search(
        "test-key",
        [LLMMessage.user("Jaka jest stolica Polski?")],
        max_uses=3,
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tools"] == [
        {"type": "web_search_20260318", "name": "web_search", "max_uses": 3}
    ]
    assert call_kwargs["messages"] == [
        {"role": "user", "content": "Jaka jest stolica Polski?"}
    ]


def test_parses_only_text_blocks_ignoring_server_tool_blocks(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [
            SimpleNamespace(type="server_tool_use", id="srv_1", name="web_search", input={}),
            SimpleNamespace(type="web_search_tool_result", tool_use_id="srv_1", content=[]),
            SimpleNamespace(type="text", text="Stolicą Polski jest Warszawa."),
        ]
    )

    result = complete_with_web_search("test-key", [LLMMessage.user("Pytanie")])

    assert result.content == "Stolicą Polski jest Warszawa."
    assert result.model == "claude-test"
    assert result.input_tokens == 10
    assert result.output_tokens == 5


def test_joins_multiple_text_blocks_with_space(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [
            SimpleNamespace(type="text", text="Część pierwsza."),
            SimpleNamespace(type="text", text="Część druga."),
        ]
    )

    result = complete_with_web_search("test-key", [LLMMessage.user("Pytanie")])

    assert result.content == "Część pierwsza. Część druga."


def test_allowed_and_blocked_domains_are_mutually_exclusive(mock_anthropic_client):
    with pytest.raises(ValueError):
        complete_with_web_search(
            "test-key",
            [LLMMessage.user("Pytanie")],
            allowed_domains=["example.com"],
            blocked_domains=["spam.example"],
        )


def test_allowed_domains_passed_through_to_tool_payload(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [SimpleNamespace(type="text", text="ok")]
    )

    complete_with_web_search(
        "test-key",
        [LLMMessage.user("Pytanie")],
        allowed_domains=["ag3nts.org"],
    )

    tool_payload = mock_client.messages.create.call_args.kwargs["tools"][0]
    assert tool_payload["allowed_domains"] == ["ag3nts.org"]
    assert "blocked_domains" not in tool_payload


def test_system_prompt_passed_through(mock_anthropic_client):
    mock_client = MagicMock()
    mock_anthropic_client.return_value = mock_client
    mock_client.messages.create.return_value = _fake_response(
        [SimpleNamespace(type="text", text="ok")]
    )

    complete_with_web_search(
        "test-key",
        [LLMMessage.user("Pytanie")],
        system="Odpowiadaj po polsku.",
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "Odpowiadaj po polsku."
