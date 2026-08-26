"""
S05E04 — nawigacja rakiety: wskazówki żeglarskie, wybór ruchu, rozbrajanie radaru.

Wszystko tutaj jest **czyste** (zero I/O), bo to są trzy miejsca, w których to zadanie
się przegrywa: źle zrozumiana wskazówka, ruch w skałę we WŁASNEJ kolumnie i zły hash
rozbrajający. Każde z nich kończy się rozbiciem albo zestrzeleniem i restartem od kolumny 1.

## Układ współrzędnych

Siatka 3 wiersze × 12 kolumn, start w kolumnie 1, wiersz 2. Zmierzone na żywo:
**`left` = port = wiersz o jeden MNIEJ** (w górę), `right` = starboard = wiersz o jeden
więcej. Każda z trzech komend przesuwa o kolumnę do przodu, także `left`/`right`.

## Reguła, na której wykłada się większość uczestników

Rakieta rusza się **najpierw w bieżącej kolumnie** (góra/dół), a dopiero potem do przodu.
Skała w kolumnie, w której właśnie stoisz, blokuje więc docelowy WIERSZ, mimo że jest
„obok", nie „przed" — sama wskazówka radiowa nie wystarcza. Odpowiedź `/verify` po każdym
ruchu podaje `currentColumn.freeRows`, więc drugie źródło jest za darmo; trzeba je tylko
uwzględnić.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from difflib import SequenceMatcher

ROWS = 3
COLUMNS = 12
START_ROW = 2

# Przesunięcie wiersza dla każdej komendy. `go` trzyma wiersz, obie pozostałe też
# przesuwają o kolumnę do przodu — to nie jest ruch „w bok zamiast do przodu".
MOVE_OFFSETS = {"left": -1, "go": 0, "right": 1}

_DIRECTION_WORDS = {
    "left": ("port", "left", "larboard"),
    "go": ("ahead", "straight", "nose", "bow", "front", "center", "centre", "forward",
           "heading", "middle", "facing", "pointing"),
    "right": ("starboard", "right"),
}

# Zwroty opisujące OBA boki naraz („both sides", „either wing", „your flanks").
# Sprawdzane dopiero wtedy, gdy w członie nie ma jawnego lewo/prawo — inaczej
# „the right-hand **side**" wskazywałoby obie strony zamiast jednej.
_BOTH_SIDES_WORDS = ("side", "flank", "wing", "edges")

# Zwroty czasowe, w których „right" znaczy „teraz", nie „na prawo". Bez ich usunięcia
# zdanie „Ahead is the only place you should not trust right now" wskazywało DWA
# kierunki naraz i wskazówka stawała się nieczytelna. Zmierzone, nie przewidziane.
_TIME_PHRASES = (" right now", " right away", " all right")

# Słowa mówiące, że dany kierunek jest ZAJĘTY przez skałę. Poza rzeczownikami także
# czasowniki umiejscowienia: „It is **waiting** in the exact path of the bow" nie
# zawiera ani słowa „rock", ani żadnego synonimu zagrożenia w tym samym zdaniu.
_BLOCKED_WORDS = (
    "rock", "stone", "obstruction", "obstacle", "hazard", "trouble", "blocked",
    "impact", "problem", "occupied", "danger", "bad choice", "risk", "alarming",
    "waiting", "lurking", "sitting", "sits", "occupies", "gathered",
    "evasive", "issue", "avoid", "collision", "threat", "boulder", "debris",
    "warning", "caution", "unsafe", "trap", "crash", "wall", "fear", "watch",
)

# Słowa mówiące, że dany kierunek jest WOLNY.
_FREE_WORDS = (
    "clean", "clear", "open", "empty", "room", "safe", "free", "unobstructed",
    "remain", "trust", "passable", "viable", "usable", "available", "quiet",
)

# Przeczenia. Odwracają sens członu, zamiast tworzyć własną kategorię — i to jest
# konieczne, bo obie strony występują w obu wariantach:
#
#   „The hazard is **not** trailing your wings"  → zagrożenie zaprzeczone  = boki wolne
#   „you have room … but **not** in the direction the craft is facing" → wolne
#                                                zaprzeczone = przód zajęty
#
# Dzięki temu „should **not** trust" wychodzi z samego „trust" na liście wolnych,
# a „shows **nothing** alarming" z samego „alarming" na liście zajętych — bez wpisywania
# całych fraz jako osobnych wyjątków. Warunek jest jeden: każde słowo musi siedzieć
# w kategorii zgodnej ze swoim ZNACZENIEM, nie z wymową całego zdania. Wpisanie
# „not trust" do zajętych obok „trust" w wolnych odwracało sens dwa razy i wskazówka
# stawała się nieczytelna.
_NEGATIONS = ("not", "n't", "nothing", "neither", "never", "no ")


# Cyfry, którymi zagłuszanie podmienia litery w nazwach pól. Podmiany typu `d`↔`b`
# czy `q`↔`p` celowo NIE są tu wypisane — od nich jest dopasowanie rozmyte, żeby zmiana
# sposobu psucia nie wymagała dopisywania kolejnej pary do tablicy.
_LOOKALIKE = str.maketrans({"0": "o", "1": "i", "3": "e", "5": "s", "4": "a", "7": "t"})

# Para `klucz: wartość` w tekście, który tylko udaje JSON: cudzysłów bywa backtickiem
# albo apostrofem, przecinki bywają zgubione.
_PAIR_RE = re.compile(r"([A-Za-z0-9_]{4,})\s*[\"\'`]?\s*:\s*[\"\'`]?\s*([A-Za-z0-9_-]+)")

# Próg podobieństwa nazwy pola do wzorca. 0.7 przepuszcza `frepuency`→`frequency` (0.89)
# i `betectioncobe`→`detectioncode` (0.85), a odrzuca `data` i `weapontype`.
_KEY_SIMILARITY = 0.7


class HintUnreadable(RuntimeError):
    """Wskazówka nie pozwala jednoznacznie wskazać skały — trzeba poprosić o kolejną."""


def _sentences(hint: str) -> list[list[str]]:
    """
    Dzieli wskazówkę na zdania, a każde zdanie na człony.

    Dwa poziomy, bo żaden sam nie wystarcza. Za grubo (całe zdania) psuje się na
    „Port is open, starboard is open, and the center lane is the bad choice" — jedno
    zdanie opisuje naraz dwa wolne kierunki i jeden zajęty. Za drobno (same człony)
    psuje się na „You have room ahead and also on the right-hand side" — drugi człon
    nie ma własnego orzeczenia i sens musi odziedziczyć po pierwszym.
    """
    text = hint.casefold()
    for phrase in _TIME_PHRASES:
        text = text.replace(phrase, " ")
    return [
        [c for c in re.split(r"[;,]| and | but | while ", sentence) if c.strip()]
        for sentence in re.split(r"[.!?]", text)
        if sentence.strip()
    ]


def _read_sense(clause: str, carried: str | None) -> tuple[str | None, str | None]:
    """
    Ocenia, czy człon mówi o wolnej drodze, czy o przeszkodzie.

    Args:
        clause: Fragment wskazówki, już małymi literami.
        carried: Sens poprzedniego członu w TYM zdaniu.

    Returns:
        Para `(sens po uwzględnieniu przeczenia, sens do przekazania dalej)`.
        Przekazywany dalej jest sens PRZED odwróceniem — „you have room … but not
        in the direction facing" dziedziczy „wolne", a przeczenie działa lokalnie.
    """
    if any(word in clause for word in _BLOCKED_WORDS):
        sense = "blocked"
    elif any(word in clause for word in _FREE_WORDS):
        sense = "free"
    else:
        # Człon bez własnego orzeczenia dziedziczy sens po poprzednim w tym zdaniu.
        sense = carried

    if sense is None:
        return None, carried
    if any(negation in clause for negation in _NEGATIONS):
        return ("free" if sense == "blocked" else "blocked"), sense
    return sense, sense


def _read_directions(clause: str) -> set[str]:
    """
    Wyłuskuje kierunki, o których mówi człon.

    Zwroty o obu bokach naraz („both sides") sprawdzamy dopiero wtedy, gdy nie ma
    jawnego lewo/prawo — inaczej „the right-hand **side**" wskazywałoby obie strony.
    """
    directions = {
        name for name, words in _DIRECTION_WORDS.items() if any(w in clause for w in words)
    }
    if not directions and any(word in clause for word in _BOTH_SIDES_WORDS):
        return {"left", "right"}
    return directions


def parse_hint(hint: str) -> str:
    """
    Zamienia radiową wskazówkę na komendę, której NIE wolno użyć.

    Args:
        hint: Komunikat z `/api/getmessage`, po angielsku, w żargonie żeglarskim.

    Returns:
        `"left"`, `"go"` albo `"right"` — kierunek, w którym stoi skała w następnej kolumnie.

    Raises:
        HintUnreadable: Gdy z komunikatu nie wynika jednoznacznie jeden kierunek.

    Dwie drogi do odpowiedzi, bo żadna sama nie wystarcza:

    1. **wprost** — fragment mówi, że dany kierunek jest zajęty („All the trouble is
       gathered beside starboard");
    2. **przez eliminację** — fragmenty mówią, że dwa kierunki są wolne, więc skała jest
       w trzecim. To jedyna droga dla komunikatów, które w ogóle nie nazywają kierunku
       skały: „You have room ahead and also on the right-hand side. The obstruction is
       lurking beside **the opposite window**."

    Komunikat nierozpoznany podnosi wyjątek zamiast zgadywać — wskazówkę można pobrać
    ponownie i przychodzi w innym sformułowaniu, więc zgadywanie nigdy się tu nie opłaca.
    """
    blocked: set[str] = set()
    free: set[str] = set()

    for sentence in _sentences(hint):
        carried: str | None = None
        for clause in sentence:
            sense, carried = _read_sense(clause, carried)
            directions = _read_directions(clause)
            if not directions or sense is None:
                continue
            if sense == "blocked":
                blocked |= directions
            else:
                free |= directions

    # Fragment opisujący wolny kierunek nie może jednocześnie zgłaszać go jako zajęty.
    blocked -= free

    if len(blocked) == 1:
        return blocked.pop()

    remaining = set(MOVE_OFFSETS) - free
    if len(remaining) == 1:
        return remaining.pop()

    raise HintUnreadable(f"Nie da się wskazać jednego kierunku: {hint!r}")


def safe_moves(row: int, free_rows: list[int], forbidden_row: int | None) -> list[str]:
    """
    Zwraca komendy, które nie kończą się rozbiciem, w kolejności preferencji.

    Args:
        row: Bieżący wiersz rakiety.
        free_rows: `currentColumn.freeRows` z odpowiedzi `/verify` — wiersze wolne
            w kolumnie, w której rakieta STOI.
        forbidden_row: Wiersz skały w następnej kolumnie, albo `None` gdy nieznany.

    Returns:
        Lista komend `left`/`go`/`right`. Pusta, gdy każdy ruch jest zabójczy.

    Trzy warunki naraz, każdy z innego źródła — pominięcie któregokolwiek to rozbicie:
    docelowy wiersz musi mieścić się w siatce, być wolny w BIEŻĄCEJ kolumnie (bo rakieta
    najpierw przesuwa się w pionie) i różnić się od skały w kolumnie następnej.
    """
    allowed = []
    for command, offset in MOVE_OFFSETS.items():
        target = row + offset
        if not 1 <= target <= ROWS:
            continue
        if target not in free_rows:
            continue
        if forbidden_row is not None and target == forbidden_row:
            continue
        allowed.append(command)
    return allowed


def choose_move(row: int, free_rows: list[int], blocked_direction: str, base_row: int) -> str:
    """
    Wybiera ruch: bezpieczny, a spośród bezpiecznych — zbliżający do wiersza bazy.

    Args:
        row: Bieżący wiersz rakiety.
        free_rows: Wiersze wolne w bieżącej kolumnie.
        blocked_direction: Wynik `parse_hint()`.
        base_row: Wiersz bazy w kolumnie 12.

    Returns:
        Komenda do wysłania.

    Raises:
        RuntimeError: Gdy żaden ruch nie jest bezpieczny.

    Zbliżanie do wiersza bazy nie jest kosmetyką: baza stoi w konkretnym wierszu, a każdy
    ruch przesuwa o kolumnę do przodu, więc na wyrównanie wiersza są tylko te kolumny,
    które zostały. Przy równej odległości wygrywa `go` — trzyma wiersz i nie zawęża
    wyborów w następnej kolumnie.
    """
    forbidden = row + MOVE_OFFSETS[blocked_direction]
    allowed = safe_moves(row, free_rows, forbidden)
    if not allowed:
        raise RuntimeError(
            f"Brak bezpiecznego ruchu z wiersza {row}: wolne {free_rows}, skała w {forbidden}."
        )
    return min(allowed, key=lambda c: (abs(row + MOVE_OFFSETS[c] - base_row), c != "go"))


def disarm_hash(detection_code: str) -> str:
    """SHA1 z `detectionCode` i doklejonego słowa `disarm` — format z treści zadania."""
    return hashlib.sha1(f"{detection_code}disarm".encode()).hexdigest()


def is_clear(response: str) -> bool:
    """
    Rozstrzyga, czy skaner mówi „czysto", mimo zniekształcenia przez zagłuszanie.

    Treść zadania obiecuje frazę „It's clear!", ale realnie przychodzi np. `"Its cleeear"`
    — z rozciągniętą samogłoską i bez apostrofu. Dosłowne porównanie odsiałoby to jako
    „namierzają nas" i wysłało bezsensowne rozbrajanie. Stąd dopasowanie po literach
    rdzenia, odporne na powtórzenia znaków.
    """
    letters = re.sub(r"[^a-z]", "", response.casefold())
    squeezed = re.sub(r"(.)\1+", r"\1", letters)
    return "clear" in squeezed or "iscler" in squeezed


def _canonical(token: str) -> str:
    """
    Sprowadza zniekształconą nazwę pola do postaci porównywalnej.

    Zagłuszanie losuje wielkość liter i podmienia znaki na podobne graficznie, więc
    `detectionCode` przychodzi jako `beTeCTi0NC0be`, a `frequency` jako `frEpUeNCy`.
    Ujednolicamy wielkość liter i zamieniamy cyfry na litery, które udają — reszta
    to już robota dla dopasowania rozmytego.
    """
    return token.casefold().translate(_LOOKALIKE)


def salvage_scan(response: str) -> tuple[int, str]:
    """
    Wyciąga `frequency` i `detectionCode` ze zniekształconej odpowiedzi skanera.

    Treść zadania ostrzega, że odpowiedź „może wyglądać jak JSON, ale może nie być
    zdatne do parsowania". Realny kształt (zmierzony 2026-08-25) jest gorszy, niż to
    brzmi — psute są **same nazwy pól**, nie tylko składnia::

        {
            "BatA": {
                "WEAP0nTyPe": "self-guided missile"
                "beTeCTi0NC0be`: "0E0JmF"
            },
            'bEINgTRacKEb": true,
            "frEpUeNCy": 445
        }

    Dlatego ani `json.loads()`, ani szukanie nazw pól wprost nie zadziała. Zamiast tego
    wyłuskujemy wszystkie pary `klucz: wartość` tolerancyjnym wyrażeniem (backtick zamiast
    cudzysłowu, brakujące przecinki), a klucze dopasowujemy **rozmyto** do wzorca. Próg
    podobieństwa, nie konkretna tablica podmian — żeby zmiana sposobu psucia nie wywracała
    odczytu.

    Returns:
        Para `(frequency, detectionCode)`.

    Raises:
        ValueError: Gdy któregoś pola nie da się odczytać. Właściwą reakcją jest wtedy
            ponowienie zapytania, nie zgadywanie hasha — zły hash to zestrzelenie.
    """
    pairs = _PAIR_RE.findall(response)

    def best(target: str, predicate: Callable[[str], bool]) -> str | None:
        scored = [
            (SequenceMatcher(None, _canonical(key), target).ratio(), value)
            for key, value in pairs
            if predicate(value)
        ]
        scored = [(ratio, value) for ratio, value in scored if ratio >= _KEY_SIMILARITY]
        return max(scored)[1] if scored else None

    frequency = best("frequency", str.isdigit)
    if frequency is None:
        # Ostatnia deska ratunku: w tej strukturze liczba całkowita jest tylko jedna.
        numbers = re.findall(r"(?<![\w.])(\d+)(?![\w.])", response)
        frequency = numbers[0] if len(numbers) == 1 else None

    code = best("detectioncode", lambda v: not v.isdigit() and len(v) >= 4)

    if frequency is None or code is None:
        raise ValueError(f"Nie odczytano frequency/detectionCode z: {response[:200]!r}")
    return int(frequency), code
