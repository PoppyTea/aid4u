"""Testy map_analysis.py — obrazy syntetyczne generowane w locie, bez sieci i bez fixture'ów binarnych."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from tasks.s02e05_drone.map_analysis import (
    DamSectorAmbiguousError,
    detect_dam_sector,
    detect_grid,
)

_RED = (220, 20, 20)
_BLUE = (20, 20, 220)
_BG = (200, 200, 180)  # tło ziemi — celowo NIE czerwone i NIE niebieskie


def _make_grid_image(
    *,
    width: int = 300,
    height: int = 200,
    col_lines: list[int],
    row_lines: list[int],
    line_thickness: int = 3,
    water_cell: tuple[int, int] | None = None,
    water_intensity: tuple[int, int, int] = _BLUE,
) -> bytes:
    """
    Buduje syntetyczną mapę: tło + pełne-wymiarowo czerwone linie siatki + opcjonalny
    "wodny" prostokąt w jednej komórce (0-indeksowana (kolumna, wiersz) wśród komórek
    WEWNĄTRZ linii — nie mylić z 1-indeksowanym wynikiem detect_dam_sector).
    """
    arr = np.full((height, width, 3), _BG, dtype=np.uint8)

    for x in col_lines:
        arr[:, max(0, x - line_thickness // 2) : x + line_thickness // 2 + 1] = _RED
    for y in row_lines:
        arr[max(0, y - line_thickness // 2) : y + line_thickness // 2 + 1, :] = _RED

    if water_cell is not None:
        ci, ri = water_cell
        col_bounds = [0, *col_lines, width]
        row_bounds = [0, *row_lines, height]
        x0, x1 = col_bounds[ci] + 5, col_bounds[ci + 1] - 5
        y0, y1 = row_bounds[ri] + 5, row_bounds[ri + 1] - 5
        arr[y0:y1, x0:x1] = water_intensity

    buf = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


class TestDetectGrid:
    """detect_grid() — granice siatki z pełno-wymiarowych czerwonych linii."""

    def test_finds_correct_number_of_boundaries_for_3x2_grid(self):
        """2 linie pionowe + 1 pozioma (plus domyślne krawędzie) dają siatkę 3x2."""
        png = _make_grid_image(col_lines=[100, 200], row_lines=[100])
        grid = detect_grid(Image.open(BytesIO(png)))

        assert grid.n_cols == 3
        assert grid.n_rows == 2

    def test_ignores_small_non_gridline_red_blobs(self):
        """Mały czerwony kwadrat (np. etykieta) nie liczy się jako linia siatki — tylko pełno-wymiarowe pasma."""
        # Czerwony "szum" (np. etykieta) w rogu — pokrywa tylko fragment wymiaru,
        # nie powinien zostać uznany za linię siatki. Prawdziwa linia pozioma jest też
        # obecna (arr[95:105, :]), żeby ten test sprawdzał WYŁĄCZNIE filtrowanie szumu,
        # nie zachowanie przy braku linii w jednym wymiarze (patrz osobny test niżej).
        arr = np.full((200, 300, 3), _BG, dtype=np.uint8)
        arr[90:110, 90:110] = _RED  # mały czerwony kwadrat, nie linia
        arr[:, 148:152] = _RED  # prawdziwa linia siatki pionowa (pełna wysokość)
        arr[95:105, :] = _RED  # prawdziwa linia siatki pozioma (pełna szerokość)
        buf = BytesIO()
        Image.fromarray(arr, mode="RGB").save(buf, format="PNG")

        grid = detect_grid(Image.open(buf))

        assert grid.n_cols == 2  # tylko jedna prawdziwa linia pionowa = 2 kolumny
        assert grid.n_rows == 2  # jedna prawdziwa linia pozioma = 2 wiersze

    def test_raises_when_no_gridlines_found(self):
        """Obraz bez żadnej czerwonej linii w żadnym wymiarze zgłasza błąd zamiast zgadywać siatkę 1x1."""
        arr = np.full((200, 300, 3), _BG, dtype=np.uint8)
        buf = BytesIO()
        Image.fromarray(arr, mode="RGB").save(buf, format="PNG")

        with pytest.raises(ValueError, match="Nie wykryto żadnych czerwonych linii"):
            detect_grid(Image.open(buf))

    def test_raises_when_one_dimension_has_no_gridlines(self):
        """Linie tylko w JEDNYM wymiarze (np. same pionowe) też zgłaszają błąd — nie zgaduje '1 wiersz'."""
        arr = np.full((200, 300, 3), _BG, dtype=np.uint8)
        arr[:, 148:152] = _RED  # tylko linia pionowa, zero poziomych
        buf = BytesIO()
        Image.fromarray(arr, mode="RGB").save(buf, format="PNG")

        with pytest.raises(ValueError, match="Nie wykryto żadnych czerwonych linii"):
            detect_grid(Image.open(buf))


class TestDetectDamSector:
    """detect_dam_sector() — pełny przepływ PNG → sektor (1-indeksowany)."""

    def test_finds_water_cell_in_3x2_grid(self):
        """Komórka wewnętrzna (1,1) 0-indeksowana odpowiada wynikowi (2,2) 1-indeksowanemu."""
        # Komórki (0-indeksowane wewnętrznie): kolumny [0,1,2], wiersze [0,1].
        # Woda w komórce (col=1, row=1) -> oczekiwany wynik 1-indeksowany: col=2, row=2.
        png = _make_grid_image(col_lines=[100, 200], row_lines=[100], water_cell=(1, 1))

        result = detect_dam_sector(png)

        assert (result.col, result.row) == (2, 2)
        assert result.grid.n_cols == 3
        assert result.grid.n_rows == 2
        assert result.water_fraction > 0

    def test_finds_water_cell_in_top_left(self):
        """Woda w skrajnie pierwszej komórce daje wynik (1,1), nie off-by-one błąd."""
        png = _make_grid_image(col_lines=[100, 200], row_lines=[100], water_cell=(0, 0))

        result = detect_dam_sector(png)

        assert (result.col, result.row) == (1, 1)

    def test_raises_when_no_water_anywhere(self):
        """Brak jakiejkolwiek wody na mapie zgłasza DamSectorAmbiguousError zamiast zgadywać."""
        png = _make_grid_image(col_lines=[100, 200], row_lines=[100], water_cell=None)

        with pytest.raises(DamSectorAmbiguousError, match="Żaden sektor"):
            detect_dam_sector(png)

    def test_raises_when_water_levels_are_ambiguous(self):
        """Dwie komórki z niemal identyczną ilością wody są zbyt niejednoznaczne, żeby wybrać jedną automatycznie."""
        # Dwie komórki z BARDZO podobną (nie wyraźnie dominującą) ilością wody —
        # sygnał zbyt niejednoznaczny, żeby zgadywać automatycznie.
        arr = np.full((200, 300, 3), _BG, dtype=np.uint8)
        arr[:, 148:152] = _RED
        arr[95:105, :] = _RED
        # Prawie identyczne plamy wody w dwóch różnych komórkach.
        arr[10:95, 10:95] = _BLUE
        arr[10:93, 160:245] = _BLUE
        buf = BytesIO()
        Image.fromarray(arr, mode="RGB").save(buf, format="PNG")

        with pytest.raises(DamSectorAmbiguousError, match="nie jest wyraźnym outlierem"):
            detect_dam_sector(buf.getvalue())

    def test_to_dict_is_json_serializable(self):
        """to_dict() produkuje słownik, który json.dumps() przyjmuje bez błędu."""
        import json

        png = _make_grid_image(col_lines=[100, 200], row_lines=[100], water_cell=(1, 1))
        result = detect_dam_sector(png)

        serialized = json.dumps(result.to_dict())  # nie powinno rzucić
        assert '"col": 2' in serialized
        assert '"row": 2' in serialized
