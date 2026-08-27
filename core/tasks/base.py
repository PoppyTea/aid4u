"""
Template Method + Registry pattern.

BaseTask definiuje SZKIELET algorytmu:
    run() → fetch_data() → solve() → submit()

Każde zadanie implementuje TYLKO solve() (i opcjonalnie fetch_data()).
Reszta — timing, logowanie, tryb dry-run, submisja — jest wspólna.

Registry Pattern:
    @task("s01e01")
    class PeopleTask(BaseTask): ...

    TASK_REGISTRY["s01e01"] → PeopleTask
"""

from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import logfire
from rich.console import Console

from core.config import WARSAW_TZ
from core.hub import HubClient, LocalCache
from core.llm import LLMClient
from core.observability.decorators import propagate_attrs
from core.runtime import AbortRun, check_abort, end_run, start_run

_console = Console()
_OUTPUTS_DIR = Path("data/run-history")

# Registry: nazwa zadania → klasa
TASK_REGISTRY: dict[str, type[BaseTask]] = {}

# Co `--dry-run` naprawdę robi w danym zadaniu. Kontrakt istniał wcześniej, ale wyłącznie
# jako komentarz w `tasks/s02e05_drone/solution.py` — i przez to rozjechał się dwanaście
# razy: sześć zadań pilnowało `self.dry_run`, siedem nie, a pomoc `run.py` obiecywała
# wszystkim „pokaż odpowiedź bez wysyłania". Deklaracja jest teraz jawna i sprawdzana
# testem, bo różnica między tymi trzema przypadkami jest różnicą w skutkach ubocznych,
# a nie w stylu.
DRY_RUN_SAFE = "safe"
"""`solve()` nie dotyka huba, dopóki nie zna odpowiedzi — `--dry-run` niczego nie zmienia."""

DRY_RUN_LIVE = "live"
"""
`solve()` MUSI rozmawiać z hubem, żeby policzyć odpowiedź, ale skutki są odwracalne.

Zadania protokołowe (`domatowo`, `filesystem`, `foodwarehouse`, `goingthere`,
`shellaccess`): odpowiedzi nie da się wyliczyć offline, bo powstaje z odpowiedzi huba.
`--dry-run` wykonuje więc pełny protokół i wstrzymuje wyłącznie punktowane zgłoszenie.
Dopuszczalne, bo każde z nich albo ma darmowy `reset`/`start`, albo tylko czyta.
"""

DRY_RUN_UNSAFE = "unsafe"
"""
`solve()` wywołuje skutki NIEODWRACALNE — `--dry-run` jest odmawiany.

Dziś dotyczy `s03e02_firmware`: `editline` i `rm` na żywej maszynie wirtualnej, gdzie
błędny ruch kończy się banem i przywróceniem VM, a jedyny „reset" (`reboot`) kasuje
cały postęp i jest świadomie poza allowlistą.
"""

DRY_RUN_MODES = frozenset({DRY_RUN_SAFE, DRY_RUN_LIVE, DRY_RUN_UNSAFE})


def task(name: str, *, hub_name: str | None = None):
    """
    Dekorator rejestrujący zadanie w TASK_REGISTRY.

    `name` to klucz CLI/rejestru/logów/nazwy pliku wyjściowego.
    `hub_name` to nazwa oczekiwana przez pole "task" w POST /verify —
    domyślnie taka sama jak `name`, ale niektóre zadania na hubie mają
    inną nazwę niż ich slug w tym repo (np. CLI "s01e01" → hub "people").

    Użycie:
        @task("s01e01", hub_name="people")
        class PeopleTask(BaseTask):
            def solve(self, data):
                ...
    """
    def decorator(cls: type[BaseTask]) -> type[BaseTask]:
        """Rejestruje `cls` w TASK_REGISTRY pod `name` i zapisuje na klasie jej nazwę CLI/hub."""
        TASK_REGISTRY[name] = cls
        cls._task_name = name
        cls._hub_task_name = hub_name or name
        return cls

    return decorator


class BaseTask(ABC):
    """
    Klasa bazowa dla wszystkich zadań kursu.

    Template Method: run() definiuje stały przepływ,
    fetch_data() i solve() mogą być nadpisane przez podklasy.
    """

    _task_name: str = ""
    _hub_task_name: str = ""

    dry_run_mode: str = DRY_RUN_SAFE
    """
    Co `--dry-run` robi w tym zadaniu — patrz stałe `DRY_RUN_*`.

    Domyślnie `safe`, bo taka jest większość zadań (pobierz dane → policz → zgłoś).
    Zadanie, którego `solve()` woła hub przed poznaniem odpowiedzi, MUSI to
    nadpisać; pilnuje tego `tests/core/tasks/test_dry_run_contract.py`.
    """

    def __init__(
        self,
        hub: HubClient,
        llm: LLMClient,
        *,
        dry_run: bool = False,
        max_seconds: float | None = None,
        max_cost: float | None = None,
    ) -> None:
        """
        Wstrzykuje zależności (hub/llm), tryb dry-run i opcjonalny budżet wall-clock (Warstwa 2
        kill switcha).
        """
        self.hub = hub
        self.llm = llm
        self.cache = LocalCache(self._task_name or self.__class__.__name__)
        self.dry_run = dry_run
        self._max_seconds = max_seconds
        self._max_cost = max_cost

    # ─── Template Method — nie nadpisuj ──────────────────────────────────────

    def run(self) -> str | None:
        """
        Główny przepływ zadania. Nie nadpisuj tej metody.
        Zamiast tego implementuj fetch_data() i solve().
        """
        task_name = self._task_name or self.__class__.__name__
        _console.print(f"\n[bold]Running task:[/] [cyan]{task_name}[/]")

        # PRZED `start_run()`: odmowa musi nastąpić zanim cokolwiek zdąży dotknąć huba,
        # a nie po zbudowaniu grupy procesów i wystartowaniu budżetu.
        if self.dry_run and not self._announce_dry_run(task_name):
            return None

        start_run(max_seconds=self._max_seconds, max_cost=self._max_cost)
        _console.print(
            "[dim]Kill switch: `bash scripts/panic.sh` (twardy, gwarantowany) albo "
            "`uv run run.py panic --graceful` (czyste zamknięcie).[/]"
        )

        # sessionId = nazwa zadania + timestamp uruchomienia + krótki losowy sufiks —
        # grupuje w Langfuse wszystkie generacje/tool observation tego jednego
        # `run.py solve` pod jedną sesją (patrz strategy/observability.md, hierarchia
        # Session→Trace→...). Bez tego propagate_attrs() istniał w kodzie od dawna,
        # ale nigdy nie był wołany — każda generacja lądowała w Langfuse bez żadnego
        # kontekstu sesji. Sufiks jest konieczny: sama sekunda (`%H%M%S`) koliduje —
        # dwa uruchomienia tego samego zadania w tej samej sekundzie dostałyby
        # identyczny session_id i ich generacje zlałyby się w jedną sesję w panelu.
        session_id = (
            f"{task_name}-{datetime.now(tz=WARSAW_TZ).strftime('%m%d-%H%M%S')}"
            f"-{uuid.uuid4().hex[:8]}"
        )

        try:
            with (
                logfire.span(f"task.{task_name}"),
                propagate_attrs(trace_name=task_name, session_id=session_id),
            ):
                start = time.perf_counter()

                try:
                    # Sprawdź PRZED jakąkolwiek robotą, nie tylko wewnątrz solve() —
                    # zadania bez run_agent_loop() (pojedyncze blokujące wywołanie)
                    # inaczej ominęłyby kill switch aż do _submit() na końcu.
                    check_abort()
                    data = self.fetch_data()
                    answer = self.solve(data)
                    self._save_output(answer)
                    flag = self._submit(self._hub_task_name or task_name, answer)
                except AbortRun as abort:
                    logfire.warning(f"Task {task_name} aborted", reason=str(abort))
                    _console.print(f"[yellow]⏹ Przerwano:[/] {abort}")
                    return None
                except Exception:
                    logfire.exception(f"Task {task_name} failed")
                    raise

                elapsed = round(time.perf_counter() - start, 2)
                logfire.info(f"Task {task_name} completed", elapsed_s=elapsed, flag=flag)

            if flag:
                _console.print(f"[bold green]✓ Flag:[/] {flag}")
            return flag
        finally:
            self._flush_langfuse()
            end_run()

    def _announce_dry_run(self, task_name: str) -> bool:
        """
        Mówi, co `--dry-run` naprawdę zrobi w tym zadaniu, i odmawia gdy trzeba.

        Args:
            task_name: Nazwa zadania, do komunikatu.

        Returns:
            `True` gdy wolno kontynuować, `False` gdy przebieg ma się nie odbyć.

        Raises:
            ValueError: Gdy zadanie deklaruje tryb spoza `DRY_RUN_MODES` — literówka
                w deklaracji cicho zdejmowałaby ochronę, więc kończy się błędem.
        """
        if self.dry_run_mode not in DRY_RUN_MODES:
            raise ValueError(
                f"{task_name}: nieznany dry_run_mode={self.dry_run_mode!r}; "
                f"dozwolone: {sorted(DRY_RUN_MODES)}"
            )

        if self.dry_run_mode == DRY_RUN_SAFE:
            return True

        if self.dry_run_mode == DRY_RUN_UNSAFE:
            _console.print(
                f"[bold red]--dry-run odmówiony dla {task_name}.[/] Rozwiązanie wywołuje "
                "skutki nieodwracalne po stronie huba, więc próbny przebieg byłby "
                "przebiegiem prawdziwym. Uruchom bez [bold]--dry-run[/], świadomie."
            )
            return False

        # DRY_RUN_LIVE — wykonujemy, ale bez udawania, że to symulacja.
        _console.print(
            f"[yellow]--dry-run w {task_name} NIE jest suchym przebiegiem.[/] Odpowiedź "
            "powstaje z odpowiedzi huba, więc cały protokół wykona się na żywo; "
            "wstrzymane zostanie wyłącznie punktowane zgłoszenie. Skutki są odwracalne "
            "(`reset`/`start`)."
        )
        return True

    @staticmethod
    def _flush_langfuse() -> None:
        """
        `uv run run.py solve sXXeYY` to krótkotrwały proces CLI — kończy się
        zaraz po run(). Bez jawnego flush() zbuforowane trace'y mogą nie
        zdążyć wysłać się do Langfuse przed wyjściem (atexit hook to tylko
        fallback, niegwarantowany przy każdym trybie zakończenia procesu).
        """
        try:
            from langfuse import get_client

            get_client().flush()
        except Exception:
            pass

    def _save_output(self, answer: Any) -> Path:
        """
        Zapisuje odpowiedź agenta do data/run-history/ (trwały ślad, nie cache —
        cache w .cache/ nadpisuje ten sam klucz przy każdym fetchu, tu zostaje
        historia każdego uruchomienia). Wyłącznie audit-trail per-run — nie mylić
        z data/output/, gdzie trafiają dane faktycznie przydatne w kolejnych
        zadaniach (patrz data/AGENTS.md).

        Nazwa: [nazwa zadania]-[MMDD-hhmmss]-[org. nazwa pliku z huba].
        Gdy zadanie nie pobierało pliku przez cache.get_or_fetch (last_key
        puste), pada na 'answer.json'.
        """
        task_name = self._task_name or self.__class__.__name__

        timestamp = datetime.now(tz=WARSAW_TZ).strftime("%m%d-%H%M%S")
        org_name = self.cache.last_key or "answer.json"

        _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        path = _OUTPUTS_DIR / f"{task_name}-{timestamp}-{org_name}"

        if isinstance(answer, bytes):
            path.write_bytes(answer)
        elif isinstance(answer, str):
            path.write_text(answer, encoding="utf-8")
        else:
            path.write_text(json.dumps(answer, indent=2, ensure_ascii=False), encoding="utf-8")

        logfire.info(f"Output saved to {path}")
        return path

    def _submit(self, task_name: str, answer: Any) -> str | None:
        """Wysyła finalną odpowiedź do huba (albo drukuje ją i wraca None w dry-run)."""
        check_abort()
        if self.dry_run:
            _console.print(f"[yellow]DRY RUN — answer would be:[/] {str(answer)[:300]}")
            return None

        response = self.hub.submit(task_name, answer)
        return self.hub.get_flag(response)

    # ─── Do implementacji w zadaniu ───────────────────────────────────────────

    def fetch_data(self) -> Any:
        """
        Opcjonalny krok pobierania danych.
        Domyślnie: brak danych (None). Nadpisz gdy zadanie wymaga pobrania.
        """
        return None

    @abstractmethod
    def solve(self, data: Any) -> Any:
        """
        JEDYNA metoda którą MUSISZ zaimplementować.

        Args:
            data: Wynik fetch_data() (domyślnie None)

        Returns:
            Odpowiedź do wysłania do /verify (string, dict, list — zależnie od zadania)
        """
        ...
