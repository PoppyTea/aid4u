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


def allocate_scouts(
    building_sizes: list[int], max_scouts: int, max_per_transporter: int
) -> list[int]:
    """
    Dzieli limit zwiadowców między budynki, zanim ruszy pierwszy transporter.

    Limit 8 zwiadowców jest globalny na całą operację, a nie na desant — dwa pełne
    czterosobowe desanty wyczerpują go w całości i trzeci `create` odbija się od API
    (potwierdzone na żywo: HTTP 400 przy trzecim budynku). Dlatego przydział musi
    powstać z góry, dla wszystkich budynków naraz.

    Każdy budynek dostaje minimum jednego zwiadowcę; reszta idzie do największych,
    bo przy równomiernym losowaniu pozycji partyzanta to tam najczęściej się kończy.

    Raises:
        ValueError: Gdy budynków jest więcej niż zwiadowców — wtedy któryś zostałby
            nieprzeszukany, a to cicha porażka: misja skończyłaby się „nie znaleziono".
    """
    if len(building_sizes) > max_scouts:
        raise ValueError(
            f"{len(building_sizes)} budynków przy limicie {max_scouts} zwiadowców — "
            "któryś zostałby nieprzeszukany."
        )

    allocation = [1] * len(building_sizes)
    spare = max_scouts - len(building_sizes)

    # Kolejność malejąco po rozmiarze budynku; przy remisie decyduje kolejność wejściowa,
    # żeby przydział był powtarzalny między przebiegami.
    order = sorted(range(len(building_sizes)), key=lambda i: (-building_sizes[i], i))
    while spare > 0:
        progressed = False
        for i in order:
            headroom = min(max_per_transporter, building_sizes[i]) - allocation[i]
            if spare > 0 and headroom > 0:
                allocation[i] += 1
                spare -= 1
                progressed = True
        if not progressed:
            break

    return allocation


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


# Komunikaty `inspect` są zdaniami generowanymi o zmiennym słownictwie, więc rozpoznanie
# sukcesu musi opierać się na SENSIE, nie na dopasowaniu konkretnego zdania. Zebrane
# z pełnego przemiatania 14 pól (2026-08-25); wszystkie negatywy mówią o braku:
#
#   „Nie ma żadnej osoby…", „Pomieszczenie bez celu…", „Pokój pusty…",
#   „Nic wartościowego…", „Brak obecności…", „Nie stwierdzono obecności…",
#   „Tu tylko śmieci. Żadnych żywych kontaktów.", „Przeszukanie nic nie wykazało…",
#   „Miejsce opuszczone…", „Nie ma nikogo…"
#
# a jedyny pozytyw mówi o człowieku:
#
#   „Cel jest z nami. Mężczyzna około 30 lat, ranny w ramię, ale przytomny."
#
# ⚠️ Ten słownik jest OTWARTY i wiadomo o tym z pomiaru, nie z przypuszczenia: przebieg
# zdobywający flagę (2026-08-25) przyniósł trzy sformułowania spoza listy zebranej dzień
# wcześniej — „Cel nieobecny…", „Pomieszczenie czyste…". Dopisane niżej, ale sama lista
# nigdy nie będzie kompletna. Dlatego `reads_as_found()` zwraca dla nieznanego zdania
# `None`, a nie `False`: to ta gałąź, nie ta lista, jest zabezpieczeniem.
ABSENCE_MARKERS = (
    "nie ma",
    "brak",
    "nikogo",
    "pust",
    "nic ",
    "nie stwierdzono",
    "nie wykazało",
    "opuszczone",
    "bez ludzi",
    "bez celu",
    "żadnych",
    "nieobecn",
    "czyste",
)

PRESENCE_MARKERS = (
    "cel jest z nami",
    "mężczyzn",
    "kobiet",
    "człowiek",
    "ranny",
    "przytomn",
    "partyzant",
)


def reads_as_found(message: str) -> bool | None:
    """
    Ocenia wpis logu `inspect`: znaleziony, pusty, czy nierozpoznany.

    Wymagamy OBU sygnałów naraz — obecności człowieka i braku słów o pustce — bo każdy
    z osobna jest zawodny: „Nie ma żadnej osoby" zawiera rzeczownik osobowy, a „Znalazłem
    latarkę, ale nikogo przy niej nie było" mówi o znalezisku. Zdanie, które nie pasuje
    do żadnej z grup, zwraca `None` zamiast `False`: to sygnał, że słownictwo się
    rozjechało i wynik przemiatania trzeba przeczytać oczami, a nie cicha porażka.

    Returns:
        `True` gdy człowiek potwierdzony, `False` gdy pole puste, `None` gdy nie wiadomo.
    """
    text = message.casefold()
    absent = any(marker in text for marker in ABSENCE_MARKERS)
    present = any(marker in text for marker in PRESENCE_MARKERS)

    if present and not absent:
        return True
    if absent:
        return False
    return None
