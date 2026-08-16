import os
import sys
from pydantic import BaseModel


# Dodajemy katalog główny do sys.path, aby importy działały
sys.path.append(os.getcwd())

from core.secrets import SecretsManager

from core.llm.adapters.gemini import GeminiAdapter
from core.llm.types import LLMMessage


class UserSchema(BaseModel):
    name: str
    age: int


def run_manual_test():
    secret = SecretsManager()
    api_key = secret.get("GEMINI_API_KEY")
    if not api_key:
        print("SKIP: GEMINI_API_KEY not found")
        return

    print("--- Testing GeminiAdapter.complete ---")
    adapter = GeminiAdapter(api_key=api_key)
    messages = [LLMMessage.user("Say exactly 'Hello World'")]
    response = adapter.complete(messages)
    print(f"Content: {response.content}")
    print(f"Model: {response.model}")
    print(f"Usage: {response.input_tokens} in / {response.output_tokens} out")

    if "Hello World" in response.content:
        print("SUCCESS: complete")
    else:
        print("FAILED: complete")

    print("\n--- Testing GeminiAdapter.complete_structured ---")
    messages = [LLMMessage.user("Name: John, Age: 30. Respond only with JSON.")]
    response = adapter.complete_structured(messages, UserSchema)
    print(f"Parsed: {response.parsed}")

    if isinstance(response.parsed, UserSchema) and response.parsed.name == "John" and response.parsed.age == 30:
        print("SUCCESS: complete_structured")
    else:
        print("FAILED: complete_structured")

    print("\n--- Testing GeminiAdapter with system_instruction ---")
    messages = [LLMMessage.user("Who are you?")]
    system = "You are a specialized bot named AID4U-TEST."
    response = adapter.complete(messages, system=system)
    print(f"Content: {response.content}")

    if "AID4U-TEST" in response.content.upper():
        print("SUCCESS: system_instruction")
    else:
        print("FAILED: system_instruction")


if __name__ == "__main__":
    run_manual_test()
