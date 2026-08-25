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
    allocate_scouts,
    cluster,
    reads_as_found,
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
        assert {t: s for s, t in plan} == {"A1": "blisko-A1", "K11": "blisko-K11"}


class TestOdczytLogu:
    """
    `reads_as_found()` — klasyfikacja zdań `inspect`.

    Wszystkie poniższe komunikaty są DOSŁOWNE, zebrane z pełnego przemiatania 14 pól
    2026-08-25. To jedyne miejsce, gdzie rozwiązanie opiera się o treść generowaną
    przez backend, więc jest pokryte najgęściej.
    """

    NEGATYWY = [
        "Nie ma żadnej osoby. Trafiłem tylko na szczura i pęknięte lustro.",
        "Pomieszczenie bez celu. Jest rozbita lornetka.",
        "Pokój pusty. Dźwięk był mylący, to tylko kapanie wody.",
        "Nic wartościowego. Puste ściany, rozrzucone papiery i stary garnek.",
        "Pomieszczenie bez ludzi. Znalazłem zardzewiały śrubokręt.",
        "Brak obecności. Są resztki jedzenia, ale miejsce opuszczone.",
        "Nie stwierdzono obecności. Tylko kilka mokrych gazet.",
        "Rozglądnąłem się dwa razy. Poza workiem pełnym śmieci nie ma tu nic.",
        "Tu tylko śmieci. Żadnych żywych kontaktów.",
        "Przeszukanie nic nie wykazało. Znalazłem jedną rękawicę.",
        "Nie ma nikogo. Jest kilka butelek, ale wszystkie puste.",
        "Miejsce opuszczone. Znalazłem latarkę, ale nikogo przy niej nie było.",
        # Trzy poniższe pojawiły się dopiero w przebiegu zdobywającym flagę (2026-08-25),
        # dzień po zebraniu reszty — dowód, że słownik backendu jest otwarty.
        "Cel nieobecny. Za drzwiami była torba, ale w środku same gazety.",
        "Cel nieobecny. Ślady prowadzą dalej korytarzem.",
        "Pomieszczenie czyste. Jest wiadro, szczur i kilka gwoździ.",
    ]

    @pytest.mark.parametrize("msg", NEGATYWY)
    def test_puste_pole(self, msg: str) -> None:
        assert reads_as_found(msg) is False

    def test_trafienie(self) -> None:
        """Jedyny zaobserwowany pozytyw — dosłownie tak brzmi znalezienie partyzanta."""
        found = "Cel jest z nami. Mężczyzna około 30 lat, ranny w ramię, ale przytomny."
        assert reads_as_found(found) is True

    def test_rzeczownik_osobowy_sam_w_sobie_nie_wystarcza(self) -> None:
        """
        „Nie ma żadnej osoby" mówi o człowieku i o jego BRAKU naraz.

        Dlatego wymagane są oba sygnały, a nie sam pozytywny — inaczej pierwsze puste
        pole zakończyłoby misję wezwaniem śmigłowca w złe miejsce.
        """
        assert reads_as_found("Nie ma żadnego mężczyzny.") is False

    def test_znalezisko_to_nie_czlowiek(self) -> None:
        """„Znalazłem latarkę, ale nikogo przy niej nie było" — czasownik zgadza się, sens nie."""
        assert reads_as_found("Miejsce opuszczone. Znalazłem latarkę.") is False

    def test_nieznane_slownictwo_daje_none_nie_false(self) -> None:
        """
        Cicha porażka jest tu droższa niż głośna: gdyby backend zmienił styl komunikatów,
        `False` dla wszystkiego wyglądałoby jak „plansza pusta", a `None` każe przeczytać
        logi oczami. Rozwiązanie zlicza takie przypadki i mówi o nich w błędzie końcowym.
        """
        assert reads_as_found("Zupełnie inne sformułowanie backendu.") is None


class TestPrzydzialZwiadowcow:
    """
    Limit 8 zwiadowców jest globalny na operację, nie na desant.

    Regresja z żywego przebiegu: dwa pełne czterosobowe desanty wyczerpały limit
    i trzeci `create` odbił się od API z HTTP 400 — przy trzecim z trzech budynków,
    czyli po wydaniu punktów na dwa poprzednie.
    """

    def test_realna_mapa_miesci_sie_w_limicie(self) -> None:
        """Domatowo ma budynki 6/4/4 pól — przydział nie może przekroczyć ośmiu ludzi."""
        allocation = allocate_scouts([6, 4, 4], max_scouts=8, max_per_transporter=4)
        assert sum(allocation) <= 8
        assert all(a >= 1 for a in allocation)

    def test_kazdy_budynek_dostaje_kogos(self) -> None:
        """Budynek bez zwiadowcy zostałby nieprzeszukany — to cicha porażka misji."""
        allocation = allocate_scouts([5, 1, 1, 1], max_scouts=4, max_per_transporter=4)
        assert allocation == [1, 1, 1, 1]

    def test_nadwyzka_idzie_do_najwiekszego(self) -> None:
        """Większy budynek to większa szansa trafienia, a przerywamy przy pierwszym."""
        allocation = allocate_scouts([6, 2], max_scouts=8, max_per_transporter=4)
        assert allocation[0] > allocation[1]

    def test_nie_przydziela_wiecej_niz_pol_w_budynku(self) -> None:
        """Piąty zwiadowca w budynku o czterech polach nie ma czego sprawdzać."""
        allocation = allocate_scouts([2, 2], max_scouts=8, max_per_transporter=4)
        assert allocation == [2, 2]

    def test_szanuje_pojemnosc_transportera(self) -> None:
        """Jeden transporter bierze najwyżej czterech pasażerów."""
        allocation = allocate_scouts([10], max_scouts=8, max_per_transporter=4)
        assert allocation == [4]

    def test_wiecej_budynkow_niz_ludzi_przerywa(self) -> None:
        with pytest.raises(ValueError, match="nieprzeszukany"):
            allocate_scouts([1, 1, 1], max_scouts=2, max_per_transporter=4)
