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

        assert isinstance(result, DummySchema)
        assert result.name == "Alice"
        assert result.age == 30


def test_complete_structured_markdown_json(adapter):
    expected_json = '```json\n{"name": "Bob", "age": 25}\n```'

    with patch.object(adapter, "complete") as mock_complete:
        mock_complete.return_value = LLMResponse(
            content=expected_json, model="claude-test", input_tokens=10, output_tokens=10
        )

        result = adapter.complete_structured(
            messages=[LLMMessage.user("Hello")], schema=DummySchema
        )

        assert isinstance(result, DummySchema)
        assert result.name == "Bob"
        assert result.age == 25


def test_complete_structured_markdown_no_lang(adapter):
    expected_json = '```\n{"name": "Charlie", "age": 40}\n```'

    with patch.object(adapter, "complete") as mock_complete:
        mock_complete.return_value = LLMResponse(
            content=expected_json, model="claude-test", input_tokens=10, output_tokens=10
        )

        result = adapter.complete_structured(
            messages=[LLMMessage.user("Hello")], schema=DummySchema
        )

        assert isinstance(result, DummySchema)
        assert result.name == "Charlie"
        assert result.age == 40


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
