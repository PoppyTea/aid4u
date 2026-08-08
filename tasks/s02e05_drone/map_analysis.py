"""
Deterministyczna analiza mapy terenu s02e05 — LOKALIZACJA SEKTORA TAMY BEZ LLM/VISION.

`LLMClient` w tym repo nie ma dziś żadnego wsparcia dla obrazów (patrz `core/AGENTS.md`
i `strategy/s03-readiness.md`) — dokładnie dlatego s02e02 zostało zaliczone ręcznie przez
przeglądarkę. Zamiast dokładać vision pod jedno zadanie, ten moduł wykorzystuje fakt, że
mapa jest wygenerowana programistycznie z dwoma jawnymi, policzalnymi sygnałami:

1. Siatka jest rysowana GRUBYMI CZERWONYMI LINIAMI, pełnej wysokości/szerokości —
   odróżnialnymi od szumu (np. czerwonych etykiet/ikon) progiem pokrycia, nie tylko
   obecnością koloru.
2. Sektor z tamą ma CELOWO PODBITĄ intensywność koloru wody względem reszty mapy
   (potwierdzone w treści zadania: "Przy tamie celowo podbito intensywność koloru wody,
   żeby ułatwić jej lokalizację") — czyli to wyraźny outlier, nie subtelna różnica.

Zweryfikowane na żywej mapie (2026-08-08): siatka 3 kolumny x 4 wiersze, dam w sektorze
(2, 4) z frakcją "wodnych" pikseli 6.1% wobec 0.0% w pozostałych 11 sektorach — czysty,
jednoznaczny sygnał, zero niepewności wymagającej modelu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO

import numpy as np
from PIL import Image

# Próg "czerwoności" (R - średnia(G,B)) kwalifikujący piksel jako część linii siatki.
_RED_THRESHOLD = 100
# Linia siatki musi pokrywać co najmniej tyle wysokości/szerokości obrazu, żeby odróżnić
# ją od szumu (etykiety, ikony, elementy graficzne) — w danych referencyjnych prawdziwe
# linie siatki pokrywają 100% wymiaru, szum <10%.
_GRIDLINE_COVERAGE = 0.85
# Próg "niebieskości" (B - średnia(R,G)) kwalifikujący piksel jako wodę.
_WATER_THRESHOLD = 30
# Sektor-kandydat na tamę musi mieć frakcję wodnych pikseli co najmniej tyle razy większą
# niż drugi najwyższy wynik — inaczej sygnał jest zbyt niejednoznaczny, żeby ufać mu bez
# nadzoru (patrz DamSectorAmbiguousError).
_MIN_OUTLIER_RATIO = 3.0


class DamSectorAmbiguousError(Exception):
    """Sygnał wody nie jest jednoznacznym outlierem — nie zgaduj, zgłoś to jawnie."""


@dataclass
class GridBoundaries:
    """Granice siatki w pikselach — punkty graniczne komórek, nie same linie."""

    col_boundaries: list[int]
    row_boundaries: list[int]

    @property
    def n_cols(self) -> int:
        """Liczba kolumn siatki (o jeden mniej niż liczba granic)."""
        return len(self.col_boundaries) - 1

    @property
    def n_rows(self) -> int:
        """Liczba wierszy siatki (o jeden mniej niż liczba granic)."""
        return len(self.row_boundaries) - 1


@dataclass
class DamSectorResult:
    """Wynik detekcji sektora tamy — współrzędne 1-indeksowane + diagnostyka do audytu."""

    col: int
    row: int
    grid: GridBoundaries
    water_fraction: float
    all_sector_scores: dict[tuple[int, int], float] = field(repr=False)

    def to_dict(self) -> dict:
        """Serializacja do JSON — zapisywana jako `data/output/s02e05_drone/dam_sector.json`."""
        return {
            "col": self.col,
            "row": self.row,
            "grid_cols": self.grid.n_cols,
            "grid_rows": self.grid.n_rows,
            "water_fraction": round(self.water_fraction, 4),
            "method": "deterministic_red_gridline_and_water_intensity",
            "all_sector_scores": {
                f"{c},{r}": round(score, 4) for (c, r), score in self.all_sector_scores.items()
            },
        }


def _band_midpoints(coverage: np.ndarray, threshold: float) -> list[int]:
    """
    Grupuje sąsiadujące indeksy o pokryciu > threshold w "pasma" (linia siatki ma kilka
    pikseli grubości) i zwraca środek każdego pasma jako pojedynczą granicę.
    """
    above = np.where(coverage > threshold)[0]
    if len(above) == 0:
        return []

    bands: list[list[int]] = [[int(above[0])]]
    for idx in above[1:]:
        idx = int(idx)
        if idx - bands[-1][-1] <= 1:
            bands[-1].append(idx)
        else:
            bands.append([idx])

    return [(band[0] + band[-1]) // 2 for band in bands]


def _with_implicit_edges(boundaries: list[int], edge_max: int, *, min_gap: int = 5) -> list[int]:
    """
    Dokłada domyślne granice na krawędziach obrazu (0 i `edge_max`), jeśli detekcja
    czerwonych linii ich nie objęła — np. mapa rysuje tylko WEWNĘTRZNE linie podziału,
    bez zamkniętej ramki wokół całości. `min_gap` zapobiega duplikatom, gdy ramka i tak
    jest czerwona i już wykryta blisko krawędzi (tak jak w referencyjnej mapie s02e05).
    """
    result = list(boundaries)
    if not result or result[0] > min_gap:
        result.insert(0, 0)
    if not result or result[-1] < edge_max - min_gap:
        result.append(edge_max)
    return result


def detect_grid(image: Image.Image) -> GridBoundaries:
    """
    Wykrywa granice siatki po pełnej-wysokości/pełnej-szerokości czerwonych liniach,
    plus domyślnie krawędzie obrazu (patrz `_with_implicit_edges`) — działa zarówno gdy
    mapa ma rysowaną ramkę (jak referencyjna mapa s02e05), jak i gdy ma tylko wewnętrzne
    linie podziału. Rzuca ValueError, jeśli mimo to znaleziono mniej niż 2 granice w
    którymkolwiek wymiarze (siatka wymaga co najmniej jednej komórki) — sygnał że próg
    detekcji trzeba dostroić do konkretnego obrazu, nie że coś innego jest nie tak.
    """
    arr = np.asarray(image.convert("RGB")).astype(int)
    h, w, _ = arr.shape
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    redness = r - (g + b) // 2
    mask = redness > _RED_THRESHOLD

    row_coverage = mask.mean(axis=1)
    col_coverage = mask.mean(axis=0)

    raw_row_boundaries = _band_midpoints(row_coverage, _GRIDLINE_COVERAGE)
    raw_col_boundaries = _band_midpoints(col_coverage, _GRIDLINE_COVERAGE)

    if not raw_row_boundaries and not raw_col_boundaries:
        # Zero czerwonych linii w OBU wymiarach — nie zgaduj "1x1 siatka", to prawie na
        # pewno źle dobrany próg albo obraz bez siatki w ogóle.
        raise ValueError(
            "Nie wykryto żadnych czerwonych linii siatki (ani poziomych, ani pionowych) — "
            "dostrój _RED_THRESHOLD/_GRIDLINE_COVERAGE do tego konkretnego obrazu, albo "
            "obraz faktycznie nie ma siatki."
        )

    row_boundaries = _with_implicit_edges(raw_row_boundaries, h - 1)
    col_boundaries = _with_implicit_edges(raw_col_boundaries, w - 1)

    return GridBoundaries(col_boundaries=col_boundaries, row_boundaries=row_boundaries)


def detect_dam_sector(png_bytes: bytes) -> DamSectorResult:
    """
    Główne wejście modułu: PNG mapy → sektor z tamą (1-indeksowany, kolumna, wiersz).

    Deterministyczne, bez sieci i bez LLM. Rzuca `DamSectorAmbiguousError`, jeśli
    najwyższy wynik "wodności" nie jest wyraźnym outlierem (patrz `_MIN_OUTLIER_RATIO`)
    — lepiej zgłosić niepewność niż po cichu zwrócić zły sektor.
    """
    image = Image.open(BytesIO(png_bytes)).convert("RGB")
    grid = detect_grid(image)

    arr = np.asarray(image).astype(int)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    blueness = b - (r + g) // 2
    water_mask = blueness > _WATER_THRESHOLD

    scores: dict[tuple[int, int], float] = {}
    for ci in range(grid.n_cols):
        x0, x1 = grid.col_boundaries[ci], grid.col_boundaries[ci + 1]
        for ri in range(grid.n_rows):
            y0, y1 = grid.row_boundaries[ri], grid.row_boundaries[ri + 1]
            cell_mask = water_mask[y0:y1, x0:x1]
            scores[(ci + 1, ri + 1)] = float(cell_mask.mean())

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (best_col, best_row), best_score = ranked[0]
    runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0

    if best_score <= 0.0:
        raise DamSectorAmbiguousError(
            "Żaden sektor nie ma podwyższonej intensywności wody — próg _WATER_THRESHOLD "
            "prawdopodobnie wymaga dostrojenia do tego obrazu."
        )
    if runner_up_score > 0.0 and best_score < runner_up_score * _MIN_OUTLIER_RATIO:
        raise DamSectorAmbiguousError(
            f"Najwyższy wynik wodności ({best_score:.4f} w sektorze {best_col},{best_row}) "
            f"nie jest wyraźnym outlierem względem drugiego miejsca ({runner_up_score:.4f}) "
            f"— sygnał zbyt niejednoznaczny, żeby ufać mu automatycznie."
        )

    return DamSectorResult(
        col=best_col,
        row=best_row,
        grid=grid,
        water_fraction=best_score,
        all_sector_scores=scores,
    )
