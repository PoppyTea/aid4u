"""
S01E03 — proxy serwer dla operatora "Wojtek".

Odbiera POST /chat {sessionID, msg}, prowadzi rozmowę per-sesja przez LLMClient
(function calling: check_package, redirect_package — patrz tools.py, wywołuje
prawdziwe API hub.ag3nts.org/api/packages). Historia per sessionID trzymana w
pamięci procesu — wystarczające dla jednej rozmowy z botem grading; restart
serwera czyści wszystkie sesje.

Uruchomienie lokalne:
    uv run python -m tasks.s01e03_proxy.server

Publiczny URL (żeby bot na hubie mógł się dobić):
    ./deploy/ngrok_tunnel.sh 8003
    → zarejestruj wypisany https://*.ngrok-free.app URL, patrz solution.py

Flaga: Wojtek przekazuje ją na końcu rozmowy w treści wiadomości, nie przez
osobny endpoint — ten serwer loguje wyraźnie, gdy wzorzec {FLG:...} pojawi
się w przychodzącej wiadomości, żeby było łatwo ją wyłapać w logach.
"""

from __future__ import annotations

import os
import re

import logfire
from pydantic import BaseModel

from core.config import get_config
from core.hub import HubClient
from core.llm import LLMClient, LLMMessage, create_provider
from core.observability.setup import setup_observability
from core.server import ServerFactory, run_server
from tasks.s01e03_proxy.prompts import SYSTEM_PROMPT_PROXY
from tasks.s01e03_proxy.tools import TOOLS, make_tool_executor

setup_observability()

_FLAG_PATTERN = re.compile(r"\{FLG:[^}]+\}")

# Karta lekcji i komentarze uczestników zgodnie wskazują, że lekki model
# (Haiku / gpt-5-mini) wystarcza do tego zadania — eskaluj (S01E03_MODEL=
# claude-sonnet-5) tylko jeśli model gubi wywołania narzędzi albo miesza
# kontekst sesji.
_MODEL = os.getenv("S01E03_MODEL", "claude-haiku-4-5-20251001")

app = ServerFactory.create("s01e03-proxy")

_sessions: dict[str, list[LLMMessage]] = {}
_hub = HubClient()
_tool_executor = make_tool_executor(_hub)
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
    if _FLAG_PATTERN.search(body.msg):
        logfire.info("Flag detected in incoming message", session_id=body.sessionID, msg=body.msg)

    history = _sessions.setdefault(body.sessionID, [])
    history.append(LLMMessage.user(body.msg))

    reply = _get_llm().run_agent_loop(
        history, TOOLS, _tool_executor, system=SYSTEM_PROMPT_PROXY
    )

    history.append(LLMMessage.assistant(reply))
    return ChatResponse(msg=reply)


if __name__ == "__main__":
    run_server(app, port=int(os.getenv("S01E03_PORT", "8003")))
