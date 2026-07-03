"""Integration tests for GeminiAdapter."""
from __future__ import annotations

import os
import pytest
from pydantic import BaseModel
from core.llm.adapters.gemini import GeminiAdapter
from core.llm.types import LLMMessage

class UserSchema(BaseModel):
    name: str
    age: int

@pytest.mark.integration
def test_gemini_complete():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not found")
        
    adapter = GeminiAdapter(api_key=api_key)
    messages = [LLMMessage.user("Say exactly 'Hello World'")]
    
    response = adapter.complete(messages)
    
    assert "Hello World" in response.content
    assert response.model == "gemini-2.5-flash"
    assert response.input_tokens > 0
    assert response.output_tokens > 0

@pytest.mark.integration
def test_gemini_complete_structured():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not found")
        
    adapter = GeminiAdapter(api_key=api_key)
    messages = [LLMMessage.user("Name: John, Age: 30")]
    
    result = adapter.complete_structured(messages, UserSchema)
    
    assert isinstance(result, UserSchema)
    assert result.name == "John"
    assert result.age == 30

@pytest.mark.integration
def test_gemini_with_system_prompt():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not found")
        
    adapter = GeminiAdapter(api_key=api_key)
    messages = [LLMMessage.user("Who are you?")]
    system = "You are a specialized bot named AID4U-TEST."
    
    response = adapter.complete(messages, system=system)
    
    assert "AID4U-TEST" in response.content.upper()
