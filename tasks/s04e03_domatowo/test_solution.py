"""
Testy s04e03 — offline, bez sieci.

Cała geometria i planowanie kosztu żyją w `city.py` jako funkcje czyste, więc dają się
sprawdzić bez huba. To nie jest kosmetyka: budżet 300 punktów akcji jest **jedynym**
sposobem przegrania tego zadania, a błąd w planie kosztuje cały przebieg.

Jeden z tych testów istnieje, bo pierwsza wersja `sweep_order()` myliła identyfikator
zwiadowcy z jego pozycją — API adresuje jednostki hashem, a koszt liczy się po
współrzędnych. Błąd wyszedł dopiero na żywym hubie, w połowie desantu.
"""

from __future__ import annotations

import pytest

from tasks.s04e03_domatowo.city import (
    cluster,
    from_coord,
    manhattan,
    neighbours,
    plan_landing,
    road_distances,
    sweep_order,
    tiles_of,
    to_coord,
)

# Fragment realnej mapy Domatowa: wiersz ulic na dole, dwa cele nad nim.
GRID = [
    ["empty", "block3", "block3", "empty"],
    ["empty", "road", "road", "road"],
    ["empty", "empty", "empty", "road"],
    ["block3", "empty", "empty", "road"],
]


class TestWspolrzedne:
    """Etykiety pól API (`A1`..`K11`) kontra indeksy tablicy."""

    @pytest.mark.parametrize(
        ("row", "col", "field"),
        [(0, 0, "A1"), (9, 1, "B10"), (10, 10, "K11"), (5, 0, "A6")],
    )
    def test_tam_i_z_powrotem(self, row: int, col: int, field: str) -> None:
        """Kolumna to litera, wiersz to liczba OD JEDNEGO — pomyłka o jeden psuje cały plan."""
        assert to_coord(row, col) == field
        assert from_coord(field) == (row, col)

    def test_dwucyfrowy_wiersz(self) -> None:
        """`B10` i `B11` mają dwucyfrową część liczbową — parser nie może brać tylko znaku."""
        assert from_coord("B11") == (10, 1)

    def test_manhattan_to_koszt_marszu(self) -> None:
        """Zwiadowca chodzi ortogonalnie po dowolnym terenie, więc dystans jest Manhattanowy."""
        assert manhattan("A6", "A10") == 4
        assert manhattan("B9", "C10") == 2

    def test_sasiedzi_przyciete_do_planszy(self) -> None:
        """Róg planszy ma dwóch sąsiadów, nie czterech."""
        assert sorted(neighbours("A1")) == ["A2", "B1"]


class TestKlastrowanie:
    """Cele tworzą budynki — to jednostka planowania desantu."""

    def test_grupuje_stykajace_sie_pola(self) -> None:
        groups = cluster(tiles_of(GRID, "block3"))
        assert [sorted(g) for g in groups] == [["B1", "C1"], ["A4"]]

    def test_najwiekszy_budynek_pierwszy(self) -> None:
        """
        Kolejność ma znaczenie operacyjne: przy równomiernym losowaniu pozycji
        partyzanta większy budynek to większa szansa trafienia, a przerywamy
        przy pierwszym znalezieniu.
        """
        groups = cluster(["A1", "A2", "A3", "K11"])
        assert len(groups[0]) == 3

    def test_pola_stykajace_sie_rogiem_to_osobne_budynki(self) -> None:
        """Sąsiedztwo jest bokiem — po przekątnej zwiadowca i tak musi zrobić dwa kroki."""
        assert len(cluster(["A1", "B2"])) == 2


class TestPlanowanieDesantu:
    """Punkt zrzutu: 1 pkt za pole transporterem kontra 7 pkt pieszo."""

    def test_wybiera_ulice_najblizej_calego_budynku(self) -> None:
        roads = set(tiles_of(GRID, "road"))
        landing = plan_landing(["B1", "C1"], roads, "D2")
        assert landing.dropoff in {"B2", "C2"}

    def test_oplaca_sie_nadlozyc_droge_pojazdem(self) -> None:
        """
        Krok zwiadowcy kosztuje 7×  tyle co krok transportera, więc kryterium jest
        suma odległości do celów, a nie sam dojazd. Ulica tuż przy spawnie, ale daleko
        od budynku, ma przegrać z dalszą, która stawia desant pod drzwiami.
        """
        roads = {"A1", "B1", "C1", "D1"}
        landing = plan_landing(["D3"], roads, "A1")
        assert landing.dropoff == "D1"
        assert landing.drive_cost == 3

    def test_brak_dojazdu_przerywa(self) -> None:
        with pytest.raises(ValueError, match="nie da się dojechać"):
            plan_landing(["A1"], set(), "A6")

    def test_odleglosci_licza_sie_po_ulicach_nie_w_linii_prostej(self) -> None:
        """Transporter nie zjeżdża z drogi — pole odcięte jest nieosiągalne mimo bliskości."""
        distances = road_distances({"A1", "A2", "C1"}, "A1")
        assert distances == {"A1": 0, "A2": 1}


class TestKolejnoscPrzeszukania:
    """`sweep_order()` — kto idzie na które pole."""

    def test_rozroznia_identyfikator_od_pozycji(self) -> None:
        """
        Regresja: pierwsza wersja przekazywała listę identyfikatorów i liczyła po nich
        odległość, co wywalało się na hashu jednostki. API adresuje zwiadowcę hashem,
        a koszt liczy po współrzędnych — to dwie różne rzeczy.
        """
        plan = sweep_order(["B10"], {"hash-nie-wspolrzedna": "B9"})
        assert plan == [("hash-nie-wspolrzedna", "B10")]

    def test_kazdy_cel_odwiedzony_dokladnie_raz(self) -> None:
        targets = ["A10", "B10", "C10", "A11", "B11", "C11"]
        plan = sweep_order(targets, {"s1": "B9", "s2": "C9"})
        assert sorted(t for _, t in plan) == sorted(targets)
        assert len(plan) == len(targets)

    def test_zaczyna_od_celu_pod_nogami(self) -> None:
        """Zwiadowca wysadzony prosto na cel ma go sprawdzić bez ruchu — krok kosztuje 7 pkt."""
        plan = sweep_order(["B10", "C11"], {"s1": "B10"})
        assert plan[0] == ("s1", "B10")

    def test_wykorzystuje_obu_zwiadowcow_zamiast_prowadzic_jednego(self) -> None:
        """
        Jedyny udokumentowany sposób przegrania to „agent zasuwa jednym zwiadowcą
        na piechotę" — plan ma rozdzielać cele między dostępnych ludzi.
        """
        plan = sweep_order(["A1", "K11"], {"blisko-A1": "A2", "blisko-K11": "K10"})
        assert dict((t, s) for s, t in plan) == {"A1": "blisko-A1", "K11": "blisko-K11"}
