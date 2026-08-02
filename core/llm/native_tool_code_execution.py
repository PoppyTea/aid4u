"""
Natywne narzędzie Anthropic: code_execution.

Server-side, jak web_search — Anthropic uruchamia kod w swoim sandboxie i zwraca
wynik (stdout/stderr/return_code) w tej samej odpowiedzi, bez pętli klient-serwer.
Wersja 20260521 ma trwały stan REPL między wywołaniami tego narzędzia w jednej
rozmowie. Świadomie POZA LLMProvider/LLMClient — patrz native_tool_web_search.py
po uzasadnienie (Anthropic-only, nie przenośne między providerami).

Użycie:
    from core.llm.native_tool_code_execution import complete_with_code_execution

    outcome = complete_with_code_execution(
        config.anthropic_key,
        [LLMMessage.user("Policz sumę liczb pierwszych poniżej 100 w Pythonie.")],
    )
    print(outcome.response.content)
    for execution in outcome.executions:
        print(execution.get("stdout"))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from core.llm.adapters.anthropic import ANTHROPIC_MODELS
from core.llm.types import LLMMessage, LLMResponse

_TOOL_TYPE = "code_execution_20260521"


@lru_cache(maxsize=8)
def _get_client(api_key: str) -> Any:
    """Cache clients by API key — reuses the underlying HTTP transport across calls."""
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def _build_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    for m in messages:
        if m.role == "system":
            raise ValueError(
                "LLMMessage(role='system') is not supported in `messages` here — "
                "pass the system prompt via the `system=` parameter instead."
            )
    return [{"role": m.role, "content": m.content} for m in messages]


@dataclass
class CodeExecutionOutcome:
    """
    Wynik wywołania z code_execution.

    `response.content` to finalna odpowiedź tekstowa modelu (podsumowanie).
    `executions` to surowe wyniki każdego uruchomienia kodu w tej odpowiedzi —
    {"stdout", "stderr", "return_code"} przy sukcesie, {"error_code"} przy błędzie
    (np. przekroczony limit czasu w sandboxie).
    """

    response: LLMResponse
    executions: list[dict[str, Any]] = field(default_factory=list)


def complete_with_code_execution(
    api_key: str,
    messages: list[LLMMessage],
    *,
    model: str = ANTHROPIC_MODELS["fast"],
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> CodeExecutionOutcome:
    """Jedno wywołanie z natywnym narzędziem code_execution."""
    client = _get_client(api_key)

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "tools": [{"type": _TOOL_TYPE, "name": "code_execution"}],
        "messages": _build_messages(messages),
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)

    text_parts: list[str] = []
    executions: list[dict[str, Any]] = []

    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(block.text)
        elif block_type == "code_execution_tool_result":
            content = block.content
            content_type = getattr(content, "type", None)
            if content_type == "code_execution_result":
                executions.append(
                    {
                        "stdout": content.stdout,
                        "stderr": content.stderr,
                        "return_code": content.return_code,
                    }
                )
            elif content_type == "code_execution_tool_result_error":
                executions.append({"error_code": content.error_code})

    llm_response = LLMResponse(
        content=" ".join(text_parts),
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
    return CodeExecutionOutcome(response=llm_response, executions=executions)
