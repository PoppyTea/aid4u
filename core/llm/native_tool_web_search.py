"""
Natywne narzędzie Anthropic: web_search.

Server-side — Anthropic wykonuje wyszukiwanie u siebie i zwraca wynik w tej samej
odpowiedzi (bez pętli klient-serwer, w przeciwieństwie do narzędzi client-side jak
bash czy text_editor). Świadomie POZA LLMProvider/LLMClient: to nie jest przenośna
funkcja (Gemini/OpenAI nie mają tego samego kształtu API), więc żyje jako osobna
funkcja narzędziowa używana wprost, gdy zadanie chce właśnie tej możliwości Anthropic.

Użycie:
    from core.llm.native_tool_web_search import complete_with_web_search

    response = complete_with_web_search(
        config.anthropic_key,
        [LLMMessage.user("Jaka jest aktualna stolica Polski?")],
    )
    print(response.content)
"""

from __future__ import annotations

from typing import Any

from core.llm.types import LLMMessage, LLMResponse

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_TOOL_TYPE = "web_search_20260318"


def complete_with_web_search(
    api_key: str,
    messages: list[LLMMessage],
    *,
    model: str = _DEFAULT_MODEL,
    system: str | None = None,
    max_tokens: int = 1024,
    max_uses: int = 5,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> LLMResponse:
    """
    Jedno wywołanie z natywnym narzędziem web_search.

    Args:
        max_uses: limit liczby wyszukiwań w jednym zapytaniu (koszt/czas).
        allowed_domains / blocked_domains: wzajemnie wykluczające się filtry domen.

    Returns:
        LLMResponse.content — finalna odpowiedź tekstowa modelu, już uwzględniająca
        wyniki wyszukiwania (Anthropic wplata je w odpowiedź przed zwróceniem).
    """
    import anthropic

    if allowed_domains and blocked_domains:
        raise ValueError("allowed_domains i blocked_domains wzajemnie się wykluczają")

    client = anthropic.Anthropic(api_key=api_key)

    tool: dict[str, Any] = {"type": _TOOL_TYPE, "name": "web_search", "max_uses": max_uses}
    if allowed_domains:
        tool["allowed_domains"] = allowed_domains
    if blocked_domains:
        tool["blocked_domains"] = blocked_domains

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "tools": [tool],
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)

    text = " ".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )

    return LLMResponse(
        content=text,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
