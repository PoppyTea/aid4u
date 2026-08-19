"""
S03E04 — katalog przedmiotów i miast, czysta logika bez I/O sieciowego.

Model danych (`data/input/s03e04_negotiations/`):
- `items.csv`      — `name,code`, 2137 wierszy, kody i nazwy unikalne
- `cities.csv`     — `name,code`, 51 wierszy (UWAGA: plik nie ma znaku nowej linii
                     na końcu — `csv` radzi sobie, `wc -l` gubi ostatni wiersz)
- `connections.csv`— `itemCode,cityCode`, 5349 wierszy

Sercem modułu jest `CatalogIndex.search()` — dopasowanie zapytania w języku
naturalnym do pozycji katalogu. Agent Centrali pyta odmienionym polskim
("szukam turbiny wiatrowej"), a katalog trzyma wyłącznie mianownik
("Turbina wiatrowa"), więc dopasowanie po podciągu tu nie wystarcza. Stąd
punktacja po RDZENIACH tokenów: `turbiny` → `turbin`, `wiatrowej` → `wiatrow`.

Punktujemy pokrycie tokenów POZYCJI KATALOGU, nie zapytania — dzięki temu
dodatkowe słowa w zapytaniu ("szukam", "potrzebuję", "majacej") są nieszkodliwe
i nie trzeba utrzymywać listy stopwords.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

DATA_DIR = Path("data/input/s03e04_negotiations")

# Końcówki fleksyjne zdejmowane przy budowie rdzenia, od najdłuższych.
# Nie jest to pełny stemmer polski i nie musi być — ma tylko sprowadzić formę
# odmienioną do wspólnego prefiksu z mianownikiem.
_SUFFIXES = (
    "ami", "ach", "owi", "ymi", "imi", "ego", "emu", "ej", "ow",
    "em", "om", "ie", "ia", "ie", "y", "i", "a", "e", "u", "o",
)
_MIN_STEM = 4

# Poniżej tego progu dwa rdzenie uznajemy za różne słowa, nie literówkę.
_FUZZY_TOKEN_RATIO = 0.82

# Pozycja musi mieć pokryte co najmniej tyle swoich tokenów nazwy, żeby trafić
# na listę kandydatów.
_MIN_COVERAGE = 0.6

# Drugi przebieg, uruchamiany dopiero gdy pierwszy nie znalazł NICZEGO. Agent
# Centrali ma 10 kroków i przerywa pracę bez odpowiedzi, więc oznaczone
# przybliżenie jest dla niego warte więcej niż pustka — ale musi być oznaczone,
# żeby mógł je odrzucić zamiast wziąć za pewnik.
_FALLBACK_COVERAGE = 0.34


def normalize(text: str) -> str:
    """Sprowadza tekst do postaci porównywalnej: bez diakrytyków, małe litery, zbite spacje."""
    folded = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def tokenize(text: str) -> list[str]:
    """Dzieli znormalizowany tekst na tokeny alfanumeryczne (zachowuje '48v', '400w')."""
    return re.findall(r"[a-z0-9]+", normalize(text))


def stem(token: str) -> str:
    """
    Obcina końcówkę fleksyjną, o ile zostanie sensowny rdzeń.

    Tokeny liczbowo-jednostkowe ('48v', '10') zostawiamy nietknięte — ich końcowe
    litery niosą znaczenie (napięcie, moc), a nie odmianę.
    """
    if any(c.isdigit() for c in token):
        return token
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= _MIN_STEM:
            return token[: -len(suffix)]
    return token


def stems(text: str) -> list[str]:
    """Rdzenie wszystkich tokenów tekstu, z zachowaniem kolejności."""
    return [stem(t) for t in tokenize(text)]


def _tokens_match(item_stem: str, query_stems: set[str]) -> bool:
    """
    Czy rdzeń pozycji katalogu ma odpowiednik wśród rdzeni zapytania.

    Trzy poziomy tolerancji, od najtańszego: równość, wspólny prefiks (ratuje
    przypadki gdzie stemmer uciął o jedną literę za dużo lub za mało), fuzzy
    (ratuje literówki agenta, np. 'trubina').
    """
    if item_stem in query_stems:
        return True
    for q in query_stems:
        if len(item_stem) >= _MIN_STEM and len(q) >= _MIN_STEM:
            if item_stem.startswith(q) or q.startswith(item_stem):
                return True
            if SequenceMatcher(None, item_stem, q).ratio() >= _FUZZY_TOKEN_RATIO:
                return True
    return False


@dataclass(frozen=True)
class Item:
    """
    Pozycja katalogu wraz z policzonymi rdzeniami — liczone raz, przy ładowaniu.

    Rdzenie są rozdzielone celowo. `word_stems` to nazwa właściwa ('turbina
    wiatrowa'), `param_stems` to parametry techniczne ('400w', '48v'). Zapytanie
    agenta bywa ogólne ("szukam turbiny wiatrowej") i wtedy parametrów nie poda —
    gdyby liczyły się do pokrycia, taka pozycja wypadłaby poniżej progu mimo
    trafienia w sedno.
    """

    name: str
    code: str
    word_stems: tuple[str, ...]
    param_stems: tuple[str, ...]


@dataclass(frozen=True)
class Match:
    """Kandydat zwrócony przez `search()`, z punktacją użytą do rankingu."""

    item: Item
    coverage: float
    matched: int
    param_hits: int
    approximate: bool = False
    sellable: bool = True


class CatalogIndex:
    """
    Indeks katalogu trzymany w pamięci procesu.

    Budowany raz przy starcie serwera (2137 pozycji — cały zbiór swobodnie mieści
    się w RAM), potem tylko odczytywany.
    """

    def __init__(self, items: list[Item], cities_by_item: dict[str, list[str]]):
        self._items = items
        self._by_code = {i.code: i for i in items}
        self._cities_by_item = cities_by_item

    @classmethod
    def load(cls, data_dir: Path | None = None) -> "CatalogIndex":
        """Wczytuje trzy pliki CSV i buduje indeks. Rzuca `ValueError` gdy dane łamią założenia."""
        base = data_dir or DATA_DIR
        items_raw = _read_csv(base / "items.csv")
        cities_raw = _read_csv(base / "cities.csv")
        conns_raw = _read_csv(base / "connections.csv")

        codes = [r["code"] for r in items_raw]
        if len(set(codes)) != len(codes):
            dupes = {c for c in codes if codes.count(c) > 1}
            raise ValueError(f"items.csv: kody nie są unikalne: {sorted(dupes)[:5]}")

        city_name_by_code = {r["code"]: r["name"] for r in cities_raw}
        unknown = {r["cityCode"] for r in conns_raw} - set(city_name_by_code)
        if unknown:
            raise ValueError(f"connections.csv: kody miast spoza cities.csv: {sorted(unknown)[:5]}")

        cities_by_item: dict[str, list[str]] = {}
        for row in conns_raw:
            cities_by_item.setdefault(row["itemCode"], []).append(
                city_name_by_code[row["cityCode"]]
            )
        for city_list in cities_by_item.values():
            city_list.sort()

        items = [_build_item(r["name"], r["code"]) for r in items_raw]
        return cls(items, cities_by_item)

    @property
    def item_count(self) -> int:
        """Liczba pozycji katalogu — używane w logu startowym jako sanity check."""
        return len(self._items)

    def orphans(self) -> list[Item]:
        """
        Pozycje bez ani jednego miasta.

        Na żywych danych jest dokładnie jedna (`06OTEB`, 'Akumulator kwasowy 12V
        200Ah') — pozostałość po łatce, którą autorzy rozdzielili zduplikowany kod
        `06OTEA`, ale nie dopisali dla niej połączeń. Pusty wynik dla takiej
        pozycji jest POPRAWNY, nie jest błędem wyszukiwania.
        """
        return [i for i in self._items if not self._cities_by_item.get(i.code)]

    def search(self, query: str, *, limit: int = 5) -> list[Match]:
        """
        Znajduje pozycje katalogu pasujące do zapytania w języku naturalnym.

        Przeszukuje CAŁY katalog, nie tylko podzespoły turbiny — agent Centrali
        pyta także o pozycje spoza zadania głównego i zawężenie zakresu odcięłoby
        te ścieżki.
        """
        query_stems = set(stems(query))
        if not query_stems:
            return []

        found = self._score(query_stems, _MIN_COVERAGE, limit)
        if found:
            return found
        return [
            Match(
                m.item,
                m.coverage,
                m.matched,
                m.param_hits,
                approximate=True,
                sellable=m.sellable,
            )
            for m in self._score(query_stems, _FALLBACK_COVERAGE, limit)
        ]

    def _score(self, query_stems: set[str], floor: float, limit: int) -> list[Match]:
        """Jeden przebieg punktacji przy zadanym progu pokrycia nazwy."""
        matches: list[Match] = []
        for item in self._items:
            if not item.word_stems:
                continue
            hit = sum(1 for s in item.word_stems if _tokens_match(s, query_stems))
            coverage = hit / len(item.word_stems)
            if coverage < floor or hit == 0:
                continue
            params = sum(1 for s in item.param_stems if s in query_stems)
            matches.append(
                Match(
                    item=item,
                    coverage=coverage,
                    matched=hit,
                    param_hits=params,
                    sellable=bool(self._cities_by_item.get(item.code)),
                )
            )

        # Pełne pokrycie nazwy przed częściowym; przy remisie wygrywa wariant,
        # którego parametry techniczne agent wymienił wprost (48V vs 24V), a na
        # końcu krótsza nazwa — bez tego zapytanie ogólne dostawałoby wariant
        # obwieszony parametrami zamiast najprostszego pasującego.
        # `sellable` jest PIERWSZYM kryterium: pozycji, której nie oferuje żadne
        # miasto, agent nie może użyć w odpowiedzi — celem zadania są miasta, nie
        # sam kod. Na żywych danych dotyczy to sieroty 06OTEB, która bez tej
        # reguły wygrywała ranking dla zapytań o akumulator 12V i prowadziła
        # agenta w ślepy zaułek.
        matches.sort(
            key=lambda m: (
                not m.sellable,
                -m.coverage,
                -m.param_hits,
                -m.matched,
                len(m.item.name),
            )
        )
        return matches[:limit]

    def cities_for(self, code: str) -> list[str]:
        """Miasta oferujące pozycję o podanym kodzie. Pusta lista gdy kod nieznany lub sierocy."""
        return list(self._cities_by_item.get(code.strip().upper(), []))

    def cities_for_all(self, codes: list[str]) -> list[str]:
        """
        Miasta oferujące WSZYSTKIE podane pozycje jednocześnie.

        To jest właściwy cel zadania (przecięcie, nie suma), więc mimo że agent
        Centrali liczy przecięcie sam po swojej stronie, trzymamy je tutaj —
        pozwala zweryfikować odpowiedź lokalnie przed wystawieniem endpointu.
        """
        if not codes:
            return []
        sets = [set(self.cities_for(c)) for c in codes]
        return sorted(set.intersection(*sets)) if all(sets) else []

    def has_code(self, code: str) -> bool:
        """Czy kod istnieje w katalogu — odróżnia 'nie ma takiego kodu' od 'kod bez miast'."""
        return code.strip().upper() in self._by_code

    def item_by_code(self, code: str) -> Item | None:
        """Pozycja o podanym kodzie albo None."""
        return self._by_code.get(code.strip().upper())


def _build_item(name: str, code: str) -> Item:
    """Rozdziela rdzenie nazwy na słowne i parametryczne (te z cyfrą)."""
    all_stems = stems(name)
    return Item(
        name=name,
        code=code,
        word_stems=tuple(s for s in all_stems if not any(c.isdigit() for c in s)),
        param_stems=tuple(s for s in all_stems if any(c.isdigit() for c in s)),
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Wczytuje CSV jako listę słowników. Rzuca `FileNotFoundError` z czytelną wskazówką."""
    if not path.exists():
        raise FileNotFoundError(
            f"Brak {path} — pobierz dane: hub.get_public('dane/s03e04_csv/<plik>')"
        )
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


_CODE_RE = re.compile(r"\b([A-Z0-9]{6})\b")


def extract_code(text: str) -> str | None:
    """
    Wyciąga kod pozycji z tekstu przysłanego przez agenta.

    Agent bywa rozwlekły ("sprawdź proszę kod 7RSVK7"), więc nie zakładamy że
    `params` to sam kod. Kody mają stały kształt: 6 znaków [A-Z0-9].
    """
    found = _CODE_RE.findall(text.strip().upper())
    return found[0] if found else None
