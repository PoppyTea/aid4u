"""
CLI dla aid4u — główny punkt wejścia.

Komendy:
    uv run run.py solve s01e01              # rozwiąż jedno zadanie
    uv run run.py solve s01e01 --dry-run    # pokaż odpowiedź bez wysyłania
    uv run run.py solve s01e01 --model gemini-2.5-flash
    uv run run.py list                      # lista dostępnych zadań
    uv run run.py status                    # pokaż zdobyte flagi

WAŻNE: setup_observability() musi być PIERWSZYM wywołaniem — przed importem
jakichkolwiek modułów LLM. Dlatego jest na górze, przed importami core.*.
"""
from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

import tasks  # noqa: F401 — uruchamia auto-import → rejestruje wszystkie @task
from core.config import get_config
from core.hub import HubClient
from core.llm import LLMClient, create_provider
from core.tasks import TASK_REGISTRY

app = typer.Typer(
    name="aid4u",
    help="AI Devs 4 — task runner",
    add_completion=False,
)
console = Console()
_FLAGS_FILE = Path(".flags.json")

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _load_flags() -> dict[str, str]:
    if _FLAGS_FILE.exists():
        return json.loads(_FLAGS_FILE.read_text())
    return {}


def _save_flag(task_name: str, flag: str) -> None:
    flags = _load_flags()
    flags[task_name] = flag
    _FLAGS_FILE.write_text(json.dumps(flags, indent=2, ensure_ascii=False))


def _make_llm(model: str) -> LLMClient:
    cfg = get_config()
    provider = create_provider(model, cfg)
    return LLMClient(provider)


# ─── Commands ─────────────────────────────────────────────────────────────────


@app.command()
def solve(
    task_name: str = typer.Argument(..., help="Nazwa zadania, np. s01e01"),
    model: str = typer.Option("gemini-2.5-flash", "--model", "-m", help="Model LLM"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Pokaż odpowiedź bez wysyłania do hubu"),
) -> None:
    """Rozwiąż jedno zadanie."""
    if task_name not in TASK_REGISTRY:
        available = ", ".join(sorted(TASK_REGISTRY.keys()))
        console.print(f"[red]Nieznane zadanie:[/] {task_name}")
        console.print(f"[dim]Dostępne: {available}[/]")
        raise typer.Exit(1)

    hub = HubClient()
    llm = _make_llm(model)
    task_cls = TASK_REGISTRY[task_name]
    task_instance = task_cls(hub, llm, dry_run=dry_run)

    try:
        flag = task_instance.run()
    except Exception as e:
        console.print(f"[red]Błąd:[/] {e}")
        raise typer.Exit(1)

    if flag and not dry_run:
        _save_flag(task_name, flag)
        console.print(f"\n[dim]Flaga zapisana w {_FLAGS_FILE}[/]")


@app.command(name="list")
def list_tasks() -> None:
    """Wyświetl listę dostępnych zadań."""
    flags = _load_flags()
    table = Table(title="Dostępne zadania", show_header=True)
    table.add_column("Zadanie", style="cyan")
    table.add_column("Klasa")
    table.add_column("Status")

    for name in sorted(TASK_REGISTRY.keys()):
        cls = TASK_REGISTRY[name]
        flag = flags.get(name)
        status = f"[green]✓ {flag}[/]" if flag else "[dim]–[/]"
        table.add_row(name, cls.__name__, status)

    console.print(table)


@app.command()
def status() -> None:
    """Pokaż postępy — zdobyte flagi i licznik punktów."""
    flags = _load_flags()
    total = len(TASK_REGISTRY)
    done = len(flags)

    console.print(f"\n[bold]Postępy:[/] {done}/{total} zadań")
    console.print(f"[bold]Do certyfikatu (20 pkt):[/] {max(0, 20 - done)} zadań pozostało\n")

    if flags:
        table = Table(show_header=True)
        table.add_column("Zadanie", style="cyan")
        table.add_column("Flaga", style="green")
        for name, flag in sorted(flags.items()):
            table.add_row(name, flag)
        console.print(table)
    else:
        console.print("[dim]Brak zdobytych flag. Zacznij od: uv run run.py solve s01e01[/]")


if __name__ == "__main__":
    app()
