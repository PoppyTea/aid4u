"""
Feedback kontekstowy: zamiana wyjątku narzędzia w komunikat, na który model może zareagować.

Do 2026-08-20 `run_agent_loop()` zwijał KAŻDY wyjątek narzędzia do stałego stringa
`"ERROR: Tool execution failed."`. Model nie miał wtedy jak odróżnić „rate limit,
poczekaj i ponów" od „zły argument, popraw wywołanie" — więc albo ponawiał w kółko
to samo błędne wywołanie, albo poddawał się przy błędzie przejściowym. Każda
udokumentowana strata $4-10 w komentarzach S03E02 wynikała z takiej ślepej pętli.

Moduł robi trzy rzeczy:
- **klasyfikuje** błąd jako przejściowy albo trwały i mówi modelowi wprost, co z tym
  zrobić (przy 429/503 czekać, przy 4xx poprawić argumenty),
- **eksponuje kod HTTP**, bo to jedyny sygnał pozwalający odróżnić ban od literówki,
- **redaguje sekrety**, bo treść wyjątku często niesie pełny URL z `apikey=` w query.
"""

from __future__ import annotations

import re

# Klucz huba jest UUID-em; redagujemy każdy UUID, nie tylko ten konkretny, żeby nie
# wiązać formatera z configiem (i żeby złapać klucze innych usług).
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)
_QUERY_SECRET_RE = re.compile(
    r"((?:api[-_]?key|apikey|token|secret|password|passwd|key|sig|signature)=)[^&\s\"'>]+",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"((?:Bearer|Basic)\s+)[A-Za-z0-9._\-+/=]+", re.IGNORECASE)
# Klucze providerów mają rozpoznawalne prefiksy — łapiemy je nawet poza query stringiem.
_PROVIDER_KEY_RE = re.compile(r"\b(sk|pk|rk|xoxb|ghp|gho|AIza)[-_][A-Za-z0-9._\-]{8,}", re.IGNORECASE)

# Kody, po których ponowienie ma sens. 429/503 to wprost rate limit i przeciążenie —
# oba przejściowe. 408/502/504 to problemy transportu/bramy, też przejściowe.
_TRANSIENT_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

_MAX_BODY_CHARS = 300


def redact(text: str) -> str:
    """
    Zaciera sekrety w tekście, który trafi do kontekstu modelu albo do logu.

    Treść wyjątku sieciowego zwykle zawiera pełny URL — a hub przyjmuje `apikey`
    w query stringu, więc bez tego kroku klucz lądowałby w historii rozmowy.
    """
    text = _QUERY_SECRET_RE.sub(r"\1<REDACTED>", text)
    text = _BEARER_RE.sub(r"\1<REDACTED>", text)
    text = _PROVIDER_KEY_RE.sub("<REDACTED>", text)
    return _UUID_RE.sub("<REDACTED>", text)


def _http_details(exc: Exception) -> tuple[int, str] | None:
    """
    Wyciąga (status, fragment ciała) z wyjątku HTTP, o ile to wyjątek HTTP.

    Sprawdzamy `response` kaczo zamiast importować `httpx` — moduł ma nie zależeć
    od konkretnego klienta HTTP, a inne biblioteki wystawiają ten sam kształt.
    """
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if not isinstance(status, int):
        return None
    try:
        body = (response.text or "").strip()
    except Exception:
        body = ""
    return status, body[:_MAX_BODY_CHARS]


def _guidance(exc: Exception, http: tuple[int, str] | None) -> str:
    """Zwraca instrukcję dla modelu: co zrobić dalej z tym konkretnym błędem."""
    if http is not None:
        status, _ = http
        if status in _TRANSIENT_STATUS:
            return (
                "Blad PRZEJSCIOWY. Odczekaj chwile i ponow TO SAMO wywolanie. "
                "Nie zmieniaj argumentow i nie rezygnuj z zadania."
            )
        if status in (401, 403):
            return (
                "Brak uprawnien — ponawianie nic nie da. Nie powtarzaj tego wywolania; "
                "sprobuj innego narzedzia albo zakoncz i zglos problem."
            )
        if 400 <= status < 500:
            return (
                "Blad TRWALY po stronie zadania. Popraw argumenty wywolania — "
                "ponowienie bez zmian da ten sam wynik."
            )
    if isinstance(exc, TimeoutError):
        return "Przekroczono czas oczekiwania. Ponow wywolanie, ewentualnie zaw z mniejszym zakresem."
    if isinstance(exc, (KeyError, ValueError, TypeError)):
        return (
            "Argumenty wywolania sa niepoprawne. Sprawdz nazwy i typy pol wzgledem "
            "opisu narzedzia, potem sprobuj ponownie."
        )
    return "Popraw wywolanie albo sprobuj innego narzedzia. Nie powtarzaj w kolko tego samego."


def format_tool_error(tool_name: str, exc: Exception) -> str:
    """
    Buduje komunikat o błędzie narzędzia przeznaczony DLA MODELU.

    Zawiera typ wyjątku, jego treść, kod HTTP (gdy jest) i jawną instrukcję co dalej.
    Wszystko po redakcji sekretów. Wynik jest krótki — trafia do historii rozmowy
    przy każdej nieudanej iteracji, więc rozwlekłość kosztuje tokeny w pętli.

    Args:
        tool_name: Nazwa narzędzia, które zawiodło.
        exc: Przechwycony wyjątek. `AbortRun` NIE może tu trafić — to sygnał kill
            switcha, propagowany osobno przez `run_agent_loop()`.
    """
    http = _http_details(exc)
    message = str(exc).strip() or exc.__class__.__name__

    if http is not None:
        status, body = http
        head = f"ERROR [{tool_name}]: HTTP {status} — {message}"
        if body:
            head = f"{head}\nOdpowiedz serwera: {body}"
    else:
        head = f"ERROR [{tool_name}]: {exc.__class__.__name__}: {message}"

    return redact(f"{head}\nCo zrobic: {_guidance(exc, http)}")
