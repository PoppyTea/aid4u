"""
S01E03 — proxy serwer dla operatora "Wojtek".

Odbiera POST /chat {sessionID, msg}, prowadzi rozmowę per-sesja przez LLMClient
(function calling: check_package, redirect_package — patrz tools.py). Historia
per sessionID trzymana w pamięci procesu — wystarczające dla jednej rozmowy z
botem grading; restart serwera czyści wszystkie sesje.

Uruchomienie lokalne:
    uv run python -m tasks.s01e03_proxy.server

Publiczny URL (żeby bot na hubie mógł się dobić):
    ./deploy/ngrok_tunnel.sh 8003
    → podaj wypisany https://*.ngrok-free.app URL botowi na hubie

Flaga: Wojtek przekazuje ją na końcu rozmowy w treści wiadomości, nie przez
osobny endpoint — wypatruj wzorca {FLG:...} w odpowiedziach z /chat.
"""

from __future__ import annotations

import os

from pydantic import BaseModel

from core.config import get_config
from core.llm import LLMClient, LLMMessage, create_provider
from core.observability.setup import setup_observability
from core.server import ServerFactory, run_server
from tasks.s01e03_proxy.packages_data import PackageStore
from tasks.s01e03_proxy.prompts import SYSTEM_PROMPT_PROXY
from tasks.s01e03_proxy.tools import TOOLS, make_tool_executor

setup_observability()

# Function calling działa zauważalnie lepiej na Sonnet niż na Haiku (drabina
# eskalacji, strategy/llm-selection.md) — ten agent musi konsekwentnie wybierać
# właściwe narzędzie z historii rozmowy, nie tylko odpowiadać na jedno pytanie.
_MODEL = os.getenv("S01E03_MODEL", "claude-sonnet-5")

app = ServerFactory.create("s01e03-proxy")

_sessions: dict[str, list[LLMMessage]] = {}
_store = PackageStore()
_tool_executor = make_tool_executor(_store)
_llm: LLMClient | None = None


def _get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        cfg = get_config()
        _llm = LLMClient(create_provider(_MODEL, cfg))
    return _llm


class ChatRequest(BaseModel):
    sessionID: str
    msg: str


class ChatResponse(BaseModel):
    msg: str


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    history = _sessions.setdefault(body.sessionID, [])
    history.append(LLMMessage.user(body.msg))

    reply = _get_llm().run_agent_loop(
        history, TOOLS, _tool_executor, system=SYSTEM_PROMPT_PROXY
    )

    history.append(LLMMessage.assistant(reply))
    return ChatResponse(msg=reply)


if __name__ == "__main__":
    run_server(app, port=int(os.getenv("S01E03_PORT", "8003")))
