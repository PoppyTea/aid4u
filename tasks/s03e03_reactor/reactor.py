"""
Czysta logika s03e03 (reactor): model fizyki bloków, symulacja jednego ticku,
BFS po najkrótszą trasę. Zero I/O, zero huba — testowalne offline na syntetycznych
planszach (patrz `test_solution.py`).

Model fizyki i kolizji USTALONY EMPIRYCZNIE sondą (`scripts/probe_api.py`), bo
lekcja nie podaje żadnego przykładu JSON:

- Plansza: 7 kolumn (1..7), 5 wierszy (1..5, wiersz 5 = dół, gdzie chodzi robot).
- Każdy blok zajmuje 2 wiersze (`top_row`, `top_row+1`), `top_row` ∈ {1,2,3,4}.
- KAŻDA komenda (`left`/`right`/`wait` — NIE `start`/`reset`) przesuwa WSZYSTKIE
  bloki o jeden wiersz w kierunku `direction`. Gdy `top_row` osiąga skrajną
  wartość (1 albo 4), `direction` w odpowiedzi jest JUŻ odwrócony — pokazuje
  kierunek dla NASTĘPNEGO ticku, nie bieżącego.
- Kolizja jest sprawdzana PO przesunięciu bloków, nie przed — potwierdzone
  eksperymentalnie: ruch w kolumnę, która PRZED ruchem nie miała bloku w wierszu 5
  (`top_row=3, direction=down`), zakończył się zgnieceniem, bo blok wszedł w
  wiersz 5 W TYM SAMYM ticku. Symetrycznie: ruch w kolumnę, która PRZED ruchem
  MIAŁA blok w wierszu 5 (`top_row=4, direction=up`), zakończył się sukcesem, bo
  blok w tym samym ticku zdążył się wycofać. To dotyczy też `wait` — stanie w
  miejscu nie chroni przed blokiem wchodzącym w Twoją kolumnę.
- Kolumny 1 (start) i 7 (cel) nigdy nie mają bloków (potwierdzone: `blocks` z API
  zawiera zawsze dokładnie kolumny 2..6).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

BOARD_COLS = 7
BOARD_ROWS = 5
BLOCK_HEIGHT = 2
GOAL_COL = BOARD_COLS
START_COL = 1
DEATH_ROW = BOARD_ROWS  # blok zajmujący ten wiersz w kolumnie robota = zgniecenie

# top_row zakres [1, BOARD_ROWS - BLOCK_HEIGHT + 1] = [1, 4]
_MIN_TOP_ROW = 1
_MAX_TOP_ROW = BOARD_ROWS - BLOCK_HEIGHT + 1

COMMANDS = ("left", "right", "wait")
_COL_DELTA = {"left": -1, "right": 1, "wait": 0}


@dataclass(frozen=True, slots=True)
class Block:
    """Jeden blok reaktora — kolumna, górny wiersz i kierunek ruchu."""

    col: int
    top_row: int
    direction: str  # "up" | "down"

    def advance(self) -> Block:
        """Przesuwa blok o jeden wiersz; odwraca kierunek dokładnie na granicy."""
        new_top = self.top_row + (1 if self.direction == "down" else -1)
        if new_top <= _MIN_TOP_ROW:
            return Block(self.col, _MIN_TOP_ROW, "down")
        if new_top >= _MAX_TOP_ROW:
            return Block(self.col, _MAX_TOP_ROW, "up")
        return Block(self.col, new_top, self.direction)

    def occupies_death_row(self) -> bool:
        return self.top_row + BLOCK_HEIGHT - 1 >= DEATH_ROW


@dataclass(frozen=True, slots=True)
class ReactorState:
    """Stan gry: kolumna robota + pozycje/kierunki wszystkich bloków."""

    player_col: int
    blocks: tuple[Block, ...]  # posortowane po col, dla stabilnego hashowania

    def blocks_by_col(self) -> dict[int, Block]:
        return {b.col: b for b in self.blocks}


def advance_blocks(blocks: tuple[Block, ...]) -> tuple[Block, ...]:
    """Jeden tick symulacji — przesuwa WSZYSTKIE bloki o wiersz."""
    return tuple(b.advance() for b in blocks)


def apply_command(state: ReactorState, command: str) -> ReactorState | None:
    """
    Symuluje jeden tick po komendzie `command`. Zwraca `None`, jeśli robot
    zostałby zgnieciony (kolizja sprawdzana PO przesunięciu bloków — patrz
    docstring modułu) — dokładnie tak, jak zachowuje się prawdziwe API.
    """
    if command not in COMMANDS:
        raise ValueError(f"Nieznana komenda symulacji: {command!r}")

    new_col = state.player_col + _COL_DELTA[command]
    if not (START_COL <= new_col <= GOAL_COL):
        return None  # ruch poza planszę — nielegalny, traktujemy jak niebezpieczny

    new_blocks = advance_blocks(state.blocks)

    if new_col != GOAL_COL and new_col != START_COL:
        block_here = next((b for b in new_blocks if b.col == new_col), None)
        if block_here is not None and block_here.occupies_death_row():
            return None  # zgnieciony

    return ReactorState(player_col=new_col, blocks=new_blocks)


def solve_bfs(initial: ReactorState, *, max_depth: int = 60) -> list[str] | None:
    """
    BFS po najkrótszą sekwencję komend prowadzącą `player_col` do `GOAL_COL`.
    Przestrzeń stanów jest mała (7 kolumn × okresowe fazy bloków, okres 6 na
    blok) — BFS kończy się natychmiast, nie potrzeba heurystyk.

    Zwraca listę komend (`["right", "wait", ...]`) albo `None`, jeśli w granicy
    `max_depth` nie znaleziono trasy (nie powinno się zdarzyć przy poprawnym
    modelu fizyki — sygnał do przejrzenia założeń, nie do zwiększania limitu).
    """
    if initial.player_col == GOAL_COL:
        return []

    visited = {initial}
    queue: deque[tuple[ReactorState, list[str]]] = deque([(initial, [])])

    while queue:
        state, path = queue.popleft()
        if len(path) >= max_depth:
            continue

        for command in COMMANDS:
            next_state = apply_command(state, command)
            if next_state is None or next_state in visited:
                continue
            next_path = [*path, command]
            if next_state.player_col == GOAL_COL:
                return next_path
            visited.add(next_state)
            queue.append((next_state, next_path))

    return None


def state_from_api(response: dict) -> ReactorState:
    """Parsuje odpowiedź `/verify` (pola `player`/`blocks`) na `ReactorState`."""
    blocks = tuple(
        sorted(
            (Block(col=b["col"], top_row=b["top_row"], direction=b["direction"]) for b in response["blocks"]),
            key=lambda b: b.col,
        )
    )
    return ReactorState(player_col=response["player"]["col"], blocks=blocks)
