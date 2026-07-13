import pytest
from unittest.mock import MagicMock
from core.llm.adapters.gemini import GeminiAdapter
from core.llm.types import LLMMessage, Tool


def test_gemini_complete_with_tools_unit():
    adapter = GeminiAdapter(api_key="dummy")

    # Mock client
    mock_client = MagicMock()
    mock_response = MagicMock()

    # Setup mock response to use modern gemini SDK format
    from google.genai import types

    mock_part = types.Part(
        function_call=types.FunctionCall(
            name="get_weather", args={"location": "London"}, id="call_123"
        )
    )
    mock_content = types.Content(parts=[mock_part])
    mock_candidate = types.Candidate(content=mock_content)

    mock_response.candidates = [mock_candidate]
    mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

    mock_client.models.generate_content.return_value = mock_response
    adapter._client = mock_client

    t = Tool(
        name="get_weather",
        description="Gets the current weather for a location",
        parameters={
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    )

    messages = [LLMMessage.user("What's the weather like in London?")]

    response = adapter.complete_with_tools(messages, [t])

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "get_weather"
    assert response.tool_calls[0].arguments == {"location": "London"}
    assert response.tool_calls[0].id == "call_123"
    assert response.content == ""
    assert response.input_tokens == 10
    assert response.output_tokens == 5
