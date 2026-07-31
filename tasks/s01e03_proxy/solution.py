"""
S01E03 nie rozwiązuje się przez `run.py solve s01e03` — to zadanie wymaga
żywej rozmowy bota Wojtek z publicznie wystawionym serwerem (server.py + ngrok),
nie jednorazowego fetch→solve→submit. Ta klasa istnieje żeby spełnić kontrakt
tasks/AGENTS.md ("every task solution MUST contain solution.py") i zarejestrować
zadanie w TASK_REGISTRY, ale solve() celowo odmawia próby automatycznego
rozwiązania zamiast po cichu wysyłać pustą odpowiedź na hub.

Uruchomienie właściwe:
    uv run python -m tasks.s01e03_proxy.server
    ./deploy/ngrok_tunnel.sh 8003
    # podaj wypisany URL botowi Wojtek na hubie, poczekaj na {FLG:...}
"""

from __future__ import annotations

from core.tasks import BaseTask, task

_RUN_INSTRUCTIONS = (
    "s01e03 nie rozwiązuje się przez `run.py solve` — uruchom serwer "
    "(`uv run python -m tasks.s01e03_proxy.server`), wystaw tunel "
    "(`./deploy/ngrok_tunnel.sh <port>`), podaj publiczny URL botowi Wojtek "
    "na hubie i poczekaj na flagę w jego wiadomości zwrotnej."
)


@task("s01e03")
class ProxyTask(BaseTask):
    def solve(self, data: None) -> str:
        raise RuntimeError(_RUN_INSTRUCTIONS)
