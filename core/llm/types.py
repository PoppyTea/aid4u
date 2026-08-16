"""Wspólne typy danych warstwy LLM. Niezależne od providera."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel


@dataclass
class LLMMessage:
    role: Literal["user", "assistant", "system"]
    content: str

    @staticmethod
    def user(content: str) -> "LLMMessage":
        return LLMMessage(role="user", content=content)

    @staticmethod
    def assistant(content: str) -> "LLMMessage":
        return LLMMessage(role="assistant", content=content)

    @staticmethod
    def system(content: str) -> "LLMMessage":
        return LLMMessage(role="system", content=content)


@dataclass
class Tool:
    """Definicja narzędzia dla function calling."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass
class ToolCall:
    """Wywołanie narzędzia przez model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """Wynik wykonania narzędzia."""

    tool_call_id: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    tool_calls: list[ToolCall] = field(default_factory=list)
    parsed: BaseModel | None = None
    """
    Wypełnione WYŁĄCZNIE przez `complete_structured()` — instancja Pydantic modelu
    (schematu) wygenerowana przez model. `content` w tym przypadku trzyma JSON-ową
    reprezentację tej samej wartości (do podglądu w Langfuse/Logfire), nie osobną
    treść. Pozwala structured output przejść przez ten sam łańcuch middleware co
    `complete()`/`complete_with_tools()` bez zmiany kontraktu `LLMMiddleware.handle()`.
    """

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)
