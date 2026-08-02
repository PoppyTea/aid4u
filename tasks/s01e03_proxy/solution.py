"""
S01E03 nie rozwiązuje się przez `run.py solve s01e03` — to zadanie wymaga
żywej rozmowy bota Wojtek z publicznie wystawionym serwerem (server.py + ngrok),
nie jednorazowego fetch→solve→submit. Ta klasa istnieje żeby spełnić kontrakt
tasks/AGENTS.md ("every task solution MUST contain solution.py") i zarejestrować
zadanie w TASK_REGISTRY, ale solve() celowo odmawia próby automatycznego
rozwiązania zamiast po cichu wysyłać pustą odpowiedź na hub.

hub_name="proxy" — to jest nazwa zadania na hubie, INNA niż lokalny slug
"s01e03" (jak s01e01 → hub_name="people"). Zarówno rejestracja URL-a, jak
i finalna flaga, idą pod zadanie "proxy" w /verify.

Uruchomienie właściwe:
    uv run python -m tasks.s01e03_proxy.server
    ./deploy/ngrok_tunnel.sh 8003
    # skopiuj wypisany https://*.ngrok-free.app URL i zarejestruj go:
    uv run python -c "
        from core.hub import HubClient
        from tasks.s01e03_proxy.solution import register_with_hub
        print(register_with_hub(HubClient(), 'https://TWÓJ-URL.ngrok-free.app', 'test-session-1'))
    "
    # Centrala połączy się, przeprowadzi rozmowę przez Wojtka i przekaże
    # flagę {FLG:...} w jednej z wiadomości — patrz logi serwera.
"""

from __future__ import annotations

from core.hub import HubClient
from core.tasks import BaseTask, task

_RUN_INSTRUCTIONS = (
    "s01e03 nie rozwiązuje się przez `run.py solve` — uruchom serwer "
    "(`uv run python -m tasks.s01e03_proxy.server`), wystaw tunel "
    "(`./deploy/ngrok_tunnel.sh <port>`), zarejestruj publiczny URL przez "
    "register_with_hub() i poczekaj na flagę w wiadomości zwrotnej Wojtka."
)


def register_with_hub(hub: HubClient, url: str, session_id: str) -> dict:
    """
    Zgłasza publiczny URL serwera do huba (zadanie 'proxy'), żeby Centrala
    mogła nawiązać połączenie i przeprowadzić testową rozmowę z Wojtkiem.
    """
    return hub.submit("proxy", {"url": url, "sessionID": session_id})


@task("s01e03", hub_name="proxy")
class ProxyTask(BaseTask):
    def solve(self, data: None) -> str:
        raise RuntimeError(_RUN_INSTRUCTIONS)
