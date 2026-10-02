"""
Kontrakt `--dry-run`: każde zadanie musi mieć świadomą odpowiedź na pytanie
„co ta flaga u mnie robi".

Powód istnienia jest empiryczny, nie teoretyczny. Kontrakt istniał od dawna, ale wyłącznie
jako komentarz w `tasks/s02e05_drone/solution.py` — i przez to rozjechał się dwanaście
razy: sześć zadań pilnowało `self.dry_run`, siedem nie, a pomoc `run.py` obiecywała
wszystkim „pokaż odpowiedź bez wysyłania". Rutyna `contract-audit` zgłosiła to jako
AID-132 dopiero po piątym zadaniu z rzędu bez osłony.

Sedno testu `test_zadanie_wolajace_hub_deklaruje_tryb`: **nie sprawdza zachowania, tylko
czy ktoś w ogóle podjął decyzję.** Wolno wołać hub w `solve()` — trzeba to zadeklarować.
Dziedziczona wartość domyślna, nigdy nietknięta, jest jedyną rzeczą, którą uznaje za błąd.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

# Import pakietu `tasks` MUSI poprzedzić odczyt rejestru: `TASK_REGISTRY` zapełnia się
# dopiero przy auto-imporcie zadań, a parametryzacja czyta go w czasie zbierania testów.
# Bez tego cała parametryzacja rozwija się do zera przypadków i test przechodzi, nie
# sprawdziwszy niczego — najgorszy możliwy tryb porażki dla testu-strażnika.
import tasks  # noqa: F401
from core.tasks import (
    DRY_RUN_LIVE,
    DRY_RUN_MODES,
    DRY_RUN_SAFE,
    DRY_RUN_UNSAFE,
    TASK_REGISTRY,
    BaseTask,
)

# Wywołania zmieniające stan po stronie huba albo wymagające żywej rozmowy.
# `get_data`/`get_public` są celowo pominięte — to pobranie danych wejściowych,
# które dzieje się w `fetch_data()` jeszcze przed `solve()` i niczego nie zmienia.
_HUB_CALLS = {"submit", "post_api"}

# Pliki obok rozwiązania, które nie leżą na ścieżce `run.py solve`: sondy uruchamiane
# ręcznie i skrypty pomocnicze. Wołają hub z definicji i nie mówią nic o trybie zadania.
_OFF_PATH = ("test_", "probe", "discover", "__init__")


def _task_sources(cls: type[BaseTask]) -> list[pathlib.Path]:
    """Pliki pakietu zadania leżące na ścieżce `solve()`."""
    folder = pathlib.Path(inspect.getfile(cls)).parent
    return [
        f
        for f in sorted(folder.rglob("*.py"))
        if not any(f.name.startswith(prefix) for prefix in _OFF_PATH) and "scripts" not in f.parts
    ]


def _calls_hub(cls: type[BaseTask]) -> bool:
    """Czy którykolwiek plik zadania woła hub w sposób wymagający decyzji o `--dry-run`."""
    for path in _task_sources(cls):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in _HUB_CALLS:
                    return True
    return False


def _declares_mode(cls: type[BaseTask]) -> bool:
    """Czy klasa ma WŁASNE przypisanie `dry_run_mode`, a nie tylko dziedziczone."""
    return "dry_run_mode" in vars(cls)


def _guards_dry_run(cls: type[BaseTask]) -> bool:
    """Czy zadanie samo sprawdza `self.dry_run` przed wywołaniem huba."""
    return any("dry_run" in path.read_text(encoding="utf-8") for path in _task_sources(cls))


@pytest.mark.parametrize("name", sorted(TASK_REGISTRY))
def test_tryb_jest_z_dozwolonego_zbioru(name: str) -> None:
    """Literówka w deklaracji cicho zdejmowałaby ochronę, więc jest błędem."""
    assert TASK_REGISTRY[name].dry_run_mode in DRY_RUN_MODES


@pytest.mark.parametrize("name", sorted(TASK_REGISTRY))
def test_zadanie_wolajace_hub_deklaruje_tryb(name: str) -> None:
    """
    Zadanie wołające hub poza `fetch_data()` musi mieć ŚWIADOMĄ odpowiedź o `--dry-run`.

    Dwie drogi są równoprawne: własny strażnik `if self.dry_run:` albo jawna deklaracja
    `dry_run_mode`. Test odrzuca wyłącznie trzecią możliwość — milczenie, czyli wartość
    dziedziczoną, której autor nigdy nie rozważył. To ona wyprodukowała AID-132.
    """
    cls = TASK_REGISTRY[name]
    if not _calls_hub(cls):
        return
    assert _declares_mode(cls) or _guards_dry_run(cls), (
        f"{name} woła hub w ścieżce solve(), ale nie deklaruje `dry_run_mode` ani nie "
        f"sprawdza `self.dry_run`. Wybierz jedno — patrz core/AGENTS.md, kontrakt --dry-run."
    )


class TestZachowanieRunPrzyDryRun:
    """`BaseTask._announce_dry_run()` — co użytkownik dostaje przed startem."""

    def _task(self, mode: str) -> BaseTask:
        class _Probe(BaseTask):
            dry_run_mode = mode

            def solve(self, data: object) -> str:
                return "x"

        return _Probe(hub=object(), llm=object(), dry_run=True)  # type: ignore[arg-type]

    def test_safe_przechodzi_bez_ostrzezenia(self) -> None:
        assert self._task(DRY_RUN_SAFE)._announce_dry_run("t") is True

    def test_live_przechodzi_ale_ostrzega(self, capsys: pytest.CaptureFixture[str]) -> None:
        """
        Przebieg się odbywa — bo dla zadań protokołowych to jedyny sposób poznania
        odpowiedzi — ale bez udawania, że nic się nie dzieje po stronie huba.
        """
        assert self._task(DRY_RUN_LIVE)._announce_dry_run("t") is True
        assert "NIE jest suchym przebiegiem" in capsys.readouterr().out

    def test_unsafe_odmawia(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Skutki nieodwracalne: próbny przebieg byłby przebiegiem prawdziwym."""
        assert self._task(DRY_RUN_UNSAFE)._announce_dry_run("t") is False
        assert "odmówiony" in capsys.readouterr().out

    def test_nieznany_tryb_przerywa(self) -> None:
        with pytest.raises(ValueError, match="nieznany dry_run_mode"):
            self._task("byle co")._announce_dry_run("t")


class TestZnaneDeklaracje:
    """Regresja: zadania, w których tryb wynika ze zmierzonych skutków ubocznych."""

    def test_firmware_odmawia_bo_mutuje_zdalna_vm(self) -> None:
        """`editline` i `rm` na żywej VM, ban za błędny ruch, `reboot` kasuje postęp."""
        assert TASK_REGISTRY["s03e02"].dry_run_mode == DRY_RUN_UNSAFE

    @pytest.mark.parametrize("name", ["s04e03", "s04e04", "s04e05", "s05e03", "s05e04"])
    def test_zadania_protokolowe_sa_live(self, name: str) -> None:
        """Odpowiedzi nie da się policzyć offline — powstaje z odpowiedzi huba."""
        assert TASK_REGISTRY[name].dry_run_mode == DRY_RUN_LIVE
