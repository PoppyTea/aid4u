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
    Dzieli wskazówkę na zdania i człony rozdzielone interpunkcją lub spójnikami.
    
    Parametry:
        hint (str): Tekst wskazówki.
    
    Zwraca:
        list[list[str]]: Lista zdań, z których każde zawiera listę niepustych członów.
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
    Converts a radio hint into the direction of the rock in the next column.
    
    Parameters:
        hint (str): An English nautical message describing the available or blocked directions.
    
    Returns:
        str: `"left"`, `"go"`, or `"right"` indicating the blocked direction.
    
    Raises:
        HintUnreadable: If the hint does not identify exactly one blocked direction.
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
    Return safe movement commands in preference order.
    
    Parameters:
        row (int): The rocket's current grid row.
        free_rows (list[int]): Rows available in the current column.
        forbidden_row (int | None): The rock's row in the next column, if known.
    
    Returns:
        list[str]: Safe commands among `left`, `go`, and `right`.
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
    """
    Generate the hexadecimal SHA-1 hash used to disarm the system.
    
    Parameters:
    	detection_code (str): Detection code to combine with the disarm suffix.
    
    Returns:
    	str: Hexadecimal SHA-1 digest of the detection code followed by "disarm".
    """
    return hashlib.sha1(f"{detection_code}disarm".encode()).hexdigest()


def is_clear(response: str) -> bool:
    """
    Rozpoznaje, czy zniekształcona odpowiedź skanera oznacza, że droga jest wolna.
    
    Parameters:
        response (str): Odpowiedź skanera, potencjalnie zawierająca powtórzone znaki lub brak apostrofu.
    
    Returns:
        bool: `True`, jeśli odpowiedź zawiera rozpoznawalny komunikat „clear”, w przeciwnym razie `False`.
    """
    letters = re.sub(r"[^a-z]", "", response.casefold())
    squeezed = re.sub(r"(.)\1+", r"\1", letters)
    return "clear" in squeezed or "iscler" in squeezed


def _canonical(token: str) -> str:
    """
    Ujednolica zniekształconą nazwę pola do postaci używanej przy porównywaniu.
    
    Parameters:
        token (str): Nazwa pola do ujednolicenia.
    
    Returns:
        str: Nazwa zapisana małymi literami, z zastąpionymi znakami wyglądającymi jak litery.
    """
    return token.casefold().translate(_LOOKALIKE)


def salvage_scan(response: str) -> tuple[int, str]:
    """
    Extracts the frequency and detection code from a distorted scanner response.
    
    Returns:
        tuple[int, str]: The scanner frequency and detection code.
    
    Raises:
        ValueError: If either value cannot be extracted from the response.
    """
    pairs = _PAIR_RE.findall(response)

    def best(target: str, predicate: Callable[[str], bool]) -> str | None:
        """
        Find the value whose key most closely matches the target and satisfies the predicate.
        
        Parameters:
            target (str): Key text to match.
            predicate (Callable[[str], bool]): Condition a value must satisfy.
        
        Returns:
            str | None: The matching value with the highest similarity, or None if no value meets the similarity threshold.
        """
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
