from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel, ValidationError
import json

from core.llm.adapters.anthropic import AnthropicAdapter
from core.llm.types import LLMMessage, LLMResponse


class DummySchema(BaseModel):
    name: str
    age: int


@pytest.fixture
def mock_anthropic_client():
    with patch("anthropic.Anthropic") as mock_anthropic:
        yield mock_anthropic


@pytest.fixture
def adapter(mock_anthropic_client):
    return AnthropicAdapter(api_key="test-key")


def test_complete_structured_plain_json(adapter):
    # Setup mock for complete
    expected_json = '{"name": "Alice", "age": 30}'

    with patch.object(adapter, "complete") as mock_complete:
        mock_complete.return_value = LLMResponse(
            content=expected_json, model="claude-test", input_tokens=10, output_tokens=10
        )

        result = adapter.complete_structured(
            messages=[LLMMessage.user("Hello")], schema=DummySchema
        )

        assert isinstance(result, LLMResponse)
        assert isinstance(result.parsed, DummySchema)
        assert result.parsed.name == "Alice"
        assert result.parsed.age == 30


def test_complete_structured_markdown_json(adapter):
    expected_json = '```json\n{"name": "Bob", "age": 25}\n```'

    with patch.object(adapter, "complete") as mock_complete:
        mock_complete.return_value = LLMResponse(
            content=expected_json, model="claude-test", input_tokens=10, output_tokens=10
        )

        result = adapter.complete_structured(
            messages=[LLMMessage.user("Hello")], schema=DummySchema
        )

        assert isinstance(result.parsed, DummySchema)
        assert result.parsed.name == "Bob"
        assert result.parsed.age == 25


def test_complete_structured_markdown_uppercase_json_language_tag(adapter):
    """Regresja: `.lstrip("```json")` (usunięte) stripował po zbiorze znaków, nie substringu
    — dla `` ```JSON `` zostawiał literalne "JSON\\n" przed danymi. Case-insensitive check naprawia to."""
    expected_json = '```JSON\n{"name": "Zoe", "age": 22}\n```'

    with patch.object(adapter, "complete") as mock_complete:
        mock_complete.return_value = LLMResponse(
            content=expected_json, model="claude-test", input_tokens=10, output_tokens=10
        )

        result = adapter.complete_structured(
            messages=[LLMMessage.user("Hello")], schema=DummySchema
        )

        assert isinstance(result.parsed, DummySchema)
        assert result.parsed.name == "Zoe"
        assert result.parsed.age == 22


def test_complete_structured_markdown_no_lang(adapter):
    expected_json = '```\n{"name": "Charlie", "age": 40}\n```'

    with patch.object(adapter, "complete") as mock_complete:
        mock_complete.return_value = LLMResponse(
            content=expected_json, model="claude-test", input_tokens=10, output_tokens=10
        )

        result = adapter.complete_structured(
            messages=[LLMMessage.user("Hello")], schema=DummySchema
        )

        assert isinstance(result.parsed, DummySchema)
        assert result.parsed.name == "Charlie"
        assert result.parsed.age == 40


def test_complete_structured_system_prompt_formatting(adapter):
    expected_json = '{"name": "Dave", "age": 50}'

    with patch.object(adapter, "complete") as mock_complete:
        mock_complete.return_value = LLMResponse(
            content=expected_json, model="claude-test", input_tokens=10, output_tokens=10
        )

        adapter.complete_structured(
            messages=[LLMMessage.user("Hello")],
            schema=DummySchema,
            system="Be a helpful assistant.",
        )

        mock_complete.assert_called_once()
        call_kwargs = mock_complete.call_args.kwargs
        assert "Be a helpful assistant." in call_kwargs["system"]
        assert "Respond ONLY with valid JSON" in call_kwargs["system"]
        assert "DummySchema" in call_kwargs["system"]
        assert call_kwargs["max_tokens"] == 4096


def test_complete_structured_invalid_json(adapter):
    expected_json = '```json\n{"name": "Eve", "age": "thirty"}\n```'  # invalid age

    with patch.object(adapter, "complete") as mock_complete:
        mock_complete.return_value = LLMResponse(
            content=expected_json, model="claude-test", input_tokens=10, output_tokens=10
        )

        with pytest.raises(ValidationError):
            adapter.complete_structured(messages=[LLMMessage.user("Hello")], schema=DummySchema)


def test_thinking_block_before_text_does_not_break_extraction():
    """
    Regresja zmierzona 2026-08-23: przy włączonym myśleniu Anthropic zwraca
    `ThinkingBlock` jako `content[0]`, a ten nie ma `.text`. Ślepe `content[0].text`
    dawało `AttributeError` w środku przebiegu. Testy jednostkowe tego nie widziały,
    bo atrapy zwracały pojedynczy blok tekstowy — złapane dopiero żywym wywołaniem.
    """
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    from core.llm.adapters.anthropic import AnthropicAdapter
    from core.llm.types import LLMMessage

    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="thinking", thinking="rozumowanie modelu"),
            SimpleNamespace(type="text", text="właściwa odpowiedź"),
        ],
        model="claude-test",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )
    with patch("anthropic.Anthropic") as mock_anthropic:
        client = MagicMock()
        mock_anthropic.return_value = client
        client.messages.create.return_value = response

        adapter = AnthropicAdapter(api_key="k")
        result = adapter.complete([LLMMessage.user("hi")], max_tokens=3000, thinking="low")

    assert result.content == "właściwa odpowiedź"
    assert client.messages.create.call_args.kwargs["thinking"] == {
        "type": "enabled",
        "budget_tokens": 1024,
    }
