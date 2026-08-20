"""
CLI dla aid4u — główny punkt wejścia.

Komendy:
    uv run run.py solve s01e01              # rozwiąż jedno zadanie
    uv run run.py solve s01e01 --dry-run    # pokaż odpowiedź bez wysyłania
    uv run run.py solve s01e01 --model gemini-2.5-flash
    uv run run.py solve s01e01 --model gemini-3.5-flash --premium  # płatny tier Gemini
    uv run run.py list                      # lista dostępnych zadań
    uv run run.py status                    # pokaż zdobyte flagi
    uv run run.py panic                     # awaryjny stop — patrz scripts/panic.sh
    uv run run.py panic --graceful          # czyste zamknięcie na najbliższym checkpoint

WAŻNE: setup_observability() musi być PIERWSZYM wywołaniem — przed importem
jakichkolwiek modułów LLM. Dlatego jest na górze, przed importami core.*.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import json
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

import tasks  # noqa: F401 — uruchamia auto-import → rejestruje wszystkie @task
from core.config import get_config
from core.hub import HubClient
from core.llm import LLMClient, create_provider
from core.runtime import request_stop
from core.tasks import TASK_REGISTRY

app = typer.Typer(
    name="aid4u",
    help="AI Devs 4 — task runner",
    add_completion=False,
)
console = Console()
_FLAGS_FILE = Path(".flags.json")

# Sufiks klucza flagi sekretnej w `.flags.json` (patrz AGENTS.md, zasada 7).
SECRET_SUFFIX = "_secret"

# Domyślny budżet kosztu na przebieg. Włączony domyślnie, bo każda udokumentowana
# strata $4-10 w komentarzach kursu do S03E02 wynikała z ZAPOMNIANEJ osłony, nie
# z jej braku w kodzie. `--max-cost 0` wyłącza.
DEFAULT_MAX_COST = 1.0


def partition_flags(flags: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """
    Rozdziela flagi na główne i sekretne.

    Flagi sekretne NIE liczą się do certyfikatu — to osobna ścieżka, odblokowująca
    materiały edukacyjne. Wliczanie ich zaniżałoby „ile jeszcze do 20", czyli
    dokładnie tę liczbę, według której planujemy sezon.

    Returns:
        Para `(główne, sekretne)`, obie zachowujące oryginalne klucze.
    """
    secrets = {n: f for n, f in flags.items() if n.endswith(SECRET_SUFFIX)}
    main = {n: f for n, f in flags.items() if n not in secrets}
    return main, secrets

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _load_flags() -> dict[str, str]:
    """Wczytuje `.flags.json` (mapa zadanie→flaga); pusty słownik jeśli plik jeszcze nie istnieje."""
    if _FLAGS_FILE.exists():
        return json.loads(_FLAGS_FILE.read_text())
    return {}


def _save_flag(task_name: str, flag: str) -> None:
    """Dopisuje zdobytą flagę do `.flags.json`, zachowując wcześniej zapisane."""
    flags = _load_flags()
    flags[task_name] = flag
    _FLAGS_FILE.write_text(json.dumps(flags, indent=2, ensure_ascii=False))


def _make_llm(model: str, *, premium: bool = False) -> LLMClient:
    """Buduje LLMClient dla podanego modelu (i tieru Gemini standard/premium, jeśli dotyczy)."""
    cfg = get_config()
    tier = "premium" if premium else "standard"
    provider = create_provider(model, cfg, tier=tier)
    return LLMClient(provider)


# ─── Commands ─────────────────────────────────────────────────────────────────


@app.command()
def solve(
    task_name: str = typer.Argument(..., help="Nazwa zadania, np. s01e01"),
    model: str = typer.Option("gemini-2.5-flash", "--model", "-m", help="Model LLM"),
    premium: bool = typer.Option(
        False,
        "--premium",
        "-p",
        help=(
            "Użyj płatnego tier Gemini (osobny klucz GEMINI_API_KEY_PREMIUM) zamiast "
            "darmowego. Dotyczy tylko modeli gemini-*; inni providerzy ignorują tę flagę."
        ),
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Pokaż odpowiedź bez wysyłania do hubu"),
    max_seconds: float | None = typer.Option(
        None,
        "--max-seconds",
        help=(
            "Twardy budżet wall-clock na cały przebieg (Warstwa 2 kill switcha) — "
            "przekroczenie przerywa solve() czysto (AbortRun), bez ubijania procesu."
        ),
    ),
    max_cost: float | None = typer.Option(
        DEFAULT_MAX_COST,
        "--max-cost",
        help=(
            "Twardy budżet kosztu LLM w USD na cały przebieg (Warstwa 2 kill switcha). "
            f"Domyślnie ${DEFAULT_MAX_COST:.2f}; `--max-cost 0` wyłącza. Bezpiecznik, nie "
            "prewencja — cenę znamy dopiero PO wywołaniu, więc limit ogranicza "
            "przekroczenie do jednego wywołania."
        ),
    ),
) -> None:
    """Rozwiąż jedno zadanie."""
    if task_name not in TASK_REGISTRY:
        available = ", ".join(sorted(TASK_REGISTRY.keys()))
        console.print(f"[red]Nieznane zadanie:[/] {task_name}")
        console.print(f"[dim]Dostępne: {available}[/]")
        raise typer.Exit(1)

    hub = HubClient()
    llm = _make_llm(model, premium=premium)
    task_cls = TASK_REGISTRY[task_name]
    task_instance = task_cls(
        hub, llm, dry_run=dry_run, max_seconds=max_seconds, max_cost=max_cost
    )

    try:
        flag = task_instance.run()
    except Exception as e:
        console.print(f"[red]Błąd:[/] {e}")
        raise typer.Exit(1)

    if flag and not dry_run:
        _save_flag(task_name, flag)
        console.print(f"\n[dim]Flaga zapisana w {_FLAGS_FILE}[/]")


@app.command()
def panic(
    graceful: bool = typer.Option(
        False,
        "--graceful",
        "-g",
        help=(
            "Zapisz .run/STOP zamiast zabijać proces — bieżący przebieg zatrzyma się "
            "czysto na najbliższym bezpiecznym punkcie (może potrwać kilka sekund)."
        ),
    ),
) -> None:
    """
    Awaryjny wyłącznik. Domyślnie: twardy kill całej grupy procesów bieżącego
    przebiegu (SIGTERM→SIGKILL po 2s) przez scripts/panic.sh.

    UWAGA — jeśli środowisko Pythona jest niesprawne (np. rozwalony venv), ta
    komenda może się nie uruchomić. Gwarantowana ścieżka to bezpośrednio:
        bash scripts/panic.sh
    (czysty bash, zero zależności) — patrz core/AGENTS.md.
    """
    if graceful:
        request_stop()
        console.print("[yellow]Zapisano .run/STOP — przebieg zatrzyma się na najbliższym bezpiecznym punkcie.[/]")
        return

    script = Path(__file__).parent / "scripts" / "panic.sh"
    if not script.is_file():
        console.print(f"[red]Brak {script} — nie mogę wywołać awaryjnego wyłącznika.[/]")
        raise typer.Exit(1)
    result = subprocess.run(["bash", str(script)])
    raise typer.Exit(result.returncode)


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

    main_flags, secrets = partition_flags(flags)
    done = len(main_flags)

    console.print(f"\n[bold]Postępy:[/] {done}/{total} zadań")
    console.print(f"[bold]Do certyfikatu (20 pkt):[/] {max(0, 20 - done)} zadań pozostało")
    if secrets:
        console.print(f"[magenta]Flagi sekretne:[/] {len(secrets)} (poza licznikiem)")
    console.print()

    if flags:
        table = Table(show_header=True)
        table.add_column("Zadanie", style="cyan")
        table.add_column("Flaga", style="green")
        table.add_column("Typ", style="dim")
        for name, flag in sorted(main_flags.items()):
            table.add_row(name, flag, "główna")
        for name, flag in sorted(secrets.items()):
            table.add_row(name.removesuffix(SECRET_SUFFIX), flag, "[magenta]sekretna[/]")
        console.print(table)
    else:
        console.print("[dim]Brak zdobytych flag. Zacznij od: uv run run.py solve s01e01[/]")


if __name__ == "__main__":
    app()
