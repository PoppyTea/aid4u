"""
Testy s03e05 — offline, na PRAWDZIWEJ mapie ze zrzutu `data/input/`.

Nacisk na reguły, których złamanie kończy misję po stronie huba (skała, woda, budżet)
oraz na `dismount` — mechanikę, której wg społeczności modele same nie odkrywają,
a bez której to zadanie jest **nierozwiązywalne**, nie tylko trudniejsze.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tasks.s03e05_savethem.terrain import (
    BUDGET_FOOD,
    BUDGET_FUEL,
    CONSUMPTION,
    Route,
    Step,
    find_cell,
    move_cost,
    parse_map,
    passable,
    plan_route,
    simulate,
)

_MAP_DUMP = Path("data/input/s03e05_savethem/maps.json")


@pytest.fixture(scope="module")
def grid() -> list[list[str]]:
    """Mapa Skolwina ze zrzutu `/api/maps` — testujemy na realnych danych."""
    return parse_map(json.loads(_MAP_DUMP.read_text(encoding="utf-8"))["Skolwin"]["map"])


class TestPrzejezdnosc:
    """Reguły terenu z `/api/books` — złamanie którejkolwiek kończy misję."""

    def test_skala_blokuje_wszystkich(self):
        """`R` blokuje ruch całkowicie — nie ma trybu, który ją pokona."""
        assert not any(passable("R", mode) for mode in CONSUMPTION)

    def test_wode_pokonuje_tylko_marsz_i_kon(self):
        """Auto ginie w wodzie, rakieta unosi się metr nad ziemią."""
        assert passable("W", "walk") and passable("W", "horse")
        assert not passable("W", "car") and not passable("W", "rocket")

    def test_drzewo_przejezdne_dla_wszystkich(self):
        assert all(passable("T", mode) for mode in CONSUMPTION)

    def test_drzewo_dolicza_paliwo_tylko_silnikowym(self):
        """+0.2 dotyczy „powered travel" — koń i marsz nie palą paliwa wcale."""
        assert move_cost("T", "rocket")[0] == CONSUMPTION["rocket"][0] + 2
        assert move_cost("T", "car")[0] == CONSUMPTION["car"][0] + 2
        assert move_cost("T", "horse")[0] == 0
        assert move_cost("T", "walk")[0] == 0

    def test_drzewo_nie_zmienia_jedzenia(self):
        assert move_cost("T", "rocket")[1] == move_cost(".", "rocket")[1]


class TestMapaSkolwina:
    """Założenia o konkretnej mapie, na których opiera się cała trasa."""

    def test_start_i_cel(self, grid):
        assert find_cell(grid, "S") == (7, 0)
        assert find_cell(grid, "G") == (4, 8)

    def test_cel_jest_odciety_rzeka(self, grid):
        """
        Każdy wiersz ma wodę w pasie kolumn 5-9, więc prawa strona z celem jest
        nieosiągalna bez przekroczenia `W`. To jest powód, dla którego `dismount`
        nie jest optymalizacją, tylko warunkiem koniecznym.
        """
        assert all("W" in row[5:] for row in grid)


class TestKoniecznoscDismount:
    """Sedno epizodu: żaden pojedynczy tryb nie dowozi do celu."""

    @pytest.mark.parametrize("mode", ["walk", "horse", "car", "rocket"])
    def test_zaden_pojazd_nie_da_rady_sam(self, grid, mode):
        """
        Dystans Manhattan S→G to 11 ruchów. Marsz i koń przekraczają jedzenie,
        auto oba budżety, rakieta paliwo — a auto i rakieta dodatkowo nie wejdą
        do wody. Test liczy to wprost z parametrów, nie z zapamiętanego wyniku.
        """
        fuel, food = CONSUMPTION[mode]
        assert fuel * 11 > BUDGET_FUEL or food * 11 > BUDGET_FOOD

    def test_planer_uzywa_dismount(self, grid):
        route = plan_route(grid)
        assert route is not None
        assert "dismount" in route.answer

    def test_dismount_nie_kosztuje_zasobow(self, grid):
        """Zasoby idą przy RUCHU, nie przy zmianie trybu — inaczej trasa nie wchodzi w budżet."""
        route = plan_route(grid)
        steps = route.steps
        idx = next(i for i, s in enumerate(steps) if s.action == "dismount")
        assert (steps[idx].fuel, steps[idx].food) == (steps[idx - 1].fuel, steps[idx - 1].food)


class TestPlanera:
    """Wynik planera musi być wykonalny, nie tylko krótki."""

    def test_trasa_istnieje_i_miesci_sie_w_budzecie(self, grid):
        route = plan_route(grid)
        assert route is not None
        assert route.fuel_used <= 10 and route.food_used <= 10

    def test_pierwszy_element_to_pojazd(self, grid):
        route = plan_route(grid)
        assert route.answer[0] in CONSUMPTION

    def test_trasa_konczy_sie_na_celu(self, grid):
        route = plan_route(grid)
        assert (route.steps[-1].row, route.steps[-1].col) == find_cell(grid, "G")

    def test_symulacja_potwierdza_plan(self, grid):
        """Symulator liczy zużycie od zera po samej liście akcji — łapie rozjazd plan/zapis."""
        route = plan_route(grid)
        trace = simulate(grid, route)
        assert trace[-1].endswith("jedzenie=8.3") or "G" in trace[-1]

    def test_nieosiagalny_cel_zwraca_none(self, grid):
        """Pole otoczone skałami: planer ma powiedzieć „nie da się", nie zwrócić bylejaką trasę."""
        walled = [row[:] for row in grid]
        for r in range(len(walled)):
            for c in range(len(walled[0])):
                if walled[r][c] == "G":
                    walled[r][c] = "."
        walled[0][0] = "G"
        for r, c in ((0, 1), (1, 0), (1, 1)):
            walled[r][c] = "R"
        assert plan_route(walled) is None


class TestSymulatora:
    """Symulator jest ostatnią bramką przed hubem — musi odrzucać złe trasy."""

    def test_odrzuca_wjazd_w_skale_pojazdem(self, grid):
        """`(7,1)` to `R` tuż obok startu — symulator ma to złapać, nie hub."""
        with pytest.raises(ValueError, match="nie wejdzie"):
            simulate(grid, Route(vehicle="car", steps=(Step("right", 7, 1, "car", 7, 10),)))

    def test_odrzuca_wjazd_w_wode_pojazdem(self, grid):
        """
        Rakieta w wodzie = utrata pojazdu.

        Trasa celowo dobrana tak, by dobić do rzeki `(3,6)` na dziesiątym ruchu —
        czyli ZANIM wyczerpie się paliwo. Inaczej test przechodziłby z powodu
        limitu zasobów i nie sprawdzał tego, co miał.
        """
        route = Route(
            vehicle="rocket",
            steps=tuple(Step("up", 6 - i, 0, "rocket", 0, 0) for i in range(4))
            + tuple(Step("right", 3, c, "rocket", 0, 0) for c in range(1, 7)),
        )
        with pytest.raises(ValueError, match="nie wejdzie"):
            simulate(grid, route)

    def test_odrzuca_dismount_w_trybie_walk(self, grid):
        with pytest.raises(ValueError, match="dismount"):
            simulate(grid, Route(vehicle="walk", steps=(Step("dismount", 7, 0, "walk", 0, 0),)))

    def test_odrzuca_nieznana_akcje(self, grid):
        with pytest.raises(ValueError, match="Nieznana akcja"):
            simulate(grid, Route(vehicle="walk", steps=(Step("teleport", 7, 0, "walk", 0, 0),)))

    def test_odrzuca_przekroczenie_jedzenia(self, grid):
        """Marsz po 2.5 na ruch wyczerpuje jedzenie na piątym kroku."""
        steps = tuple(Step("up", 7 - i, 0, "walk", 0, 0) for i in range(1, 6))
        with pytest.raises(ValueError, match="Jedzenie wyczerpane"):
            simulate(grid, Route(vehicle="walk", steps=steps))
