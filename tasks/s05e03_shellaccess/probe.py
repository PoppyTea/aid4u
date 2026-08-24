"""
Sonda eksploracyjna S05E03 — jedno polecenie na zdalnym archiwum, surowa odpowiedź.

Rozwiązanie jest deterministyczne, ale sekwencja `grep`-ów wychodzi dopiero z oglądu
realnego archiwum: treść zadania podaje tylko katalog `/data`, nic o układzie plików
ani o formacie wpisów. Ten skrypt służy do tego oglądu i zostaje w repo, bo bez niego
`solution.py` wygląda na zbiór magicznych regexów bez wyjaśnienia, skąd się wzięły.

    uv run python -m tasks.s05e03_shellaccess.probe 'ls -la /data' 'wc -l /data/time_logs.csv'

Przyjmuje dowolnie wiele poleceń i wykonuje je po kolei w jednym procesie — start
obserwabilności trwa dłużej niż samo zapytanie, więc pakowanie kilku sond w jeden
przebieg realnie skraca eksplorację.

Przy pierwszym poleceniu wypisuje pełną odpowiedź huba (nie tylko stdout), żeby było
widać także kod i komunikat — to one rozstrzygają, czy hub w ogóle wpuszcza do S05.
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
from core.runtime import CommandRejected
from tasks.s05e03_shellaccess.archive import ArchiveShell

_console = Console()


def main(argv: list[str]) -> int:
    """Wykonuje kolejno polecenia podane w argv i wypisuje ich wynik."""
    if len(argv) < 2:
        _console.print(
            "[red]Użycie:[/] uv run python -m tasks.s05e03_shellaccess.probe "
            r"'<polecenie>' \[...]"
        )
        return 2

    shell = ArchiveShell(HubClient())
    for index, cmd in enumerate(argv[1:], start=1):
        # `escape()` i `markup=False` niżej nie są kosmetyką: Rich traktuje `[cokolwiek]`
        # jako znacznik stylu i przy nieznanej nazwie **po cichu usuwa go z wyjścia**.
        # Sonda drukuje surową treść zdalnego archiwum, więc bez tego fragment wyniku
        # `grep` z nawiasem kwadratowym zniknąłby bez śladu — a to narzędzie, którego
        # jedynym zadaniem jest pokazać, co naprawdę jest po drugiej stronie.
        _console.print(f"\n[bold cyan]$ {escape(cmd)}[/]")
        try:
            output = shell.run(cmd)
        except CommandRejected as rejected:
            _console.print(f"[red]Bramka odrzuciła polecenie:[/] {rejected}")
            return 1

        # Pełna odpowiedź tylko dla pierwszego polecenia — dalej interesuje nas
        # sam stdout, a `code`/`message` powtarzają się bez wartości informacyjnej.
        if index == 1:
            status = json.dumps(
                {k: v for k, v in shell.last_response.items() if k != "output"},
                ensure_ascii=False,
            )
            _console.print(f"[dim]{escape(status)}[/]")
        if output:
            _console.print(output, markup=False, highlight=False)
        else:
            _console.print("[dim](puste)[/]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
