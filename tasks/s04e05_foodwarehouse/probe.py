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
from rich.markup import escape

from core.hub import HubClient

HUB_TASK = "foodwarehouse"

_console = Console()


def main(argv: list[str]) -> int:
    """Wysyła kolejno podane wywołania narzędzi i wypisuje odpowiedzi huba."""
    if len(argv) < 2:
        _console.print(
            "[red]Użycie:[/] uv run python -m tasks.s04e05_foodwarehouse.probe "
            r"""'{"tool":"help"}' \[...]"""
        )
        return 2

    hub = HubClient()
    for raw in argv[1:]:
        # `escape()` tutaj i `markup=False` niżej: Rich traktuje `[cokolwiek]` jako
        # znacznik stylu i przy nieznanej nazwie **po cichu usuwa go z wyjścia**.
        # Odpowiedzi tego API to JSON pełen tablic, więc bez tego sonda pokazywałaby
        # okrojoną treść — a jej jedynym zadaniem jest pokazać, co hub naprawdę odesłał.
        _console.print(f"\n[bold cyan]→ {escape(raw)}[/]")
        response = hub.submit(HUB_TASK, json.loads(raw))
        rendered = json.dumps(response, indent=2, ensure_ascii=False)
        _console.print(rendered, markup=False, highlight=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
