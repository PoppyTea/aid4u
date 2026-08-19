"""
S03E04 `negotiations` — rejestracja narzędzi i odbiór flagi.

To zadanie NIE rozwiązuje się przez `run.py solve s03e04`. Flaga nie powstaje
z naszej odpowiedzi — powstaje z pracy agenta Centrali, który odpytuje nasze
publiczne endpointy i **sam** zgłasza znalezione miasta. My tylko rejestrujemy
adresy narzędzi i po chwili odbieramy wynik.

Stąd `solve()` jawnie odmawia (kontrakt żywego serwera z `tasks/AGENTS.md`,
ten sam co w `s01e03_proxy`) zamiast po cichu wysyłać pustą odpowiedź.

Pełny przebieg:
    # 1. terminal A — serwer narzędzi
    uv run python -m tasks.s03e04_negotiations.server

    # 2. terminal B — tunel publiczny
    ./deploy/ngrok_tunnel.sh 8004

    # 3. terminal C — rejestracja i odbiór flagi
    uv run python -m tasks.s03e04_negotiations.solution https://TWOJ-URL.ngrok-free.app

Podgląd realnego ruchu od agenta: https://hub.ag3nts.org/debug
Zatrzymanie wszystkiego: `bash scripts/panic.sh`.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import sys
import time

import httpx
from rich.console import Console

from core.hub import HubClient
from core.tasks import BaseTask, task

_console = Console()

_RUN_INSTRUCTIONS = (
    "s03e04 nie rozwiazuje sie przez `run.py solve` — flage generuje agent "
    "Centrali odpytujac Twoje publiczne narzedzia. Uruchom serwer "
    "(`uv run python -m tasks.s03e04_negotiations.server`), wystaw tunel "
    "(`./deploy/ngrok_tunnel.sh 8004`), a nastepnie zarejestruj URL: "
    "`uv run python -m tasks.s03e04_negotiations.solution <https://...ngrok-free.app>`"
)

# Hub wymaga DOKŁADNIE dwóch narzędzi. Treść zadania sugeruje, że można ogarnąć
# wszystko jednym ("Mozesz zarejestrowac najwyzej 2 narzedzia"), ale walidator
# odrzuca zgłoszenie z jednym elementem: `Field "tools" must contain exactly 2
# elements (tool #1 and tool #2)`. Podział na wyszukiwanie i odpytanie o miasta
# jest i tak naturalny — agent i tak potrzebuje obu kroków.
#
# Klucz to "URL" WIELKIMI literami — tak jest w przykładzie z treści zadania.
#
# Opisy są jedynym kanałem, przez który agent dowiaduje się, jak używać narzędzi,
# więc mówią wprost: co przyjmują, co zwracają i w jakiej kolejności ich użyć.
def build_tools(base_url: str) -> list[dict[str, str]]:
    """Buduje listę dwóch narzędzi w formacie wymaganym przez huba."""
    base = base_url.rstrip("/")
    return [
        {
            "URL": f"{base}/search",
            "description": (
                "Wyszukiwarka katalogu towarow. Parametr: opis przedmiotu w jezyku "
                "naturalnym po polsku, np. 'turbina wiatrowa 48V'. Zwraca liste "
                "pasujacych pozycji, kazda w formacie 'KOD: nazwa'. Uzyj tego "
                "narzedzia NAJPIERW, aby poznac kod przedmiotu."
            ),
        },
        {
            "URL": f"{base}/cities",
            "description": (
                "Zwraca miasta, ktore oferuja dany przedmiot. Parametr: 6-znakowy "
                "kod pozycji otrzymany z wyszukiwarki, np. 'WITR48'. Zwraca nazwy "
                "miast oddzielone przecinkami. Uzyj po wyszukaniu kodu."
            ),
        },
    ]


def register_with_hub(hub: HubClient, base_url: str) -> dict:
    """Zgłasza adresy dwóch narzędzi do huba pod zadaniem 'negotiations'."""
    return hub.submit("negotiations", {"tools": build_tools(base_url)})


def check_result(hub: HubClient) -> dict:
    """
    Odpytuje hub o wynik pracy agenta.

    `-500 "No results yet"` to NORMALNY stan, nie błąd — agent potrzebuje
    minimum 30-60 sekund. Zwracamy surową odpowiedź, żeby wywołujący mógł
    odróżnić 'jeszcze liczy' od prawdziwego błędu.
    """
    try:
        return hub.submit("negotiations", {"action": "check"})
    except httpx.HTTPStatusError as exc:
        try:
            return exc.response.json()
        except Exception:
            raise


def poll_for_flag(hub: HubClient, *, attempts: int = 10, delay: int = 20) -> str | None:
    """Ponawia `check` aż agent skończy pracę albo wyczerpią się próby."""
    for attempt in range(1, attempts + 1):
        result = check_result(hub)
        flag = hub.get_flag(result)
        if flag:
            return flag
        _console.print(f"[dim]{attempt}/{attempts}: {str(result)[:120]}[/]")
        if attempt < attempts:
            time.sleep(delay)
    return None


@task("s03e04", hub_name="negotiations")
class NegotiationsTask(BaseTask):
    """Zadanie z żywym serwerem — `solve()` celowo odmawia automatycznego przebiegu."""

    def solve(self, data: None) -> str:
        """Zawsze rzuca — patrz docstring modułu i `tasks/AGENTS.md`."""
        raise RuntimeError(_RUN_INSTRUCTIONS)


def main() -> None:
    """Rejestruje publiczny URL i czeka na flagę od agenta Centrali."""
    if len(sys.argv) < 2:
        _console.print(f"[red]Uzycie:[/] {sys.argv[0]} https://TWOJ-URL.ngrok-free.app")
        raise SystemExit(2)

    base_url = sys.argv[1]
    hub = HubClient()

    _console.print(f"[bold]Rejestruje narzedzia[/] pod {base_url}")
    response = register_with_hub(hub, base_url)
    _console.print(f"[dim]{str(response)[:200]}[/]")

    _console.print("[bold]Czekam na agenta[/] (min. 30-60 s). Podglad: https://hub.ag3nts.org/debug")
    time.sleep(30)

    flag = poll_for_flag(hub)
    if flag:
        _console.print(f"[bold green]✓ Flaga:[/] {flag}")
    else:
        _console.print("[yellow]Brak flagi — sprawdz /debug i logi .run/s03e04_negotiations/[/]")


if __name__ == "__main__":
    main()
