"""
Kill switch — awaryjne zatrzymanie przebiegu, niezależne od współpracy agenta.

Trzy warstwy (patrz `core/AGENTS.md` dla pełnego uzasadnienia projektowego):

- **Warstwa 0 (OS-level, `PANIC_BUTTON`)** — `start_run()` odłącza proces do własnej
  grupy (`os.setsid()`), PGID ląduje w `.run/current.pgid`. `scripts/panic.sh`
  (czysty bash, bez zależności od Pythona) zabija CAŁĄ grupę sygnałem
  SIGTERM→SIGKILL — działa nawet gdy środowisko Pythona jest rozwalone. To jest
  ostateczna gwarancja; ta klasa jej nie implementuje, tylko przygotowuje grunt
  (plik z PGID).
- **Warstwa 1 (kooperacyjna, graceful)** — plik-wartownik `.run/STOP`.
  `check_abort()`, wywoływane w bezpiecznych punktach pętli (start iteracji, przed
  tool callem, przed submit), rzuca `AbortRun` — czyste zamknięcie zamiast
  ubicia procesu.
- **Warstwa 2 (budżety)** — `start_run(max_seconds=...)` ustawia twardy limit
  wall-clock na cały przebieg, sprawdzany przy każdym `check_abort()`.
  `truncate_tool_result()` to osobny mechanizm per-call (NIE przerywa przebiegu,
  tylko koryguje pojedynczy wynik narzędzia) — chroni przed np. `cat` dużego pliku
  zalewającym kontekst (udokumentowana strata $5-10 w komentarzach kursu S03E02).

Budżet kosztu/tokenów jest świadomie NIEZAIMPLEMENTOWANY w tej wersji "basic" —
wymagałby ekspozycji bieżącego kosztu z `CostTrackMiddleware` w trakcie przebiegu,
nie tylko na końcu. Zostawione jako przyszłe rozszerzenie `RunBudget`.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

_RUN_DIR = Path(".run")
_PGID_FILE = _RUN_DIR / "current.pgid"
_STOP_FILE = _RUN_DIR / "STOP"

# ~5k tokenów — na tyle duże, żeby nie ucinać normalnych odpowiedzi API, na tyle
# małe, żeby jeden `cat` dużego pliku nie wysadził kontekstu ani budżetu.
DEFAULT_MAX_TOOL_RESULT_BYTES = 20_000


class AbortRun(Exception):
    """Rzucane, gdy przebieg powinien się zatrzymać (Warstwa 1 lub 2). Łapane w `BaseTask.run()`."""


@dataclass
class RunBudget:
    """Twarde limity na cały przebieg `solve()`. Dziś tylko wall-clock — patrz docstring modułu."""

    max_seconds: float | None = None
    _started_at: float = field(default_factory=time.monotonic, init=False, repr=False)

    def check_time(self) -> None:
        """Rzuca `AbortRun`, jeśli przebieg trwa dłużej niż `max_seconds`. No-op gdy limit nieustawiony."""
        if self.max_seconds is None:
            return
        elapsed = time.monotonic() - self._started_at
        if elapsed > self.max_seconds:
            raise AbortRun(f"Przekroczono budżet czasu: {elapsed:.1f}s > {self.max_seconds}s.")


_active_budget: RunBudget | None = None


def start_run(*, max_seconds: float | None = None) -> None:
    """
    Wywoływane raz na początku `BaseTask.run()`. Instaluje grupę procesów (Warstwa 0),
    czyści wartownika `.run/STOP` z ewentualnego poprzedniego przebiegu (patrz
    ostrzeżenie w docstringu `request_stop()` — bez tego nowy przebieg mógłby ubić się
    natychmiast na pierwszym `check_abort()`) i, jeśli podano, aktywuje budżet
    wall-clock (Warstwa 2).

    `max_seconds` sprawdzane przez `is not None`, nie przez truthy-check — `0` to
    poprawny (choć ekstremalny) budżet "przerwij natychmiast", nie "brak budżetu".
    Ujemne wartości nie mają sensu i są odrzucane.
    """
    global _active_budget
    # Walidacja PRZED jakimikolwiek efektami ubocznymi (grupa procesów, plik PGID) —
    # inaczej ValueError zostawia osierocony .run/current.pgid na dysku (start_run()
    # jest wołane poza try/finally w BaseTask.run(), więc end_run() się nie odpali).
    if max_seconds is not None and max_seconds < 0:
        raise ValueError(f"max_seconds musi być >= 0, dostano {max_seconds}.")
    _install_process_group()
    _STOP_FILE.unlink(missing_ok=True)
    _active_budget = RunBudget(max_seconds=max_seconds) if max_seconds is not None else None


def end_run() -> None:
    """Sprząta `.run/` po zakończeniu przebiegu (sukces, błąd, abort) — wywołuj w `finally`."""
    global _active_budget
    _active_budget = None
    for f in (_PGID_FILE, _STOP_FILE):
        f.unlink(missing_ok=True)


def request_stop() -> None:
    """
    Warstwa 1 — zapisuje wartownika `.run/STOP`. Wywoływane przez `run.py panic
    --graceful`.

    ⚠️ Jeśli wywołane gdy żaden przebieg nie jest aktywny (np. podwójne wywołanie,
    albo `panic --graceful` bez uruchomionego zadania), plik zostaje osierocony —
    `start_run()` czyści go na starcie KOLEJNEGO przebiegu właśnie z tego powodu,
    żeby stary wartownik nie ubił nowego zadania na pierwszym `check_abort()`.
    """
    _RUN_DIR.mkdir(exist_ok=True)
    _STOP_FILE.touch()


def check_abort() -> None:
    """
    Sprawdza obie miękkie warstwy (STOP + budżet czasu) i rzuca `AbortRun` przy
    przekroczeniu którejkolwiek. Wywołuj w bezpiecznych punktach: start iteracji
    pętli agenta, przed każdym tool callem, przed `hub.submit()`.
    """
    if _STOP_FILE.exists():
        raise AbortRun("Przerwano przez .run/STOP (graceful stop).")
    if _active_budget is not None:
        _active_budget.check_time()


def current_pgid_file() -> Path:
    """Ścieżka do pliku z PGID bieżącego przebiegu — używane przez `run.py panic` i testy."""
    return _PGID_FILE


def truncate_tool_result(result: str, *, max_bytes: int = DEFAULT_MAX_TOOL_RESULT_BYTES) -> str:
    """
    Warstwa 2, zasięg per-call — koryguje pojedynczy wynik narzędzia, NIE przerywa
    przebiegu. Ucina wynik przekraczający `max_bytes` i jawnie to oznacza dla modelu
    (zamiast po cichu zalewać kontekst pełną treścią).

    Zwrócony string mieści się w `max_bytes` CAŁKOWICIE, licząc znacznik obcięcia —
    znacznik jest budowany najpierw, a treść przycinana do pozostałego miejsca, nie
    doklejana po fakcie (inaczej `max_bytes` byłby limitem tylko na samą treść, nie
    na realny rozmiar tego co trafia do kontekstu modelu).
    """
    encoded = result.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return result

    marker = f"\n\n[OBCIĘTO: wynik miał {len(encoded)} B, limit {max_bytes} B]".encode("utf-8")
    budget_for_content = max(0, max_bytes - len(marker))
    truncated = encoded[:budget_for_content].decode("utf-8", errors="ignore")
    return truncated + marker.decode("utf-8")


def _install_process_group() -> None:
    """
    Odłącza bieżący proces do własnej grupy (`setsid`) i zapisuje PGID do pliku, żeby
    `scripts/panic.sh` miało co zabić. No-op poza POSIX (Windows nie ma grup procesów
    w tym sensie) i no-op, jeśli proces już jest liderem sesji (np. powtórne wywołanie
    w tym samym procesie, typowe w testach).
    """
    if os.name != "posix":
        return
    try:
        os.setsid()
    except OSError:
        pass
    _RUN_DIR.mkdir(exist_ok=True)
    _PGID_FILE.write_text(str(os.getpgrp()))
