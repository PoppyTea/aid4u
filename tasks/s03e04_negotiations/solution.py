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
import argparse
import time

import httpx
from rich.console import Console

from core.hub import HubClient
from core.tasks import BaseTask, task
from tasks.s03e04_negotiations import secrets_probe

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
def build_tools(base_url: str, *, secrets: bool = False) -> list[dict[str, str]]:
    """
    Buduje listę dwóch narzędzi w formacie wymaganym przez huba.

    Przy `secrets=True` do opisów dokłada się ładunek prompt injection
    (`secrets_probe`) — próba sekretnej flagi. Normalny przebieg go nie widzi.
    """
    base = base_url.rstrip("/")
    tools = [
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
    return secrets_probe.inject_descriptions(tools) if secrets else tools


def register_with_hub(hub: HubClient, base_url: str, *, secrets: bool = False) -> dict:
    """Zgłasza adresy dwóch narzędzi do huba pod zadaniem 'negotiations'."""
    return hub.submit("negotiations", {"tools": build_tools(base_url, secrets=secrets)})


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


def poll_for_secret(hub: HubClient, *, attempts: int = 10, delay: int = 20) -> str | None:
    """
    Sekretny poller — dodatkowo dekoduje odpowiedzi pod kątem obejścia cenzury.

    Dumpuje PEŁNE odpowiedzi (nie ucina), bo przy jednym podejściu sama reakcja
    huba jest interesująca, nawet gdy flagi nie ma. Skanuje base64/rot13 —
    jawny `{FLG:...}` byłby ocenzurowany, więc realny sygnał jest zakodowany.
    """
    for attempt in range(1, attempts + 1):
        result = check_result(hub)
        raw = str(result)
        _console.print(f"[dim]{attempt}/{attempts}:[/] {raw}")

        for method, value in secrets_probe.decode_flags(raw):
            _console.print(f"[bold magenta]  ↳ {method}:[/] {value}")
            if method != "plain":
                return value

        plain = hub.get_flag(result)
        if plain:
            _console.print(f"[yellow]  ↳ flaga jawna (moze glowna, nie sekret):[/] {plain}")

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
    parser = argparse.ArgumentParser(description="Rejestracja narzedzi s03e04 i odbior flagi.")
    parser.add_argument("url", help="Publiczny URL serwera, np. https://xxx.ngrok-free.app")
    parser.add_argument(
        "--secrets",
        action="store_true",
        help=(
            "Proba sekretnej flagi przez prompt injection. Wymaga serwera "
            "uruchomionego z S03E04_SECRETS=1 (injection w odpowiedziach); ta flaga "
            "steruje injection w opisach narzedzi przy rejestracji."
        ),
    )
    args = parser.parse_args()

    hub = HubClient()

    if args.secrets:
        secrets_probe.enable_in_process()
        _console.print("[bold magenta]TRYB SEKRETNY[/] — prompt injection, jedno podejscie.")
        if not secrets_probe.enabled():  # pragma: no cover - sanity
            _console.print("[yellow]Uwaga: S03E04_SECRETS nie wykryte w tym procesie.[/]")

    _console.print(f"[bold]Rejestruje narzedzia[/] pod {args.url}")
    response = register_with_hub(hub, args.url, secrets=args.secrets)
    _console.print(f"[dim]{str(response)[:200]}[/]")

    _console.print("[bold]Czekam na agenta[/] (min. 30-60 s). Podglad: https://hub.ag3nts.org/debug")
    time.sleep(30)

    if args.secrets:
        flag = poll_for_secret(hub)
        label = "Sekretna flaga"
    else:
        flag = poll_for_flag(hub)
        label = "Flaga"

    if flag:
        _console.print(f"[bold green]✓ {label}:[/] {flag}")
    else:
        _console.print("[yellow]Brak flagi — sprawdz /debug i logi .run/s03e04_negotiations/[/]")


if __name__ == "__main__":
    main()
