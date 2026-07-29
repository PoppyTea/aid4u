"""
Strategy pattern — interfejs LLMProvider.

Każdy adapter (Anthropic, OpenAI, Gemini) implementuje ten protokół.
Kod zadań operuje wyłącznie na LLMProvider — nie wie nic o konkretnym SDK.

Dzięki temu zmiana providera = zmiana jednej linii w run.py:
    --model gemini-2.5-flash    →  GeminiAdapter
    --model claude-sonnet-5     →  AnthropicAdapter
    --model gpt-5.4-nano        →  OpenAIAdapter
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from core.llm.types import LLMMessage, LLMResponse, Tool, ToolResult

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Interfejs Strategy — każdy provider go implementuje."""

    @abstractmethod
    def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Jedno wywołanie tekstowe."""
        ...

    @abstractmethod
    def complete_structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        """Wywołanie ze strukturyzowanym wyjściem (Pydantic model)."""
        ...

    @abstractmethod
    def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[Tool],
        *,
        system: str | None = None,
    ) -> LLMResponse:
        """Pojedyncze wywołanie z dostępem do narzędzi.
        Zwraca tool_calls jeśli model chce użyć narzędzi.
        Pętla agentowa realizowana jest przez LLMClient.run_agent_loop().
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Pełna nazwa modelu, np. 'gemini-2.5-flash'."""
        ...
