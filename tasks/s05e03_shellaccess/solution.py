"""
S05E03 `shellaccess` — namierzenie miejsca i daty spotkania z Rafałem w archiwum czasu.

**Zero LLM.** Archiwum jest relacyjne i w pełni deterministyczne: trzy pliki w `/data`
połączone kluczami liczbowymi, jedno jedyne zdarzenie opisujące znalezienie ciała.
Pętla agentowa musiałaby odkryć dokładnie to, co widać po czterech `grep`-ach —
za cenę kilkudziesięciu tur i realnego ryzyka odmowy modelu (społeczność wielokrotnie
raportowała, że Claude odmawia „szukania ciała", powołując się na politykę użytkowania).

Kształt archiwum, ustalony sondą (`probe.py`) — treść zadania nie podaje go wcale,
a fabuła wręcz myli, zapowiadając „prosty plik tekstowy":

    /data/time_logs.csv    date;description;location;place   (4541 wierszy)
    /data/locations.json   [{location_id, name}]
    /data/gps.json         [{latitude, longitude, type, location_id, entry_id}]

Kolumna `location` wskazuje na `location_id`, kolumna `place` na `entry_id` — nazwy
NIE są zgodne między plikami, co jest jedyną realną zagwozdką w tym zadaniu.

Odpowiedź: `date` **o dzień wcześniejsza** niż zdarzenie (podpowiedź z base64 w treści
zadania; w samym archiwum nie ma o tym śladu), `city` z `locations.json`, współrzędne
z `gps.json`. Wynikiem jest polecenie `echo` — hub czyta stdout, nie pole `answer`.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import json
import re
from datetime import date, timedelta

import logfire
from rich.console import Console
from rich.markup import escape

from core.runtime import check_command
from core.tasks import BaseTask, task
from tasks.s05e03_shellaccess.archive import ArchiveShell

_console = Console()

TIME_LOGS = "/data/time_logs.csv"
LOCATIONS = "/data/locations.json"
GPS = "/data/gps.json"

# Fraza zdarzenia. Wąska celowo: `grep -c ciało` daje w całym archiwum DOKŁADNIE jedno
# trafienie, więc zawężanie do "ciało Rafała" byłoby złudną precyzją — wpis mówi
# "ciało mężczyzny", nazwiska w nim nie ma. Szeroki wzorzec (np. "Rafał", 37 trafień)
# przewraca hub na HTTP 400 przez rozmiar wyniku — patrz `archive.py`.
EVENT_PHRASE = "ciało"

# `date;description;location;place`, z opcjonalnym prefiksem `plik:` i/lub `nr-linii:`
# dorzucanym przez `grep`. Kotwiczymy na końcu wiersza, bo opis potrafi zawierać `;`.
_LOG_LINE_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2});(?P<description>.*);(?P<location>\d+);(?P<place>\d+)\s*$"
)

_NAME_RE = re.compile(r'"name"\s*:\s*"(?P<name>(?:[^"\\]|\\.)*)"')

# Współrzędne wyciągamy jako TEKST, nie jako `float`. Odpowiedź ma zawierać dokładnie
# te cyfry, które są w archiwum; przepuszczenie ich przez `float` wprowadza ryzyko
# rozjazdu reprezentacji (`18.968774` → `18.968773999999998`) w miejscu, w którym
# walidator porównuje wartość liczbową.
_LATITUDE_RE = re.compile(r'"latitude"\s*:\s*(?P<value>-?\d+(?:\.\d+)?)')
_LONGITUDE_RE = re.compile(r'"longitude"\s*:\s*(?P<value>-?\d+(?:\.\d+)?)')


class ArchiveLookupError(RuntimeError):
    """Archiwum nie oddało spodziewanego kształtu danych — przerywamy zamiast zgadywać."""


@task("s05e03", hub_name="shellaccess")
class ShellAccessTask(BaseTask):
    """Zdalny grep po archiwum czasu; odpowiedź wypisywana `echo`-em na stdout serwera."""

    def solve(self, data: None) -> dict[str, str]:
        """
        Odtwarza dane z archiwum i buduje polecenie wypisujące odpowiedź.

        Args:
            data: Nieużywane — całe wejście żyje na zdalnym serwerze.

        Returns:
            `{"cmd": "echo '<json>'"}` — polecenie, którego stdout hub uzna za odpowiedź.
        """
        shell = ArchiveShell(self.hub)

        found_date, location_id, entry_id = self._find_event(shell)
        city = self._find_city(shell, location_id)
        latitude, longitude = self._find_coordinates(shell, entry_id)

        # Sedno zadania i jedyna informacja spoza archiwum: spotkanie ma się odbyć
        # DZIEŃ PRZED znalezieniem ciała. W logach nie ma o tym ani słowa — podpowiedź
        # siedzi zakodowana base64 w treści zadania.
        meeting_date = found_date - timedelta(days=1)

        # `escape()` na nazwie miasta — wartość pochodzi ze zdalnego archiwum, a Rich
        # po cichu usuwa z wyjścia wszystko, co wygląda na znacznik stylu.
        _console.print(
            f"[bold]Zdarzenie:[/] {found_date} → [bold]spotkanie:[/] {meeting_date} · "
            f"[cyan]{escape(city)}[/] ({latitude}, {longitude})"
        )
        return {"cmd": build_echo_command(meeting_date, city, latitude, longitude)}

    def _find_event(self, shell: ArchiveShell) -> tuple[date, str, str]:
        """Znajduje wpis o znalezieniu ciała i zwraca `(data, location_id, entry_id)`."""
        output = shell.run(f"grep -n {EVENT_PHRASE} {TIME_LOGS}")
        match = _LOG_LINE_RE.search(output)
        if not match:
            raise ArchiveLookupError(f"Brak wpisu pasującego do wzorca w wyniku: {output[:200]!r}")

        logfire.info("Event line found", line=match.group(0))
        return (
            date.fromisoformat(match["date"]),
            match["location"],
            match["place"],
        )

    def _find_city(self, shell: ArchiveShell, location_id: str) -> str:
        """Tłumaczy `location_id` na nazwę miasta z `locations.json`."""
        # `-w` odcina dopasowania częściowe (`219` wewnątrz `1219`); `-A2` wystarcza,
        # bo `name` stoi bezpośrednio pod `location_id` w każdym rekordzie.
        output = shell.run(f"grep -A2 -w {location_id} {LOCATIONS}")
        match = _NAME_RE.search(output)
        if not match:
            raise ArchiveLookupError(f"Brak nazwy dla location_id={location_id}: {output[:200]!r}")

        # Plik trzyma diakrytyki jako escape'y (`Grudziądz`), więc dekodujemy je
        # przez parser JSON zamiast podstawiać ręcznie.
        return json.loads(f'"{match["name"]}"')

    def _find_coordinates(self, shell: ArchiveShell, entry_id: str) -> tuple[str, str]:
        """Zwraca `(latitude, longitude)` jako teksty — dokładnie tak, jak w archiwum."""
        # `entry_id` jest ostatnim polem rekordu, więc kontekst bierzemy WSTECZ.
        output = shell.run(f"grep -B5 -w {entry_id} {GPS}")
        latitude = _LATITUDE_RE.search(output)
        longitude = _LONGITUDE_RE.search(output)
        if not latitude or not longitude:
            raise ArchiveLookupError(
                f"Brak współrzędnych dla entry_id={entry_id}: {output[:200]!r}"
            )

        return latitude["value"], longitude["value"]


def build_echo_command(meeting_date: date, city: str, latitude: str, longitude: str) -> str:
    """
    Składa polecenie `echo` wypisujące odpowiedź na stdout zdalnego serwera.

    Wydzielone z `solve()`, bo to jedyny fragment z realnymi trybami porażki
    zgłaszanymi przez społeczność — i jedyny, który da się przetestować bez sieci.

    Raises:
        ValueError: Gdy dane wymusiłyby polecenie, które rozjechałoby się w powłoce
            albo nie byłoby poprawnym JSON-em.
    """
    city_json = json.dumps(city, ensure_ascii=False)
    payload = (
        f'{{"date":"{meeting_date.isoformat()}","city":{city_json},'
        f'"longitude":{longitude},"latitude":{latitude}}}'
    )

    # Trzy asercje na trzy udokumentowane sposoby przegrania tego zadania mimo
    # posiadania poprawnych danych:
    #
    # 1. apostrof w treści zamknąłby `echo '…'` przedwcześnie i wypisał śmieci;
    # 2. literówka w sklejaniu JSON-a daje odpowiedź, którą hub odsyła echem bez flagi
    #    (raportowane: „miałem źle sformatowaną komendę echo");
    # 3. bramka poleceń dostaje własną komendę do sprawdzenia, zanim pójdzie w świat.
    #
    # `printf` jest tu świadomie NIEobecny: przy poprawnych danych walidator zwracał
    # na nim ucięte `{city:` — to znany, powtarzalny tryb porażki, nie kwestia gustu.
    if "'" in payload:
        raise ValueError(f"Apostrof w odpowiedzi rozbiłby cytowanie echo: {payload}")
    json.loads(payload)

    command = f"echo '{payload}'"
    check_command(command)
    return command
