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
        Advance the mission to the final column and return the last movement command without executing it.
        
        Returns:
            dict[str, str]: A mapping containing the final movement command under ``"command"``.
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
        """
        Execute one movement command and return the updated mission state.
        
        Parameters:
            state (dict): Current mission state used to plan the movement.
            base_row (int): Row the player must reach for the final movement.
        
        Returns:
            dict: Updated mission state after the movement.
        
        Raises:
            MissionFailed: If the hub rejects the movement or does not return the player's position.
        """
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
        Plan a safe movement command from the current position.
        
        Args:
            state: Latest movement state containing the player's position and free rows.
            base_row: Target row in the destination column.
            required_row: Required landing row for the final movement.
        
        Raises:
            MissionFailed: If no safe movement is available or the required landing row
                cannot be reached.
        
        Returns:
            A movement command leading to a safe destination.
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
        Pobiera wskazówkę radiową i określa zablokowany kierunek.
        
        Ponawia próbę dla nieczytelnych wskazówek. Po wyczerpaniu limitu prób zgłasza
        MissionFailed.
        
        Returns:
        	str: Zablokowany kierunek.
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
        Checks the frequency scanner and disarms the radar when the rocket is being tracked.
        """
        response = self._insist(
            lambda: self._http.get(
                f"{self._base}/api/frequencyScanner", params={"key": self._key}
            )
        )
        body = response.text
        if is_clear(body):
            return

        frequency, code = salvage_scan(body)
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

    def _insist(self, call: Callable[[], httpx.Response]) -> httpx.Response:
        """
        Wykonuje żądanie ponownie, aż otrzyma prawidłową odpowiedź z niepustą treścią inną niż HTML.
        
        Raises:
            MissionFailed: Gdy wszystkie próby zakończą się niepowodzeniem.
        """
        last: Exception | str = "brak prób"
        for attempt in range(1, _ATTEMPTS + 1):
            check_abort()
            try:
                response = call()
                response.raise_for_status()
                expect_not_html(response.content, source="frequencyScanner/getmessage")
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
