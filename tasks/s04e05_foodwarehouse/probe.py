"""
Sonda eksploracyjna S04E05 — jedno wywołanie narzędzia magazynu, surowa odpowiedź.

Całe API zadania idzie przez `/verify` w polu `answer` jako obiekt z kluczem `tool`,
więc sonda przyjmuje JSON i przekazuje go bez zmian:

    uv run python -m tasks.s04e05_foodwarehouse.probe '{"tool":"help"}'

Istnieje osobno od `s05e03/probe.py`, bo tam treścią zgłoszenia jest polecenie powłoki,
a tu obiekt narzędzia — wspólna abstrakcja nad dwoma różnymi protokołami kosztowałaby
więcej, niż warte są dwa pliki po trzydzieści linii.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import json
import sys

from rich.console import Console

from core.hub import HubClient

HUB_TASK = "foodwarehouse"

_console = Console()


def main(argv: list[str]) -> int:
    """Wysyła kolejno podane wywołania narzędzi i wypisuje odpowiedzi huba."""
    if len(argv) < 2:
        _console.print("[red]Użycie:[/] uv run python -m tasks.s04e05_foodwarehouse.probe '{\"tool\":\"help\"}' [...]")
        return 2

    hub = HubClient()
    for raw in argv[1:]:
        _console.print(f"\n[bold cyan]→ {raw}[/]")
        response = hub.submit(HUB_TASK, json.loads(raw))
        _console.print(json.dumps(response, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
