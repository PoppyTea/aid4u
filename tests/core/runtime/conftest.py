"""
Wspólna izolacja dla testów `core/runtime/`.

Fixture był wcześniej lokalny dla `test_killswitch.py`; przeniesiony tutaj, gdy
`test_cost_budget.py` zaczął wołać `start_run()` bez niego i dotykał prawdziwego
`.run/` repozytorium. Duplikowanie go w każdym module byłoby zaproszeniem do
powtórzenia tego samego przeoczenia.
"""

from __future__ import annotations

import os

import pytest

from core.runtime import killswitch


@pytest.fixture(autouse=True)
def _isolated_run_dir(monkeypatch, tmp_path):
    """
    Przekierowuje ścieżki `.run/` na `tmp_path` i neutralizuje `os.setsid()`.

    Bez tego testy jednostkowe: (a) czytałyby i pisały PRAWDZIWY `.run/` repozytorium
    — kolizja z rzeczywistym przebiegiem uruchomionym równolegle, a przy zrównoleglonych
    workerach także między sobą; (b) wołałyby prawdziwy `os.setsid()` na PROCESIE
    pytest, odłączając go od sesji terminala w trakcie przebiegu testów. To realne
    efekty uboczne, nie teoretyczne.

    `TestPanicScriptKillsEntireProcessGroup` w `test_killswitch.py` świadomie omija ten
    fixture, licząc ścieżkę do prawdziwego `.run/` z `__file__` — `panic.sh` (bash)
    rozwiązuje ją względem swojej lokalizacji na dysku, więc monkeypatch Pythona jej
    nie dotyczy.
    """
    run_dir = tmp_path / ".run"
    monkeypatch.setattr(killswitch, "_RUN_DIR", run_dir)
    monkeypatch.setattr(killswitch, "_PGID_FILE", run_dir / "current.pgid")
    monkeypatch.setattr(killswitch, "_STOP_FILE", run_dir / "STOP")
    monkeypatch.setattr(os, "setsid", lambda: None)
    killswitch.end_run()
    yield
    killswitch.end_run()
