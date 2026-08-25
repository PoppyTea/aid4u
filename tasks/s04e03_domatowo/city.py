"""
S04E03 — geometria Domatowa: współrzędne, klastrowanie celów, planowanie desantu.

Cała logika przestrzenna siedzi tutaj i jest **czysta** (żadnego I/O), bo to ona
decyduje o koszcie operacji, a budżet 300 punktów akcji jest jedynym sposobem
przegrania tego zadania. Dzięki temu plan da się przetestować bez ruszania huba.

## Model kosztu (zmierzony na żywo, nie z treści zadania)

Treść podaje cenniki, ale nie mówi dwóch rzeczy, które wyszły dopiero z sondy:

- `move` raportuje `path_steps` **wliczając pole startowe**, a nalicza za `path_steps - 1`.
  Zmierzone: A6→A10 to `path_steps: 5` przy koszcie 28 = 4 × 7.
- Zwiadowca chodzi po dowolnym terenie (potwierdzone wejściem na `block3`), więc jego
  trasa to odległość Manhattan. Transporter jeździ wyłącznie po ulicach.

Stąd: `koszt_zwiadowcy(p, q) = manhattan(p, q) * 7`, a transporter liczy się po ścieżce
w grafie ulic — czyli 7× drożej ruszać zwiadowcą niż dowieźć go pojazdem.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

COLUMNS = "ABCDEFGHIJK"
SIZE = 11

# Kafelek, w którym ukrywa się partyzant. Z przechwyconego sygnału: „Ukryłem się
# w jednym z najwyższych bloków" — a najwyższy w legendzie mapy jest `block3` („Blok 3p").
TARGET_TILE = "block3"
ROAD_TILE = "road"


def to_coord(row: int, col: int) -> str:
    """Indeksy `(wiersz, kolumna)` liczone od zera na etykietę pola: `(9, 1)` → `B10`."""
    return f"{COLUMNS[col]}{row + 1}"


def from_coord(field: str) -> tuple[int, int]:
    """Odwrotność `to_coord()` — `B10` → `(9, 1)`."""
    return int(field[1:]) - 1, COLUMNS.index(field[0])


def manhattan(a: str, b: str) -> int:
    """Odległość, jaką pokona zwiadowca — chodzi ortogonalnie i po dowolnym terenie."""
    (ra, ca), (rb, cb) = from_coord(a), from_coord(b)
    return abs(ra - rb) + abs(ca - cb)


def neighbours(field: str) -> list[str]:
    """Pola stykające się bokiem, przycięte do planszy."""
    row, col = from_coord(field)
    candidates = ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
    return [to_coord(r, c) for r, c in candidates if 0 <= r < SIZE and 0 <= c < SIZE]


def tiles_of(grid: list[list[str]], kind: str) -> list[str]:
    """Wszystkie pola danego typu terenu, w kolejności czytania mapy."""
    return [
        to_coord(r, c) for r, row in enumerate(grid) for c, tile in enumerate(row) if tile == kind
    ]


def cluster(fields: list[str]) -> list[list[str]]:
    """
    Grupuje pola w spójne bryły (sąsiedztwo bokiem).

    Cele nie są rozsypane po mapie, tylko tworzą budynki. Klaster to jednostka
    planowania: jeden transporter dowozi grupę zwiadowców pod jeden budynek,
    a dalej chodzą oni po sąsiadujących polach po 7 punktów za krok.

    Returns:
        Bryły posortowane malejąco po rozmiarze — większy budynek to większa
        szansa, że partyzant jest właśnie w nim, więc zaczynamy od niego.
    """
    remaining = set(fields)
    groups: list[list[str]] = []

    while remaining:
        seed = min(remaining)
        group, queue = [], deque([seed])
        remaining.discard(seed)
        while queue:
            field = queue.popleft()
            group.append(field)
            for other in neighbours(field):
                if other in remaining:
                    remaining.discard(other)
                    queue.append(other)
        groups.append(sorted(group))

    return sorted(groups, key=lambda g: (-len(g), g[0]))


def road_distances(roads: set[str], start: str) -> dict[str, int]:
    """
    Liczba pól, jakie transporter musi przejechać ze `start` do każdej osiągalnej ulicy.

    BFS po samych ulicach — transporter nie zjeżdża z drogi, więc odległość Manhattan
    byłaby tu kłamstwem (potrafi nie istnieć żadna trasa mimo bliskości w linii prostej).

    Gdy `start` sam nie jest ulicą, transporter nie ruszy się z miejsca i nic nie jest
    osiągalne. Zaszycie punktu startowego w wyniku „bo przecież tam stoi" dawałoby plan
    wysadzający desant poza drogą — czyli akcję, której API nie wykona.
    """
    if start not in roads:
        return {}

    distances = {start: 0}
    queue = deque([start])
    while queue:
        field = queue.popleft()
        for other in neighbours(field):
            if other in roads and other not in distances:
                distances[other] = distances[field] + 1
                queue.append(other)
    return distances


@dataclass(frozen=True)
class Landing:
    """Punkt wysadzenia grupy zwiadowców pod jeden budynek."""

    dropoff: str
    """Ulica, na którą dojedzie transporter."""
    targets: list[str]
    """Pola tego budynku, do sprawdzenia."""
    drive_cost: int
    """Punkty akcji za dojazd transportera ze spawnu."""


def plan_landing(targets: list[str], roads: set[str], spawn: str) -> Landing:
    """
    Wybiera ulicę do wysadzenia desantu pod dany budynek.

    Kryterium to **suma odległości od punktu zrzutu do wszystkich celów budynku**,
    a nie sama bliskość dojazdu: krok transportera kosztuje 1 punkt, a krok zwiadowcy 7,
    więc opłaca się nadłożyć drogi pojazdem, żeby skrócić marsz pieszo. Remisy
    rozstrzyga tańszy dojazd, a potem nazwa pola — plan ma być powtarzalny.

    Raises:
        ValueError: Gdy żadna ulica nie jest osiągalna ze spawnu.
    """
    reachable = road_distances(roads, spawn)
    if not reachable:
        raise ValueError(f"Ze spawnu {spawn} nie da się dojechać do żadnej ulicy.")

    best = min(
        reachable,
        key=lambda road: (
            sum(manhattan(road, t) for t in targets),
            reachable[road],
            road,
        ),
    )
    return Landing(dropoff=best, targets=list(targets), drive_cost=reachable[best])


def sweep_order(targets: list[str], scouts: dict[str, str]) -> list[tuple[str, str]]:
    """
    Układa kolejność sprawdzania celów: kto idzie na które pole i w jakiej kolejności.

    Zachłannie po najtańszym kroku — za każdym razem bierzemy parę (zwiadowca, cel)
    o najmniejszej odległości i przesuwamy tego zwiadowcę na sprawdzone pole. Dzięki
    temu kolejne cele w tym samym budynku kosztują zwykle jeden krok, bo zwiadowca
    stoi już w środku bryły.

    To jest heurystyka, nie optimum — pełne przypisanie byłoby problemem komiwojażera
    dla 14 pól. Przy zmierzonym budżecie nie ma to znaczenia: liczy się, żeby nie
    prowadzić zwiadowcy przez pół mapy, co jest jedynym udokumentowanym sposobem
    przepalenia 300 punktów.

    Args:
        targets: Pola do sprawdzenia.
        scouts: Mapa `identyfikator zwiadowcy → jego bieżące pole`. Identyfikator
            i pozycja MUSZĄ być rozdzielone — API adresuje jednostki hashem, a koszt
            liczy się po współrzędnych.

    Returns:
        Lista par `(identyfikator zwiadowcy, cel)` w kolejności wykonania.
    """
    positions = dict(scouts)
    pending = list(targets)
    plan: list[tuple[str, str]] = []

    while pending:
        scout, target = min(
            ((s, t) for s in positions for t in pending),
            key=lambda pair: (manhattan(positions[pair[0]], pair[1]), pair[1]),
        )
        plan.append((scout, target))
        positions[scout] = target
        pending.remove(target)

    return plan
