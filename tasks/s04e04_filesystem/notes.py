"""
S04E04 — czytanie notatek Natana: miasta, ludzie, towary.

**Zero LLM, wbrew intelowi społeczności.** Komentarze kursu są zgodne, że to zadanie
lingwistyczne i że lokalne modele się na nim wykładały (*„o ile radziły sobie z czystą
gramatyką to gubiły się w znaczeniu tych notatek"*), a przeszło dopiero `gemini-3-flash`
za $0.26. Deterministyczna droga istnieje, bo w paczce jest plik, którego modele nie
wykorzystywały jako słownika: **`transakcje.txt` podaje wszystkie miasta i wszystkie
towary w mianowniku**, po jednym na linię, w sztywnym formacie `Miasto -> towar -> Miasto`.

To zamienia problem „rozpoznaj polską odmianę" w problem „dopasuj formę odmienioną do
znanego, skończonego słownika" — a to jest dopasowanie rdzenia, nie rozumienie języka.

## Trzy miejsca, w których to potrafi po cichu zawieść

1. **Kolizja rdzeni.** `maka` jest prefiksem `makaron`, więc dopasowanie „pierwszy
   pasujący" wpisałoby mąkę wszędzie tam, gdzie jest makaron. Stąd dopasowanie
   **od najdłuższego rdzenia**.
2. **Rozbite nazwiska.** Dwie osoby są nazwane po nazwisku w jednym zdaniu i po imieniu
   w innym („Kisiel ma do mnie dzwonic" … „Rafal oddzwonil wieczorem"). Pełne imię
   powstaje ze złączenia obu wzmianek po wspólnym mieście.
3. **Miasto w odmianie.** „z Opalina", „w Domatowie", „z Darzlubiem" — nazwa nigdy nie
   pada w mianowniku poza `transakcje.txt`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field

# Towar spoza `transakcje.txt`: woda nie jest przedmiotem handlu między miastami,
# ale pojawia się w zapotrzebowaniu każdego z nich. Bez tego wpisu `/miasta` gubiłoby
# największą pozycję każdego zamówienia.
EXTRA_GOODS = ("woda",)

# Minimalna długość rdzenia przy dopasowaniu formy odmienionej. Trzy znaki, nie cztery:
# `woda` ma tylko cztery litery, a musi złapać `wody` i `wode`, więc rdzeń MUSI być
# krótszy od formy podstawowej. Przy czterech znakach `woda` zostawała `woda`, nie
# pasowała do niczego i największa pozycja każdego zamówienia znikała po cichu.
MIN_STEM = 3

_TRANSACTION_RE = re.compile(r"^\s*(.+?)\s*->\s*(.+?)\s*->\s*(.+?)\s*$")
_FULL_NAME_RE = re.compile(r"\b([A-ZŁŚŻŹĆÓĘĄŃ][a-ząćęłńóśźż]+)\s+([A-ZŁŚŻŹĆÓĘĄŃ][a-ząćęłńóśźż]+)\b")
_CAPITALISED_RE = re.compile(r"\b([A-ZŁŚŻŹĆÓĘĄŃ][a-ząćęłńóśźż]{2,})\b")

# Polskie wyrazy, które w tych notatkach otwierają zdanie i przez to wyglądają jak imię.
# Filtr po POZYCJI nie działa i to jest zmierzone, nie założone: „Kisiel" i „Rafal" też
# stoją na początku zdania („…dla Brudzewa. Kisiel ma do mnie dzwonic"), więc odsianie
# wszystkiego, co otwiera zdanie, wycięłoby prawdziwe nazwisko razem z adverbium.
# Lista jest krótka i zamknięta, bo korpus ma 2 kB i jest stały; gdyby kurs go przelosował,
# broni nas walidacja w `read_notes()`, która przerywa zamiast zgadywać.
_NOT_A_NAME = frozenset(
    {
        "najpierw", "teraz", "potem", "reszta", "uwaga", "notka", "oba", "obie",
        "przynajmniej", "krotka", "kto", "ktos", "jak", "chce", "moze", "tylko",
    }
)


# `ł` i `Ł` to jedyne polskie litery BEZ dekompozycji kanonicznej — `NFD` zostawia je
# nietknięte, więc samo odsiewanie znaków łączących ich nie usunie. Bez tej podmiany
# `łopata`, `młotek` i `wołowina` trafiłyby do nazw plików z polskim znakiem, czego
# treść zadania zabrania wprost.
_UNDECOMPOSABLE = str.maketrans({"ł": "l", "Ł": "L"})


def fold(text: str) -> str:
    """
    Sprowadza tekst do ASCII bez znaków diakrytycznych, zachowując wielkość liter.

    Potrzebne dwukrotnie i z dwóch różnych powodów: do dopasowywania form odmienionych
    (notatki są pisane bez ogonków, `transakcje.txt` z ogonkami) oraz do nazw plików
    i treści JSON, gdzie treść zadania zabrania polskich znaków wprost.
    """
    normalised = unicodedata.normalize("NFD", text.translate(_UNDECOMPOSABLE))
    return "".join(c for c in normalised if not unicodedata.combining(c))


def _stem(word: str) -> str:
    """Rdzeń do dopasowania odmiany — obcięta końcówka fleksyjna, minimum `MIN_STEM` znaków."""
    folded = fold(word).casefold()
    return folded[: max(MIN_STEM, len(folded) - 2)]


def match_known(word: str, vocabulary: list[str]) -> str | None:
    """
    Dopasowuje odmienione słowo do formy podstawowej ze słownika.

    Args:
        word: Forma z tekstu, np. `mlotkow`, `Opalina`.
        vocabulary: Formy podstawowe, np. `["mlotek", "makaron", "maka"]`.

    Returns:
        Forma podstawowa albo `None`.

    Kolejność sprawdzania idzie **od najdłuższego rdzenia**, bo krótsze bywają prefiksami
    dłuższych: `maka` jest prefiksem `makaron`, więc kolejność „pierwszy pasujący"
    wstawiałaby mąkę w miejsce makaronu.
    """
    target = fold(word).casefold()
    for base in sorted(vocabulary, key=lambda b: -len(b)):
        stem = _stem(base)
        if len(stem) >= MIN_STEM and target.startswith(stem):
            return base
    return None


@dataclass
class Ledger:
    """Wszystko, co da się wyczytać z notatek Natana."""

    cities: list[str] = field(default_factory=list)
    """Miasta w mianowniku, w kolejności pierwszego wystąpienia."""
    goods: list[str] = field(default_factory=list)
    """Towary w mianowniku liczby pojedynczej."""
    offers: dict[str, list[str]] = field(default_factory=dict)
    """Towar → miasta, które go sprzedają."""
    demand: dict[str, dict[str, int]] = field(default_factory=dict)
    """Miasto → {towar: ilość}."""
    managers: dict[str, str] = field(default_factory=dict)
    """Miasto → imię i nazwisko osoby odpowiedzialnej za handel."""


def read_transactions(text: str) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """
    Czyta `transakcje.txt` — jedyne źródło form podstawowych w całej paczce.

    Format jest sztywny (`Miasto -> towar -> Miasto`), więc nie ma tu żadnego zgadywania.
    Zwracane słowniki służą potem do rozpoznawania odmienionych form w pozostałych plikach.

    Returns:
        `(miasta, towary, towar → miasta sprzedające)`. Strona LEWA strzałki to sprzedawca,
        więc to ona trafia do oferty; prawa to odbiorca.
    """
    cities: list[str] = []
    goods: list[str] = []
    offers: dict[str, list[str]] = {}

    for line in text.splitlines():
        match = _TRANSACTION_RE.match(line)
        if not match:
            continue
        seller, good, buyer = (part.strip() for part in match.groups())

        for city in (seller, buyer):
            if city not in cities:
                cities.append(city)
        if good not in goods:
            goods.append(good)
        sellers = offers.setdefault(good, [])
        if seller not in sellers:
            sellers.append(seller)

    return cities, goods, offers


def read_demand(text: str, cities: list[str], goods: list[str]) -> dict[str, dict[str, int]]:
    """
    Czyta `ogłoszenia.txt` — zapotrzebowanie miast, akapit po akapicie.

    Liczba i towar stoją w dowolnej kolejności („45 chlebow", ale też „ziemniaki 100 kg",
    „kapusta 70"), więc dla każdej liczby sprawdzamy oba sąsiedztwa i bierzemy bliższy
    rozpoznany towar. Jednostki („butelek", „workow", „kg", „porcji") nie są towarami,
    więc nie trafiają do słownika i po prostu nie pasują.
    """
    demand: dict[str, dict[str, int]] = {}

    for block in (b for b in text.split("\n\n") if b.strip()):
        words = re.findall(r"[\w']+", block, flags=re.UNICODE)
        city = next((c for w in words if (c := match_known(w, cities))), None)
        if city is None:
            continue

        found: dict[str, int] = {}
        for index, word in enumerate(words):
            if not word.isdigit():
                continue
            # Kolejność sąsiadów jest wynikiem pomiaru, nie gustu. Towar stoi raz przed
            # liczbą („ziemniaki 100 kg"), raz po niej („45 chlebow"), a między liczbą
            # a towarem bywa jednostka („120 butelek wody"). Stąd najpierw sąsiad
            # BEZPOŚREDNI z obu stron, dopiero potem dalsze.
            #
            # Warunek „towar jeszcze nieprzypisany" jest drugą połową tego samego
            # problemu: w „45 chlebow, 120 butelek wody" liczba 120 ma po lewej `chlebow`,
            # który należy do poprzedniej pozycji. Bez pomijania zajętych towarów woda
            # przepadała, a przy „ziemniaki 100 kg, kapusta 70" cały akapit rozjeżdżał
            # się o jedną pozycję.
            for offset in (-1, 1, 2, -2, 3, -3):
                neighbour = index + offset
                if not 0 <= neighbour < len(words):
                    continue
                good = match_known(words[neighbour], goods)
                if good is not None and good not in found:
                    found[good] = int(word)
                    break

        if found:
            demand[city] = found

    return demand


def read_managers(text: str, cities: list[str], goods: list[str]) -> dict[str, str]:
    """
    Czyta `rozmowy.txt` — kto odpowiada za handel w którym mieście.

    Najtrudniejszy plik w paczce i miejsce, w którym wykładały się modele. Dwie osoby są
    przedstawione na raty: nazwisko w jednym akapicie, imię w innym, oba razem z tym samym
    miastem. Dlatego przebieg jest dwufazowy — najpierw pełne imiona i nazwiska, potem
    sklejanie pojedynczych wzmianek dla miast, które wciąż nie mają opiekuna.
    """
    # Wyłącznie wypunktowania. Nagłówek pliku („Notatki przygotowane przez Natana Ramsa
    # z Domatowa") wygląda jak zwykły akapit i podaje nazwisko w DOPEŁNIACZU — wpuszczony
    # do przebiegu ustawiał Domatowu opiekuna „Natana Ramsa" zamiast „Natan Rams".
    blocks = [b.strip() for b in re.split(r"^\s*-\s+", text, flags=re.MULTILINE)[1:] if b.strip()]
    managers: dict[str, str] = {}
    loose: dict[str, list[str]] = {}

    for block in blocks:
        words = re.findall(r"[\w']+", block, flags=re.UNICODE)
        mentioned = [c for w in words if (c := match_known(w, cities))]
        if not mentioned:
            continue
        city = mentioned[0]

        names = [f"{a} {b}" for a, b in _FULL_NAME_RE.findall(block)]
        if names:
            managers.setdefault(city, names[0])
            continue

        # Wzmianki pojedyncze: imię ALBO nazwisko. Odsiewamy nazwy miast, nazwy towarów
        # („Woda dla Brudzewa…" otwiera zdanie wielką literą) i wyrazy z `_NOT_A_NAME`.
        for token in _CAPITALISED_RE.findall(block):
            folded = fold(token).casefold()
            if folded in _NOT_A_NAME:
                continue
            if match_known(token, cities) is not None or match_known(token, goods) is not None:
                continue
            if token not in loose.setdefault(city, []):
                loose[city].append(token)

    for city, tokens in loose.items():
        if city in managers or len(tokens) < 2:
            continue
        # Kolejność w tekście to nazwisko-potem-imię („Kisiel"… „Rafal"), a chcemy
        # „Imię Nazwisko" — stąd odwrócenie pary.
        surname, given = tokens[0], tokens[1]
        managers[city] = f"{given} {surname}"

    return managers


def read_notes(files: dict[str, str]) -> Ledger:
    """
    Składa komplet wiedzy z rozpakowanych notatek.

    Args:
        files: Mapa `nazwa pliku → treść`, z paczki `natan_notes.zip`.

    Returns:
        Wypełniony `Ledger`.

    Raises:
        ValueError: Gdy brakuje któregoś z trzech plików źródłowych.
    """
    def pick(fragment: str) -> str:
        for name, content in files.items():
            if fragment in fold(name).casefold():
                return content
        raise ValueError(f"W paczce brakuje pliku zawierającego '{fragment}': {sorted(files)}")

    cities, goods, offers = read_transactions(pick("transakcje"))
    vocabulary = goods + [g for g in EXTRA_GOODS if g not in goods]

    ledger = Ledger(
        cities=cities,
        goods=goods,
        offers=offers,
        demand=read_demand(pick("ogloszenia"), cities, vocabulary),
        managers=read_managers(pick("rozmowy"), cities, vocabulary),
    )
    _reject_incomplete(ledger)
    return ledger


def _reject_incomplete(ledger: Ledger) -> None:
    """
    Przerywa, gdy odczyt notatek jest niepełny albo podejrzany.

    Rozpoznawanie polskiej odmiany zawodzi CICHO: miasto bez zapotrzebowania albo osoba
    złożona z przypadkowego wyrazu wyglądają jak poprawny wynik i lądują na hubie jako
    zła struktura. Tu jest jedyne miejsce, w którym da się to zatrzymać, więc warunki
    są celowo ostre.

    Raises:
        ValueError: Przy pierwszej niezgodności, z nazwą miasta w komunikacie.
    """
    for city in ledger.cities:
        if not ledger.demand.get(city):
            raise ValueError(f"Brak zapotrzebowania dla miasta {city!r} — parser zgubił akapit.")
        manager = ledger.managers.get(city)
        if not manager:
            raise ValueError(f"Brak osoby odpowiedzialnej za {city!r}.")
        if len(manager.split()) != 2:
            raise ValueError(
                f"Osoba dla {city!r} to {manager!r} — oczekiwano imienia i nazwiska. "
                "Najpewniej wyraz otwierający zdanie został wzięty za imię."
            )


def file_name(text: str) -> str:
    """
    Zamienia nazwę własną na dopuszczalną nazwę pliku.

    Trzy reguły, z czego **dwie niepisane** — nie ma ich ani w treści zadania, ani
    w `help`, wyszły z sondy (2026-08-25):

    - bez polskich znaków (to akurat treść zadania mówi wprost),
    - **wyłącznie małe litery** — `/miasta/Brudzewo` odbija się z `code -940`
      („Invalid file path."), a `/miasta/brudzewo` przechodzi,
    - **bez kropek** — `code -935` („File extensions are not allowed. Use names
      without dots."), więc żadnych `.md`.

    Wielkość liter zostaje natomiast w TREŚCI plików: „Natan Rams" ma być nazwiskiem,
    nie identyfikatorem.
    """
    return fold(text).casefold().replace(" ", "_").replace(".", "")


def city_path(city: str) -> str:
    """Ścieżka pliku miasta — używana też jako cel linków markdown z `/osoby` i `/towary`."""
    return f"/miasta/{file_name(city)}"


def build_operations(ledger: Ledger) -> list[dict[str, str]]:
    """
    Zamienia wiedzę z notatek na sekwencję operacji `batch_mode`.

    Kolejność jest **wymuszona przez API**, nie kosmetyczna: `help` mówi wprost
    „markdown links must point to existing files", więc katalogi i pliki miast muszą
    powstać zanim ktokolwiek do nich linkuje. Stąd `/miasta` przed `/osoby` i `/towary`.
    """
    operations: list[dict[str, str]] = [
        {"action": "createDirectory", "path": path} for path in ("/miasta", "/osoby", "/towary")
    ]

    for city in sorted(ledger.demand):
        content = json.dumps(
            {fold(good): amount for good, amount in sorted(ledger.demand[city].items())},
            ensure_ascii=True,
        )
        operations.append({"action": "createFile", "path": city_path(city), "content": content})

    for city in sorted(ledger.managers):
        person = ledger.managers[city]
        operations.append(
            {
                "action": "createFile",
                "path": f"/osoby/{file_name(person)}",
                "content": f"{person} - [{fold(city)}]({city_path(city)})",
            }
        )

    for good in sorted(ledger.offers):
        # Każdy link w osobnej linii — walidator zgłasza „Each link…" przy sklejeniu
        # ich w jedno zdanie (raport ze społeczności, HTTP 400 / code -789).
        links = "\n".join(
            f"- [{fold(city)}]({city_path(city)})" for city in sorted(ledger.offers[good])
        )
        operations.append(
            {"action": "createFile", "path": f"/towary/{file_name(good)}", "content": links}
        )

    return operations
