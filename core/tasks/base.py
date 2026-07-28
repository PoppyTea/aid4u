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
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import logfire
from rich.console import Console

from core.config import WARSAW_TZ
from core.hub import HubClient, LocalCache
from core.llm import LLMClient

_console = Console()
_OUTPUTS_DIR = Path("data/outputs")

# Registry: nazwa zadania → klasa
TASK_REGISTRY: dict[str, type[BaseTask]] = {}


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

    def __init__(
        self,
        hub: HubClient,
        llm: LLMClient,
        *,
        dry_run: bool = False,
    ) -> None:
        self.hub = hub
        self.llm = llm
        self.cache = LocalCache(self._task_name or self.__class__.__name__)
        self.dry_run = dry_run

    # ─── Template Method — nie nadpisuj ──────────────────────────────────────

    def run(self) -> str | None:
        """
        Główny przepływ zadania. Nie nadpisuj tej metody.
        Zamiast tego implementuj fetch_data() i solve().
        """
        task_name = self._task_name or self.__class__.__name__
        _console.print(f"\n[bold]Running task:[/] [cyan]{task_name}[/]")

        with logfire.span(f"task.{task_name}"):
            start = time.perf_counter()

            try:
                data = self.fetch_data()
                answer = self.solve(data)
                self._save_output(answer)
                flag = self._submit(self._hub_task_name or task_name, answer)
            except Exception:
                logfire.exception(f"Task {task_name} failed")
                raise

            elapsed = round(time.perf_counter() - start, 2)
            logfire.info(f"Task {task_name} completed", elapsed_s=elapsed, flag=flag)

        if flag:
            _console.print(f"[bold green]✓ Flag:[/] {flag}")
        return flag

    def _save_output(self, answer: Any) -> Path:
        """
        Zapisuje odpowiedź agenta do data/outputs/ (trwały ślad, nie cache —
        cache w .cache/ nadpisuje ten sam klucz przy każdym fetchu, tu zostaje
        historia każdego uruchomienia).

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
