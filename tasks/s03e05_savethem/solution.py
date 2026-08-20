"""
S03E05 `savethem` — planowanie trasy posłańca do Skolwina.

Zero LLM. Narzędzia Centrali odkrywa `discover.py` (raz, wynik commitowany), a trasę
liczy deterministyczny planer z `terrain.py` — front Pareto po `(wiersz, kolumna,
tryb)`. Uzasadnienie wyboru algorytmu: patrz docstring `terrain.py` i `AGENTS.md`.

Kluczowy fakt, którego bez policzenia nie widać: **żaden pojedynczy tryb nie dowozi
do celu**. Dystans Manhattan S→G to 11 ruchów, a marsz (2.5 jedzenia/ruch), koń (1.6),
auto (1.0 jedzenia + 0.7 paliwa) i rakieta (1.0 paliwa) przekraczają wtedy budżet —
do tego auto i rakieta w ogóle nie wejdą do wody, a cel jest odcięty rzeką. `dismount`
jest więc warunkiem koniecznym, nie optymalizacją.

Uruchomienie:
    uv run python -m tasks.s03e05_savethem.discover   # raz, zrzut narzędzi
    uv run run.py solve s03e05 --dry-run              # plan + symulacja, bez huba
    uv run run.py solve s03e05                        # zgłoszenie
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import json
from pathlib import Path

from rich.console import Console

from core.tasks import BaseTask, task
from tasks.s03e05_savethem.terrain import Route, parse_map, plan_route, simulate

_console = Console()

DATA_DIR = Path("data/input/s03e05_savethem")
CITY = "Skolwin"


def load_grid(data_dir: Path | None = None) -> list[list[str]]:
    """
    Wczytuje mapę ze zrzutu `/api/maps`.

    Solver czyta ZRZUT, nie żywe API — dzięki temu `--dry-run`, testy i powtórne
    przebiegi nie zależą od sieci ani od tego, czy hub akurat odpowiada.
    """
    path = (data_dir or DATA_DIR) / "maps.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Brak {path} — uruchom najpierw: uv run python -m tasks.s03e05_savethem.discover"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))[CITY]
    return parse_map(payload["map"])


def build_route(grid: list[list[str]], *, target: tuple[int, int] | None = None) -> Route:
    """Liczy trasę i weryfikuje ją symulacją. Rzuca, gdy plan nie jest wykonalny."""
    route = plan_route(grid, target=target)
    if route is None:
        raise RuntimeError("Planer nie znalazł trasy mieszczącej się w budżecie")

    for line in simulate(grid, route):
        _console.print(f"  [dim]{line}[/]")
    _console.print(
        f"[bold]Trasa:[/] {route.vehicle}, {len(route.answer) - 1} akcji, "
        f"paliwo {route.fuel_used}/10, jedzenie {route.food_used}/10"
    )
    return route


@task("s03e05", hub_name="savethem")
class SaveThemTask(BaseTask):
    """Planuje trasę i zgłasza ją jako płaską listę `[pojazd, akcja, …]`."""

    def solve(self, data: None) -> list[str]:
        """
        Zwraca trasę w formacie oczekiwanym przez hub.

        Symulacja w `build_route()` jest twardą bramką: trasa łamiąca reguły terenu
        albo budżet rzuca wyjątkiem tutaj, a nie po stronie huba — na tej mapie
        pomyłka kosztuje przebieg, bo budżet ma zero marginesu (8.0/10 i 8.3/10).
        """
        return build_route(load_grid()).answer


if __name__ == "__main__":
    build_route(load_grid())
