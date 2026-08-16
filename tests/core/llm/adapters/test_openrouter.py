from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

from core.llm.adapters.openrouter import OpenRouterAdapter
from core.llm.types import LLMMessage, LLMResponse


class DummySchema(BaseModel):
    name: str
    age: int


@pytest.fixture
def mock_openai_client():
    with patch("openai.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        yield mock_openai, mock_client


def test_openrouter_adapter_init(mock_openai_client) -> None:
    mock_openai, mock_client = mock_openai_client

    # Case 1: Model with openrouter/ prefix
    adapter = OpenRouterAdapter(api_key="test-key", model="openrouter/meta-llama/llama-3-8b")

    mock_openai.assert_called_once_with(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
    )
    assert adapter.model_name == "meta-llama/llama-3-8b"

    # Reset mock and test Case 2: Model without openrouter/ prefix
    mock_openai.reset_mock()
    adapter2 = OpenRouterAdapter(api_key="test-key2", model="meta-llama/llama-3-8b")

    mock_openai.assert_called_once_with(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key2",
    )
    assert adapter2.model_name == "meta-llama/llama-3-8b"


def test_openrouter_adapter_init_case_insensitive(mock_openai_client) -> None:
    mock_openai, mock_client = mock_openai_client

    # Case 3: Mixed case prefix OPENROUTER/
    adapter = OpenRouterAdapter(api_key="test-key", model="OPENROUTER/meta-llama/llama-3-8b")
    assert adapter.model_name == "meta-llama/llama-3-8b"


def test_openrouter_adapter_complete(mock_openai_client) -> None:
    mock_openai, mock_client = mock_openai_client
    adapter = OpenRouterAdapter(api_key="test-key", model="openrouter/meta-llama/llama-3-8b")

    # Mock chat.completions.create response
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello from OpenRouter!"
    mock_response.choices = [mock_choice]
    mock_response.model = "meta-llama/llama-3-8b"
    mock_response.usage.prompt_tokens = 15
    mock_response.usage.completion_tokens = 10
    mock_client.chat.completions.create.return_value = mock_response

    messages = [LLMMessage.user("Hello")]
    response = adapter.complete(messages, system="You are a helper")

    # Verify that mock_client.chat.completions.create was called with correct args
    mock_client.chat.completions.create.assert_called_once_with(
        model="meta-llama/llama-3-8b",
        messages=[
            {"role": "system", "content": "You are a helper"},
            {"role": "user", "content": "Hello"},
        ],
        max_tokens=1024,
        temperature=0.0,
    )

    # Verify response
    assert isinstance(response, LLMResponse)
    assert response.content == "Hello from OpenRouter!"
    assert response.model == "meta-llama/llama-3-8b"
    assert response.input_tokens == 15
    assert response.output_tokens == 10


def test_openrouter_adapter_complete_structured(mock_openai_client) -> None:
    mock_openai, mock_client = mock_openai_client
    adapter = OpenRouterAdapter(api_key="test-key", model="openrouter/meta-llama/llama-3-8b")

    expected_json = '{"name": "Alice", "age": 30}'

    # Mock complete method of adapter to avoid complex nested mocks
    with patch.object(adapter, "complete") as mock_complete:
        mock_complete.return_value = LLMResponse(
            content=expected_json,
            model="meta-llama/llama-3-8b",
            input_tokens=10,
            output_tokens=10,
        )

        result = adapter.complete_structured(
            messages=[LLMMessage.user("Parse this")],
            schema=DummySchema,
            system="Be precise",
        )

        assert isinstance(result.parsed, DummySchema)
        assert result.parsed.name == "Alice"
        assert result.parsed.age == 30

        mock_complete.assert_called_once()
        call_kwargs = mock_complete.call_args.kwargs
        assert "Be precise" in call_kwargs["system"]
        assert "Respond ONLY with JSON" in call_kwargs["system"]
        assert "DummySchema" in call_kwargs["system"]
