"""
S01E05 — railway

Aktywuje trasę kolejową X-01 przez samo-dokumentujące się, wieloetapowe API
hubu (task="railway"). Trasa X-01 to stała wartość z fabuły zadania — nie
jest parametrem losowanym per-użytkownik.

Protokół (poznany z akcji "help", niezależnie zweryfikowany na żywo):
    help → reconfigure(route) → setstatus(route, RTOPEN) → save(route)

Każdy krok idzie przez ten sam POST /verify co reszta zadań kursu —
HubClient.submit() jest tu wywoływany kilkukrotnie w ramach jednego solve(),
nie tylko raz na końcu. Ostatni krok (save) wraca jako `answer` i to właśnie
jego odpowiedź (automatyczny finalny submit z BaseTask.run()) zawiera flagę.

Główna trudność zadania to NIE logika, tylko odporność na symulowane
przeciążenie API (503) i bardzo restrykcyjny rate limit (429, z rosnącą karą
za zbyt wczesny retry) — to obsługuje HubClient.submit() (patrz
_post_verify_resilient()), więc solve() jest tu w pełni deterministyczne i
proste.
"""

from __future__ import annotations

from typing import Any

import logfire

from core.tasks import BaseTask, task

ROUTE = "X-01"


@task("s01e05", hub_name="railway")
class RailwayTask(BaseTask):
    """Aktywacja trasy kolejowej przez wieloetapowe API hubu — bez LLM."""

    def _call(self, action: str, **params: Any) -> dict:
        answer = {"action": action, **params}
        if self.dry_run:
            logfire.info(f"DRY RUN — pomijam realne wywołanie hubu dla akcji '{action}'", answer=answer)
            return {"ok": True, "dry_run": True}
        response = self.hub.submit(self._hub_task_name, answer)
        if response.get("ok") is False:
            raise RuntimeError(f"Railway API odrzuciło akcję '{action}': {response.get('message')}")
        return response

    def solve(self, data: Any) -> dict:
        self._call("help")
        self._call("reconfigure", route=ROUTE)
        self._call("setstatus", route=ROUTE, value="RTOPEN")
        return {"action": "save", "route": ROUTE}
