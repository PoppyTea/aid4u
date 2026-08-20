"""
S03E05 — model terenu i planer trasy. Czysta logika, zero I/O.

Reguły odkryte przez `/api/books` i `/api/wehicles` (zrzuty w
`data/input/s03e05_savethem/`):

- `R` blokuje ruch **całkowicie**, dla każdego trybu.
- `W` (woda) przekraczalna **wyłącznie** pieszo i konno; auto i rakieta giną.
- `T` (drzewo) przejezdne dla wszystkich, ale **+0.2 paliwa** dla trybów silnikowych.
- Zasoby zużywają się **przy ruchu**, nie przy wyborze pojazdu.
- Pojazd wybiera się **tylko na starcie**; jedyna zmiana trybu to `dismount`
  (zejście na piechotę, nieodwracalne).
- Budżet: 10 paliwa i 10 jedzenia; wyczerpanie któregokolwiek = porażka.

**Dlaczego front Pareto, a nie zwykły BFS.** Budżety są DWA i niezależne, więc nie
istnieje porządek całkowity na stanach: trasa tańsza w paliwie bywa droższa
w jedzeniu. Dla każdego `(wiersz, kolumna, tryb)` trzymamy więc zbiór
nieZdominowanych par `(paliwo, jedzenie)`; para odpada dopiero wtedy, gdy inna jest
od niej nie gorsza na OBU wymiarach. Zwykły BFS optymalizowałby liczbę ruchów, która
nie jest tu kryterium wykonalności — plan zachłanny na tej mapie zawodzi.

Zasoby liczymy w **dziesiątych częściach jako liczby całkowite** (2.5 → 25), żeby
dominacja Pareto była dokładna. Na floatach 0.1+0.2 != 0.3 potrafiłoby wyciąć
poprawne trasy przy porównaniu z budżetem.
"""

from __future__ import annotations

from dataclasses import dataclass

ROCK, WATER, TREE, START, GOAL, PLAIN = "R", "W", "T", "S", "G", "."

WALK = "walk"
DISMOUNT = "dismount"

# (paliwo, jedzenie) na ruch, w dziesiątych częściach jednostki.
CONSUMPTION: dict[str, tuple[int, int]] = {
    "walk": (0, 25),
    "horse": (0, 16),
    "car": (7, 10),
    "rocket": (10, 1),
}

VEHICLES = ("walk", "horse", "car", "rocket")

# Tryby, które w ogóle wjeżdżają na wodę. Auto „ginie natychmiast", rakieta „unosi
# się metr nad ziemią" — obie to zakaz, nie kara.
WATER_CAPABLE = frozenset({"walk", "horse"})

TREE_FUEL_PENALTY = 2  # 0.2 jednostki, tylko dla trybów silnikowych

# Budżet jest OSTRY, nie domknięty: zużycie równe 10.0 to porażka, nie granica.
# Ustalone empirycznie 2026-08-20 — trasa zużywająca dokładnie 10.0 paliwa dostała
# `-930 "Fuel reached zero. Mission failed."`. Notatka `resource-consumption`
# z `/api/books` mówi „if a vehicle runs out of fuel, the mission is considered
# failed", co czytaliśmy jako „przekroczy", a znaczy „dobije do zera".
BUDGET_FUEL = 100
BUDGET_FOOD = 100

# Ruchy w nazewnictwie oczekiwanym przez hub (patrz `doc/zadanie.md`).
MOVES: dict[str, tuple[int, int]] = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


@dataclass(frozen=True)
class Step:
    """Pojedynczy element trasy: ruch kierunkowy albo `dismount`."""

    action: str
    row: int
    col: int
    mode: str
    fuel: int
    food: int


@dataclass(frozen=True)
class Route:
    """Kompletna trasa gotowa do zgłoszenia."""

    vehicle: str
    steps: tuple[Step, ...]

    @property
    def answer(self) -> list[str]:
        """Format oczekiwany przez hub: `[nazwa_pojazdu, akcja, akcja, …]`."""
        return [self.vehicle, *(s.action for s in self.steps)]

    @property
    def fuel_used(self) -> float:
        """Zużyte paliwo w jednostkach (nie w dziesiątych)."""
        return (self.steps[-1].fuel if self.steps else 0) / 10

    @property
    def food_used(self) -> float:
        """Zużyte jedzenie w jednostkach (nie w dziesiątych)."""
        return (self.steps[-1].food if self.steps else 0) / 10


def parse_map(raw: list[list[str]] | list[str]) -> list[list[str]]:
    """
    Normalizuje mapę do listy list znaków.

    `/api/maps` zwraca ją dwojako — jako siatkę list (`map`) i jako tekst z liniami
    (`text`) — więc przyjmujemy oba kształty zamiast zakładać jeden.
    """
    if raw and isinstance(raw[0], str):
        return [list(line) for line in raw if line]  # type: ignore[arg-type]
    return [list(row) for row in raw]  # type: ignore[arg-type]


def find_cell(grid: list[list[str]], marker: str) -> tuple[int, int]:
    """Zwraca współrzędne pierwszego pola o danym znaku. Rzuca, gdy go nie ma."""
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            if value == marker:
                return r, c
    raise ValueError(f"Brak pola '{marker}' na mapie")


def passable(cell: str, mode: str) -> bool:
    """Czy dany tryb może WEJŚĆ na to pole."""
    if cell == ROCK:
        return False
    if cell == WATER:
        return mode in WATER_CAPABLE
    return True


def move_cost(cell: str, mode: str) -> tuple[int, int]:
    """Koszt (paliwo, jedzenie) wejścia na pole danym trybem, w dziesiątych."""
    fuel, food = CONSUMPTION[mode]
    if cell == TREE and fuel > 0:
        fuel += TREE_FUEL_PENALTY
    return fuel, food


def _prune(front: list[tuple[int, int]], fuel: int, food: int) -> bool:
    """
    Wstawia `(fuel, food)` do frontu Pareto. Zwraca False, gdy para jest zdominowana.

    Dominacja jest słaba: para odpada, gdy istnieje inna nie gorsza na OBU wymiarach.
    Przy okazji usuwamy z frontu pary, które nowa właśnie zdominowała — bez tego front
    puchłby o stany bezużyteczne.
    """
    for existing_fuel, existing_food in front:
        if existing_fuel <= fuel and existing_food <= food:
            return False
    front[:] = [
        (f, d) for f, d in front if not (fuel <= f and food <= d)
    ]
    front.append((fuel, food))
    return True


def plan_route(
    grid: list[list[str]],
    *,
    budget_fuel: int = BUDGET_FUEL,
    budget_food: int = BUDGET_FOOD,
    target: tuple[int, int] | None = None,
) -> Route | None:
    """
    Znajduje trasę mieszczącą się w obu budżetach albo zwraca None.

    Args:
        grid: Mapa jako siatka znaków.
        budget_fuel: Limit paliwa w dziesiątych (domyślnie 10 jednostek).
        budget_food: Limit jedzenia w dziesiątych.
        target: Pole docelowe. Domyślnie `G`; podanie innego pozwala celować
            w dowolną współrzędną (używane przy polu bobrów).

    Spośród tras spełniających budżet wybieramy tę o najmniejszej sumie zużycia —
    to arbitralne kryterium porządkujące, wprowadzone dopiero PO odfiltrowaniu
    wykonalnych, więc nie wpływa na poprawność.
    """
    start = find_cell(grid, START)
    goal = target if target is not None else find_cell(grid, GOAL)

    best: Route | None = None
    for vehicle in VEHICLES:
        route = _search_from(grid, start, goal, vehicle, budget_fuel, budget_food)
        if route is None:
            continue
        if best is None or (route.fuel_used + route.food_used) < (
            best.fuel_used + best.food_used
        ):
            best = route
    return best


def _search_from(
    grid: list[list[str]],
    start: tuple[int, int],
    goal: tuple[int, int],
    vehicle: str,
    budget_fuel: int,
    budget_food: int,
) -> Route | None:
    """Przeszukiwanie frontem Pareto dla jednego wyboru pojazdu startowego."""
    height, width = len(grid), len(grid[0])
    fronts: dict[tuple[int, int, str], list[tuple[int, int]]] = {}

    # Kolejka FIFO — przy dwóch kryteriach nie ma sensownego klucza priorytetu,
    # a front Pareto i tak przycina wszystko, co zdominowane.
    queue: list[tuple[int, int, str, int, int, tuple[Step, ...]]] = [
        (start[0], start[1], vehicle, 0, 0, ())
    ]
    fronts[(start[0], start[1], vehicle)] = [(0, 0)]

    reached: Route | None = None
    while queue:
        row, col, mode, fuel, food, path = queue.pop(0)

        if (row, col) == goal:
            candidate = Route(vehicle=vehicle, steps=path)
            if reached is None or (fuel + food) < (
                reached.steps[-1].fuel + reached.steps[-1].food if reached.steps else 0
            ):
                reached = candidate
            continue

        # `dismount` — zmiana trybu bez ruchu, więc bez kosztu. Jednokierunkowa:
        # z `walk` nie ma dokąd zsiadać, a wsiąść z powrotem się nie da.
        if mode != WALK:
            key = (row, col, WALK)
            front = fronts.setdefault(key, [])
            if _prune(front, fuel, food):
                step = Step(DISMOUNT, row, col, WALK, fuel, food)
                queue.append((row, col, WALK, fuel, food, (*path, step)))

        for action, (d_row, d_col) in MOVES.items():
            next_row, next_col = row + d_row, col + d_col
            if not (0 <= next_row < height and 0 <= next_col < width):
                continue
            cell = grid[next_row][next_col]
            if not passable(cell, mode):
                continue

            step_fuel, step_food = move_cost(cell, mode)
            new_fuel, new_food = fuel + step_fuel, food + step_food
            # Ostro `>=`, nie `>` — dobicie do zera zasobu kończy misję.
            if new_fuel >= budget_fuel or new_food >= budget_food:
                continue

            key = (next_row, next_col, mode)
            front = fronts.setdefault(key, [])
            if not _prune(front, new_fuel, new_food):
                continue

            step = Step(action, next_row, next_col, mode, new_fuel, new_food)
            queue.append((next_row, next_col, mode, new_fuel, new_food, (*path, step)))

    return reached


def simulate(grid: list[list[str]], route: Route) -> list[str]:
    """
    Odtwarza trasę krok po kroku i zwraca czytelny ślad.

    Symulacja jest niezależna od solvera — liczy zużycie od zera po samej liście
    akcji, więc łapie rozjazd między planem a jego zapisem ZANIM cokolwiek pójdzie
    na hub. Rzuca `ValueError` przy pierwszym naruszeniu reguł.
    """
    row, col = find_cell(grid, START)
    mode = route.vehicle
    fuel = food = 0
    trace = [f"start ({row},{col}) tryb={mode}"]

    for action in route.answer[1:]:
        if action == DISMOUNT:
            if mode == WALK:
                raise ValueError("dismount w trybie walk — nie ma z czego zsiadać")
            mode = WALK
            trace.append(f"dismount    ({row},{col}) tryb={mode}")
            continue

        if action not in MOVES:
            raise ValueError(f"Nieznana akcja: {action!r}")
        d_row, d_col = MOVES[action]
        row, col = row + d_row, col + d_col
        if not (0 <= row < len(grid) and 0 <= col < len(grid[0])):
            raise ValueError(f"Ruch {action} poza mapę na ({row},{col})")

        cell = grid[row][col]
        if not passable(cell, mode):
            raise ValueError(f"Tryb {mode} nie wejdzie na '{cell}' na ({row},{col})")

        step_fuel, step_food = move_cost(cell, mode)
        fuel += step_fuel
        food += step_food
        if fuel >= BUDGET_FUEL:
            raise ValueError(f"Paliwo wyczerpane na ({row},{col}): {fuel / 10}")
        if food >= BUDGET_FOOD:
            raise ValueError(f"Jedzenie wyczerpane na ({row},{col}): {food / 10}")

        trace.append(
            f"{action:<11} ({row},{col}) '{cell}' paliwo={fuel / 10:.1f} jedzenie={food / 10:.1f}"
        )

    return trace
