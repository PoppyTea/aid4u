"""
Sonda protokołu s03e03 (reactor) — PRZED napisaniem solvera.

Lekcja S03E03 nie podaje żadnego przykładowego JSON-a dla odpowiedzi API (potwierdzone
przez NotebookLM — treść lekcji zawiera tylko opis mechaniki, zero curl/JSON). Dwie
niewiadome, których nie da się wydedukować z opisu, trzeba zmierzyć:

1. Okres cyklu bloków — hipoteza "6 ticków" wyprowadzona z geometrii (blok wysokości 2,
   plansza 5 wierszy, odbicie od krawędzi) — do potwierdzenia sekwencją `wait`.
2. Kolejność zdarzeń w jednym ticku — czy robot rusza PRZED przesunięciem bloków, czy PO
   — wpływa na to, która kolumna jest "śmiertelna" w danym ticku.

Sekwencja: start → wait ×3 (mierzy cykl bloków bez ruchu robota) → right ×1 (mierzy
kolejność zdarzeń) → reset. Każda surowa odpowiedź huba ląduje w osobnym pliku JSON w
`data/input/s03e03_reactor/` — solution.py/reactor.py piszemy DOPIERO po przejrzeniu
tych plików, nie pod zgadywaną strukturę.

Uruchom:
    uv run python tasks/s03e03_reactor/scripts/probe_api.py
"""

from __future__ import annotations

from core.observability.setup import setup_observability

setup_observability()

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import httpx  # noqa: E402

from core.hub import HubClient  # noqa: E402

OUTPUT_DIR = Path("data/input/s03e03_reactor")
HUB_TASK_NAME = "reactor"


def _submit_diagnostic(hub: HubClient, command: str) -> dict:
    """
    Jak `hub.submit()`, ale nie wywala się na 4xx — to skrypt SONDUJĄCY, protokół
    zadania jest nieznany, więc 400 może być normalnym krokiem iteracji (jak w
    s02e03_failure), a nie błędem. Łapiemy tylko po to, żeby zobaczyć CIAŁO
    odpowiedzi i zdecydować, co ono znaczy — produkcyjny solution.py dostanie
    właściwą, zawężoną obsługę PO tym, jak zobaczymy realny kształt.

    Format `answer` USTALONY EMPIRYCZNIE (lekcja go nie podaje): musi być obiektem
    `{"command": "..."}`, nie gołym stringiem — hub zwraca `-21`/`-22`/`-990` na
    inne warianty (bare string, JSON-encoded string, zły klucz obiektu).
    """
    try:
        return hub.submit(HUB_TASK_NAME, {"command": command})
    except httpx.HTTPStatusError as exc:
        print(f"[diagnostyka] HTTP {exc.response.status_code} — ciało odpowiedzi:")
        try:
            return exc.response.json()
        except ValueError:
            return {"_raw_text": exc.response.text, "_status": exc.response.status_code}

# (nazwa pliku, komenda) — w tej kolejności, jedna po drugiej, bez powtórzeń.
SEQUENCE = [
    ("probe-01-start.json", "start"),
    ("probe-02-wait.json", "wait"),
    ("probe-03-wait.json", "wait"),
    ("probe-04-wait.json", "wait"),
    ("probe-05-right.json", "right"),
    ("probe-06-reset.json", "reset"),
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hub = HubClient()

    for filename, command in SEQUENCE:
        print(f"\n=== {command} ===")
        response = _submit_diagnostic(hub, command)
        print(json.dumps(response, indent=2, ensure_ascii=False))

        path = OUTPUT_DIR / filename
        path.write_text(json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"-> zapisano {path}")

        flag = hub.get_flag(response)
        if flag:
            print(f"\n*** FLAGA już tutaj (niespodzianka)?! {flag} ***")
            break


if __name__ == "__main__":
    main()
