"""
S05E04 `goingthere` — przelot rakietą 3×12 do Grudziądza.

**Zero LLM.** Zadanie wygląda na językowe (wskazówki radiowe w żargonie żeglarskim), ale
komunikaty pochodzą ze skończonej puli sformułowań opisujących jeden z trzech kierunków,
więc rozstrzyga je słownik i eliminacja — patrz `rocket.parse_hint()`.

## Trzy niezależne sposoby zginięcia

1. **Skała w następnej kolumnie** — o niej mówi wskazówka radiowa.
2. **Skała we WŁASNEJ kolumnie.** Rakieta przesuwa się najpierw w pionie, dopiero potem
   do przodu, więc skała „obok" blokuje docelowy wiersz tak samo jak ta „przed". To jest
   ten błąd, na którym wykłada się większość uczestników; `/verify` podaje
   `currentColumn.freeRows` po każdym ruchu, więc drugie źródło jest za darmo.
3. **Radar systemu OKO** — ruch bez rozbrojenia kończy się zestrzeleniem.

Do tego dochodzi wyjście poza siatkę i konieczność wylądowania w wierszu bazy.

## Zagłuszanie jest częścią zadania, nie awarią

Zmierzone 2026-08-25: ~21% wywołań skanera kończy się `502`, czasem z pełnym HTML-em przy
statusie sugerującym sukces. Nawet komunikat „czysto" przychodzi zniekształcony — realnie
`"Its cleeear"`, nie `"It's clear!"` z treści zadania. Dlatego każde zapytanie idzie przez
`_insist()`, treść jest walidowana `expect_not_html()`, a odczyt pól skanera nie używa
`json.loads()` (treść zadania wprost ostrzega, że to „może nie być zdatne do parsowania").
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import time
from typing import Any
from collections.abc import Callable

import httpx
import logfire
from rich.console import Console
from rich.markup import escape

from core.config import get_config
from core.net import expect_not_html
from core.runtime import check_abort
from core.tasks import BaseTask, task
from tasks.s05e04_goingthere.rocket import (
    COLUMNS,
    MOVE_OFFSETS,
    HintUnreadable,
    disarm_hash,
    is_clear,
    parse_hint,
    safe_moves,
    salvage_scan,
)

_console = Console()

HUB_TASK = "goingthere"

# Ile razy ponawiać zapytanie do zagłuszanego API. Przy zmierzonych ~21% błędów sześć
# prób daje szansę porażki rzędu 0.21^6 ≈ 1 na 11 000 — a przelot potrzebuje ich ~22.
_ATTEMPTS = 6
_BACKOFF_S = 1.5

# Ile razy pobrać wskazówkę, zanim uznamy kolumnę za nieczytelną.
#
# Dwa, a nie więcej, i to jest wynik pomiaru: sformułowanie jest **stałe dla pozycji**
# — pięć zapytań pod rząd zwróciło dokładnie to samo zdanie. Wariant językowy zmienia
# się między grami, nie w obrębie jednej. Powtarzanie nie jest więc drogą do
# rozpoznania trudnej wskazówki, a jedynie osłoną na przekłamanie transmisji;
# właściwą odpowiedzią na nieznane sformułowanie jest poszerzenie słownika.
_HINT_ATTEMPTS = 2


class MissionFailed(RuntimeError):
    """Przelot nie może się udać — przerywamy zamiast lecieć w ciemno."""


@task("s05e04", hub_name="goingthere")
class GoingThereTask(BaseTask):
    """Prowadzi rakietę przez 11 ruchów i oddaje ostatni jako odpowiedź zadania."""

    def solve(self, data: None) -> dict[str, str]:
        """
        Przeprowadza przelot i zwraca OSTATNI ruch, zamiast go wykonywać.

        Args:
            data: Nieużywane — stan gry żyje po stronie API.

        Returns:
            `{"command": …}` — ruch wjeżdżający do kolumny 12. Wysyła go
            `BaseTask._submit()`, więc flaga wraca z jednego, jawnego zgłoszenia.
        """
        cfg = get_config()
        self._key = cfg.apikey
        self._base = cfg.hub_base_url

        state = self.hub.submit(HUB_TASK, {"command": "start"})
        base_row = state["base"]["row"]
        _console.print(f"[bold]Start:[/] {state['player']} → baza w wierszu {base_row}")

        with httpx.Client(timeout=25.0) as http:
            self._http = http
            # Pętla kończy się w kolumnie 11: ostatni ruch zwraca `solve()`, żeby to
            # `_submit()` odebrał flagę i żeby zgłoszenie poszło dokładnie raz.
            while state["player"]["col"] < COLUMNS - 1:
                state = self._advance(state, base_row)

            command = self._plan(state, base_row, required_row=base_row)
            _console.print(f"[bold green]Ostatni ruch:[/] {command} → kolumna {COLUMNS}")
            return {"command": command}

    def _advance(self, state: dict, base_row: int) -> dict:
        """Wykonuje jeden pełny krok: rozbrojenie radaru, wskazówka, ruch."""
        command = self._plan(state, base_row)
        try:
            moved = self.hub.submit(HUB_TASK, {"command": command})
        except httpx.HTTPStatusError as rejected:
            # Hub odrzuca ruch tym samym kodem 400 niezależnie od powodu — rozbicie
            # o skałę, zestrzelenie przez radar i wyjście poza siatkę wyglądają
            # identycznie, dopóki nie przeczyta się treści odpowiedzi. Bez tego
            # diagnostyka sprowadza się do zgadywania, który z trzech sposobów
            # zginięcia właśnie nastąpił.
            raise MissionFailed(
                f"Ruch {command!r} z kolumny {state['player']['col']} "
                f"(wiersz {state['player']['row']}, wolne {state['currentColumn']['freeRows']}) "
                f"odrzucony: {rejected.response.text[:300]}"
            ) from rejected

        player = moved.get("player")
        if not player:
            raise MissionFailed(f"Ruch {command!r} nie zwrócił pozycji: {moved}")
        _console.print(
            f"  kol {player['col']:>2} wiersz {player['row']}  ({command})",
            highlight=False,
        )
        return moved

    def _plan(self, state: dict, base_row: int, required_row: int | None = None) -> str:
        """
        Przygotowuje jeden ruch: rozbraja radar, czyta wskazówkę, wybiera komendę.

        Args:
            state: Ostatnia odpowiedź `/verify` (`player` + `currentColumn`).
            base_row: Wiersz bazy w kolumnie 12.
            required_row: Wiersz, w którym ruch MUSI wylądować (tylko ostatni krok).

        Raises:
            MissionFailed: Gdy nie ma bezpiecznego ruchu albo gdy wymagany wiersz
                jest niedostępny.
        """
        check_abort()
        self._disarm_if_tracked()

        row = state["player"]["row"]
        free_rows = state["currentColumn"]["freeRows"]

        # Skała we WŁASNEJ kolumnie i krawędź siatki potrafią same zostawić jedno
        # wyjście. Wtedy wskazówka niczego nie rozstrzyga: pytanie o nią kosztuje
        # wywołanie zagłuszanego API i daje kolejną okazję do nieczytelnego zdania,
        # a odpowiedź i tak nie zmieni wyboru.
        allowed = safe_moves(row, free_rows, forbidden_row=None)
        if len(allowed) > 1:
            blocked = self._read_hint()
            allowed = safe_moves(row, free_rows, row + MOVE_OFFSETS[blocked])

        if not allowed:
            raise MissionFailed(
                f"Brak bezpiecznego ruchu w kolumnie {state['player']['col']}: "
                f"wiersz {row}, wolne wiersze {free_rows}."
            )

        if required_row is not None:
            landing = [c for c in allowed if row + MOVE_OFFSETS[c] == required_row]
            if not landing:
                raise MissionFailed(
                    f"Nie da się wylądować w wierszu bazy {required_row} z wiersza {row}; "
                    f"bezpieczne ruchy: {allowed}."
                )
            return landing[0]

        return min(allowed, key=lambda c: (abs(row + MOVE_OFFSETS[c] - base_row), c != "go"))

    def _read_hint(self) -> str:
        """
        Pobiera wskazówkę radiową i zamienia ją na zablokowany kierunek.

        Przy nieczytelnym sformułowaniu pyta PONOWNIE, zamiast zgadywać: ta sama skała
        bywa opisana inaczej przy każdym zapytaniu, więc powtórzenie jest tańsze
        i pewniejsze niż rozbudowywanie słownika o kolejny wariant.
        """
        seen: list[str] = []
        for _ in range(_HINT_ATTEMPTS):
            payload = self._insist(
                lambda: self._http.post(f"{self._base}/api/getmessage", json={"apikey": self._key})
            )
            hint = str(payload.json().get("hint", ""))
            seen.append(hint)
            try:
                return parse_hint(hint)
            except HintUnreadable:
                logfire.info("Wskazówka nieczytelna, pytam ponownie", hint=hint)
                _console.print(f"    [yellow]?[/] {escape(hint)}", highlight=False)

        raise MissionFailed(f"{_HINT_ATTEMPTS} nieczytelnych wskazówek z rzędu: {seen}")

    def _disarm_if_tracked(self) -> None:
        """
        Sprawdza skaner i rozbraja radar, jeśli rakieta jest namierzana.

        Ruch bez rozbrojenia kończy się zestrzeleniem, więc to sprawdzenie idzie PRZED
        każdym ruchem, także przed ostatnim.
        """
        # Odczyt pól dzieje się WEWNĄTRZ pętli ponowień, nie po niej. Zniekształcenie
        # jest losowane per odpowiedź, więc pakiet zepsuty nieodwracalnie da się po
        # prostu pobrać jeszcze raz — a przerwanie misji w tym miejscu byłoby porażką
        # z powodu, który sam mija. Poprawka zaproponowana przez CodeRabbita na PR #88.
        scan: tuple[int, str] | None = None

        def parse_scan(response: httpx.Response) -> None:
            """Czyta stan skanera, dopóki jesteśmy jeszcze w budżecie ponowień."""
            nonlocal scan
            scan = None if is_clear(response.text) else salvage_scan(response.text)

        self._insist(
            lambda: self._http.get(
                f"{self._base}/api/frequencyScanner", params={"key": self._key}
            ),
            validate=parse_scan,
        )
        if scan is None:
            return

        frequency, code = scan
        _console.print(f"    [magenta]radar[/] f={frequency} — rozbrajam", highlight=False)
        self._insist(
            lambda: self._http.post(
                f"{self._base}/api/frequencyScanner",
                json={
                    "apikey": self._key,
                    "frequency": frequency,
                    "disarmHash": disarm_hash(code),
                },
            )
        )

    def _insist(
        self,
        call: Callable[[], httpx.Response],
        validate: Callable[[httpx.Response], None] | None = None,
    ) -> httpx.Response:
        """
        Ponawia zapytanie do zagłuszanego API, aż zwróci sensowną treść.

        Zagłuszanie jest zamierzone i zmierzone: ~21% wywołań kończy się `502`, czasem
        ze stroną HTML przy statusie sugerującym sukces — stąd walidacja treści obok
        kodu odpowiedzi. `expect_not_html()` jest tu warunkiem koniecznym, nie ozdobą.

        Args:
            call: Zapytanie do wykonania.
            validate: Opcjonalny odczyt treści, wykonywany W TEJ SAMEJ pętli prób.
                Dzięki temu odpowiedź nieodwracalnie zepsuta liczy się jak błąd
                transportu i po prostu ponawiamy zapytanie.

        Raises:
            MissionFailed: Po wyczerpaniu prób.
        """
        last: Exception | str = "brak prób"
        for attempt in range(1, _ATTEMPTS + 1):
            check_abort()
            try:
                response = call()
                response.raise_for_status()
                expect_not_html(response.content, source="frequencyScanner/getmessage")
                if validate is not None:
                    validate(response)
                return response
            except Exception as failure:  # noqa: BLE001 — każdy błąd jest tu przejściowy
                last = failure
                logfire.info("Zagłuszone zapytanie, ponawiam", attempt=attempt)
                time.sleep(_BACKOFF_S)
        raise MissionFailed(f"API nie odpowiedziało sensownie w {_ATTEMPTS} próbach: {last}")

    _http: httpx.Client
    _key: str
    _base: str

    def fetch_data(self) -> Any:
        """Zadanie nie pobiera danych — cały stan powstaje po `start`."""
        return None
