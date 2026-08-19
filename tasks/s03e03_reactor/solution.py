"""
S03E03 — reactor

Prowadzi robota transportowego przez planszę reaktora 7×5 do celu, omijając
ruchome bloki — **deterministycznie, zero LLM** (zgodnie z rekomendacją
`tasks/s03/requirements/s03e03.md` i `community-intel.md`: "kilku uczestników
zrobiło to czystym BFS w 8-12 ruchach", koszt $0.00).

Format API i model fizyki bloków NIE są udokumentowane w treści zadania —
ustalone empirycznie sondą (`scripts/probe_api.py`, wyniki w
`data/input/s03e03_reactor/`), pełny opis w docstringu `reactor.py`.

Strategia — receding-horizon BFS (Podejście C, `tasks/s03e03_reactor/AGENTS.md`):
    1. obserwuj RZECZYWISTY stan planszy z API (nie własną symulację)
    2. BFS na `reactor.py` → pełny plan do celu
    3. weź TYLKO pierwszy ruch z planu
    4. guardrail: zweryfikuj go własną symulacją PRZED wysłaniem — jeśli
       model przewiduje zgniecenie, wymuś `wait`
    5. wyślij jeden ruch, wyrzuć resztę planu, wróć do 1

Samonaprawialne: błąd w modelu fizyki koryguje się w następnym ticku, bo plan
jest przeliczany od stanu ZAOBSERWOWANEGO przez API, nie od własnej symulacji.

Kontrakt submisji (`strategy/rules/common/r13-single-submission-contract.md`,
AID-15): to zadanie woła hub WIELOKROTNIE wewnątrz `solve()` (jak
`s01e05_railway`), więc `_submit()` jest nadpisane — nigdy nie wysyła listy
ruchów jako osobnej "odpowiedzi", zwraca flagę złapaną po drodze.
"""

from __future__ import annotations

from typing import Any

import httpx
import logfire

from core.runtime import check_abort
from core.tasks import BaseTask, task
from tasks.s03e03_reactor.reactor import GOAL_COL, apply_command, solve_bfs, state_from_api

_MAX_COMMANDS = 60
_MAX_CRUSH_RETRIES = 3
_CRUSH_HTTP_STATUS = 409
_CRUSH_CODE = -920


@task("s03e03", hub_name="reactor")
class ReactorTask(BaseTask):
    """Prowadzi robota do celu przez planszę reaktora — deterministyczny BFS, zero LLM."""

    _captured_flag: str | None = None

    def solve(self, data: Any) -> dict:
        if self.dry_run:
            return self._dry_run_preview()

        moves: list[str] = []
        crush_retries = 0

        response = self._send("start")
        state = state_from_api(response)

        while state.player_col != GOAL_COL:
            check_abort()
            if len(moves) >= _MAX_COMMANDS:
                raise RuntimeError(
                    f"s03e03: przekroczono {_MAX_COMMANDS} komend bez dotarcia do celu. "
                    f"Ostatni stan: player_col={state.player_col}, moves={moves}"
                )

            plan = solve_bfs(state)
            if not plan:
                raise RuntimeError(
                    f"s03e03: BFS nie znalazł trasy do celu ze stanu player_col={state.player_col}, "
                    f"blocks={state.blocks} — sprawdź model fizyki w reactor.py."
                )
            command = plan[0]

            # Guardrail programistyczny (staff kursu jawnie błogosławi ten mechanizm,
            # patrz s03e03.md) — jeśli własna symulacja przewiduje zgniecenie na tym
            # ruchu, wymuś bezpieczniejszą alternatywę zamiast ślepo ufać planowi.
            if apply_command(state, command) is None:
                logfire.warning(
                    "s03e03: BFS zwrócił ruch oceniany przez guardrail jako zgniecenie — wymuszam wait",
                    command=command,
                    player_col=state.player_col,
                )
                command = "wait"

            response = self._send(command)
            moves.append(command)

            if response.get("code") == _CRUSH_CODE:
                crush_retries += 1
                logfire.warning(
                    "s03e03: zgnieciony mimo guardrailu — model fizyki się rozjechał z rzeczywistością, reset",
                    attempt=crush_retries,
                    moves_so_far=len(moves),
                )
                if crush_retries > _MAX_CRUSH_RETRIES:
                    raise RuntimeError(
                        f"s03e03: {_MAX_CRUSH_RETRIES} zgnieceń mimo guardrailu, przerywam. "
                        f"Ostatnia odpowiedź huba: {response}"
                    )
                response = self._send("reset")
                state = state_from_api(response)
                continue

            flag = self.hub.get_flag(response)
            if flag:
                # Odpowiedź, która niesie flagę, nie zawiera już `blocks` (gra
                # skończona) — nie próbuj jej parsować jako stanu planszy, po
                # prostu skończ pętlę.
                self._captured_flag = flag
                break

            state = state_from_api(response)

        return {"moves": moves, "crush_retries": crush_retries}

    def _send(self, command: str) -> dict:
        """
        POST /verify z `{"command": ...}` (format ustalony empirycznie — hub
        odrzuca gołe stringi, patrz docstring modułu). Zgniecenie (HTTP 409,
        `code: -920`) to udokumentowany, normalny krok protokołu tej gry, nie
        błąd — łapiemy WYŁĄCZNIE ten kod (R7: except zawężony do
        udokumentowanego statusu), reszta propaguje się.
        """
        try:
            return self.hub.submit(self._hub_task_name, {"command": command})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != _CRUSH_HTTP_STATUS:
                raise
            try:
                return exc.response.json()
            except ValueError:
                return {"code": _CRUSH_CODE, "message": "Robot was crushed :(", "_raw": exc.response.text}

    def _dry_run_preview(self) -> dict:
        """
        DRY RUN: jedno wywołanie `start` (odczyt stanu planszy — gra nie ma
        żadnych statycznych/offline danych, to jedyny sposób zbudowania
        czegokolwiek do pokazania) + jeden pełny BFS od stanu początkowego.
        Nie wykonuje ŻADNEGO z zaplanowanych ruchów — to podgląd JEDNEGO planu,
        nie symulacja pełnej pętli receding-horizon z `solve()` (ta koryguje
        się co tick na podstawie odpowiedzi huba, więc nie da się jej sensownie
        "zasymulować" bez faktycznego wysyłania komend).
        """
        response = self._send("start")
        state = state_from_api(response)
        plan = solve_bfs(state)
        return {
            "dry_run": True,
            "initial_player_col": state.player_col,
            "planned_moves": plan,
        }

    def _submit(self, task_name: str, answer: Any) -> str | None:
        """
        Pomija domyślny finalny POST /verify — `solve()` już wołało hub
        wielokrotnie i `answer` (lista ruchów) nie jest poprawnym formatem
        odpowiedzi tej gry (R6: zadania z pętlą feedbacku w `solve()` muszą
        nadpisać `_submit()`, nie polegać na domyślnym zachowaniu `BaseTask`).
        """
        check_abort()
        if self._captured_flag:
            return self._captured_flag
        if self.dry_run:
            return super()._submit(task_name, answer)
        raise RuntimeError(
            "s03e03: robot dotarł do celu (player_col == GOAL_COL), ale żadna odpowiedź huba "
            "po drodze nie zawierała flagi — sprawdź ostatnią odpowiedź /verify ręcznie."
        )
