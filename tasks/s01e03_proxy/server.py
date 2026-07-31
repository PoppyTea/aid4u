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

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import os
import re
from collections import OrderedDict

import logfire
from pydantic import BaseModel

from core.config import get_config
from core.hub import HubClient
from core.llm import LLMClient, LLMMessage, create_provider
from core.llm.adapters.anthropic import ANTHROPIC_MODELS
from core.server import ServerFactory, run_server
from tasks.s01e03_proxy.prompts import SYSTEM_PROMPT_PROXY
from tasks.s01e03_proxy.tools import TOOLS, make_tool_executor

_FLAG_PATTERN = re.compile(r"\{FLG:[^}]+\}")

# Karta lekcji i komentarze uczestników zgodnie wskazują, że lekki model
# (Haiku / gpt-5-mini) wystarcza do tego zadania — eskaluj (S01E03_MODEL=
# claude-sonnet-5) tylko jeśli model gubi wywołania narzędzi albo miesza
# kontekst sesji.
_MODEL = os.getenv("S01E03_MODEL", ANTHROPIC_MODELS["fast"])

# Endpoint jest publicznie osiągalny przez ngrok — bez tych limitów sesje o
# unikalnych sessionID rosłyby w nieskończoność (ryzyko DoS/wyczerpania pamięci).
_MAX_SESSIONS = 200
_MAX_MESSAGES_PER_SESSION = 50

app = ServerFactory.create("s01e03-proxy")

_sessions: "OrderedDict[str, list[LLMMessage]]" = OrderedDict()
_hub = HubClient()
_llm: LLMClient | None = None


def _get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        cfg = get_config()
        _llm = LLMClient(create_provider(_MODEL, cfg))
    return _llm


def _get_session(session_id: str) -> list[LLMMessage]:
    """LRU-bounded per-session history — patrz komentarz przy _MAX_SESSIONS."""
    if session_id in _sessions:
        _sessions.move_to_end(session_id)
        return _sessions[session_id]

    if len(_sessions) >= _MAX_SESSIONS:
        _sessions.popitem(last=False)  # wyrzuć najstarszą sesję

    history: list[LLMMessage] = []
    _sessions[session_id] = history
    return history


class ChatRequest(BaseModel):
    sessionID: str
    msg: str


class ChatResponse(BaseModel):
    msg: str


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    """
    Zwykłe (nie `async def`) — celowo: `run_agent_loop()` jest synchroniczne
    i blokujące na I/O sieciowym (wywołania LLM). FastAPI/Starlette
    automatycznie uruchamia zwykłe endpointy w threadpoolu, więc event loop
    zostaje odblokowany dla /health i innych requestów w trakcie długiej
    odpowiedzi — inaczej jeden wolny /chat blokowałby cały serwer.
    """
    if _FLAG_PATTERN.search(body.msg):
        logfire.info("Flag detected in incoming message", session_id=body.sessionID, msg=body.msg)

    history = _get_session(body.sessionID)
    history.append(LLMMessage.user(body.msg))

    llm = _get_llm()
    # Zbudowany per-request: executor musi widzieć BIEŻĄCĄ historię tej sesji,
    # żeby redirect_package mogło sklasyfikować, czy ta konkretna paczka ma
    # zostać podmieniona — patrz tools.py.
    tool_executor = make_tool_executor(_hub, llm, history)

    reply = llm.run_agent_loop(history, TOOLS, tool_executor, system=SYSTEM_PROMPT_PROXY)

    history.append(LLMMessage.assistant(reply))
    if len(history) > _MAX_MESSAGES_PER_SESSION:
        del history[: len(history) - _MAX_MESSAGES_PER_SESSION]

    return ChatResponse(msg=reply)


if __name__ == "__main__":
    run_server(app, port=int(os.getenv("S01E03_PORT", "8003")))
