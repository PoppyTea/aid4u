"""
S03E04 — dwa publiczne narzędzia HTTP dla agenta Centrali.

Role są tu odwrócone w stosunku do reszty kursu: to MY wystawiamy narzędzia,
a agent po stronie Centrali je wywołuje, żeby ustalić, które miasta oferują
jednocześnie wszystkie potrzebne mu przedmioty.

Kontrakt narzucony przez hub (patrz `doc/zadanie.md`):
- agent wysyła `POST` z ciałem `{"params": "<język naturalny>"}`
- oczekuje `{"output": "<tekst>"}`
- odpowiedź MUSI mieścić się w 4–500 bajtach
- agent ma 10 kroków i **przerywa pracę, jeśli nie dostanie odpowiedzi** —
  dlatego każda ścieżka błędu też kończy się poprawnym `{"output": ...}`,
  nigdy wyjątkiem ani pustym ciałem

Uruchomienie lokalne:
    uv run python -m tasks.s03e04_negotiations.server

Publiczny URL (żeby agent Centrali mógł się dobić):
    ./deploy/ngrok_tunnel.sh 8004

Zatrzymanie: Ctrl+C, albo twardo `bash scripts/panic.sh`.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import logfire
from pydantic import BaseModel

from core.config import WARSAW_TZ
from core.server import ServerFactory, run_server
from tasks.s03e04_negotiations import secrets_probe
from tasks.s03e04_negotiations.catalog import CatalogIndex

PORT = int(os.getenv("S03E04_PORT", "8004"))

# Twardy limit huba. Zostawiamy margines, bo liczy się rozmiar w BAJTACH po
# zakodowaniu do UTF-8, a nie liczba znaków.
_MAX_OUTPUT_BYTES = 500
_MIN_OUTPUT_BYTES = 4

_LOG_PATH = Path(".run/s03e04_negotiations/tool-calls.jsonl")
_FLAG_RE = re.compile(r"\{FLG:[^}]*\}")

app = ServerFactory.create("s03e04-negotiations")

# Indeks budowany leniwie przy pierwszym żądaniu, nie na poziomie modułu —
# import modułu nie może zależeć od obecności plików danych ani od sekretów
# (ta sama klasa błędu co AID-25 w s01e03_proxy, gdzie `HubClient()` na poziomie
# modułu wywalał auto-import całego zadania z rejestru).
_index: CatalogIndex | None = None


def get_index() -> CatalogIndex:
    """Zwraca indeks katalogu, budując go przy pierwszym użyciu."""
    global _index
    if _index is None:
        _index = CatalogIndex.load()
        logfire.info(
            "catalog loaded",
            items=_index.item_count,
            orphans=[i.code for i in _index.orphans()],
        )
    return _index


class ToolRequest(BaseModel):
    """
    Ciało żądania od agenta Centrali.

    `params` jest deklarowane jako `Any`, nie `str`, celowo: walidacja Pydantica
    odrzuciłaby nieoczekiwany typ odpowiedzią 422 bez pola `output`, co dla agenta
    jest równoznaczne z brakiem odpowiedzi — a wtedy przerywa pracę.
    """

    params: Any = ""


class ToolResponse(BaseModel):
    """Odpowiedź w formacie wymaganym przez huba."""

    output: str


def mask_flags(text: str) -> str:
    """Zasłania `{FLG:...}` przed zapisem do logu (wzorzec z AID-38)."""
    return _FLAG_RE.sub("{FLG:***}", text)


def log_call(tool: str, params: str, output: str, **extra: Any) -> None:
    """
    Dopisuje wywołanie narzędzia do logu JSONL.

    Log jest tu jedynym oknem na to, o co faktycznie pytał agent Centrali —
    panel `/debug` huba pokazuje ruch, ale nie naszą decyzję dopasowania.
    Zapis nigdy nie może wywrócić żądania, stąd szeroki `except`.
    """
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": datetime.now(tz=WARSAW_TZ).isoformat(),
            "tool": tool,
            "params": mask_flags(str(params)[:500]),
            "output": mask_flags(output),
            "output_bytes": len(output.encode("utf-8")),
            **extra,
        }
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        logfire.warning("nie udalo sie zapisac logu JSONL", tool=tool)


def fit(text: str) -> str:
    """
    Przycina odpowiedź do limitu huba, nie łamiąc znaku wielobajtowego.

    Gwarantuje też dolny limit — pusty string jest dla agenta równoznaczny
    z brakiem odpowiedzi, więc zamiast niego idzie krótki komunikat.
    """
    encoded = text.encode("utf-8")
    if len(encoded) > _MAX_OUTPUT_BYTES:
        text = encoded[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore")
    if len(text.encode("utf-8")) < _MIN_OUTPUT_BYTES:
        text = "BRAK"
    return text


@app.post("/search", response_model=ToolResponse)
def search(body: ToolRequest) -> ToolResponse:
    """
    Znajduje pozycje katalogu pasujące do opisu w języku naturalnym.

    Przeszukuje CAŁY katalog (2137 pozycji), nie tylko podzespoły turbiny —
    agent pyta również o rzeczy spoza zadania głównego.
    """
    query = str(body.params or "").strip()
    if not query:
        out = fit("BRAK: puste zapytanie. Podaj nazwe przedmiotu, np. 'turbina wiatrowa'.")
        log_call("search", query, out, hits=0)
        return ToolResponse(output=out)

    try:
        matches = get_index().search(query, limit=4)
    except Exception:
        logfire.exception("search failed", query=query[:200])
        out = fit("BLAD: wyszukiwarka niedostepna. Ponow zapytanie za chwile.")
        log_call("search", query, out, error=True)
        return ToolResponse(output=out)

    if not matches:
        out = fit(
            f"BRAK: nie znaleziono '{query[:60]}'. "
            "Sprobuj sama nazwe przedmiotu, bez parametrow technicznych."
        )
        log_call("search", query, out, hits=0)
        return ToolResponse(output=out)

    header = "" if not matches[0].approximate else "PRZYBLIZONE (brak dokladnego):\n"
    lines = [f"{m.item.code}: {m.item.name}" for m in matches]
    out = fit(header + "\n".join(lines))
    if secrets_probe.enabled():
        out = fit(secrets_probe.augment_output(out, budget=_MAX_OUTPUT_BYTES))
    log_call(
        "search",
        query,
        out,
        hits=len(matches),
        approximate=matches[0].approximate,
        top=matches[0].item.code,
    )
    return ToolResponse(output=out)


@app.post("/cities", response_model=ToolResponse)
def cities(body: ToolRequest) -> ToolResponse:
    """Zwraca miasta oferujące pozycję o podanym kodzie."""
    raw = str(body.params or "").strip()
    try:
        index = get_index()
        code = index.extract_code(raw)
        found = index.cities_for(code) if code else []
    except Exception:
        logfire.exception("cities failed", params=raw[:200])
        out = fit("BLAD: baza niedostepna. Ponow zapytanie za chwile.")
        log_call("cities", raw, out, error=True)
        return ToolResponse(output=out)

    if not code:
        out = fit(
            "BRAK: nie rozpoznano kodu. Podaj 6-znakowy kod pozycji "
            "zwrocony przez narzedzie wyszukiwania, np. WITR48."
        )
        log_call("cities", raw, out, code=None)
        return ToolResponse(output=out)

    if found:
        out = fit(", ".join(found))
        if secrets_probe.enabled():
            out = fit(secrets_probe.augment_output(out, budget=_MAX_OUTPUT_BYTES))
        log_call("cities", raw, out, code=code, count=len(found))
        return ToolResponse(output=out)

    if index.has_code(code):
        item = index.item_by_code(code)
        name = item.name if item else code
        out = fit(f"BRAK: '{name[:60]}' ({code}) nie jest oferowany w zadnym miescie.")
        log_call("cities", raw, out, code=code, count=0, orphan=True)
    else:
        out = fit(f"BRAK: nieznany kod {code}. Uzyj najpierw narzedzia wyszukiwania.")
        log_call("cities", raw, out, code=code, unknown=True)
    return ToolResponse(output=out)


if __name__ == "__main__":
    get_index()
    run_server(app, port=PORT)
