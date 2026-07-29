#!/usr/bin/env python3
"""Przełącza aid4u między "learning mode" (edukacja, TDD-first, pełny ceremoniał) a
"efficiency mode" (szybkość/skuteczność zdobywania flag, do 20/25) — nieddestrukcyjnie.

Każdy tryb ma swoją "szafę" (closet) w .help/learning-vs-efficiency/<mode>/, ze strukturą
katalogów lustrzaną względem realnych ścieżek w repo. Przełączanie ZAWSZE najpierw chowa
aktualną aktywną treść do przeciwnej szafy, dopiero potem wyciąga docelową — nic nigdy nie
ginie, tylko wędruje między "aktywne miejsce" a "szafa".

CLAUDE.md/AGENTS.md nie wymagają osobnej synchronizacji tutaj — CLAUDE.md w zarządzanych
folderach to symlink do AGENTS.md, więc podąża za treścią automatycznie.

Użycie:
    python3 learning_mode_on_off.py status
    python3 learning_mode_on_off.py on     # przywróć tryb nauki
    python3 learning_mode_on_off.py off    # przełącz na efficiency mode
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../00_aid4u
CLOSET_ROOT = PROJECT_ROOT / ".help" / "learning-vs-efficiency"
STATE_FILE = CLOSET_ROOT / ".current_mode"

# Ścieżki względem PROJECT_ROOT zarządzane przez toggle. Dodaj tu nową ścieżkę razem z
# zainicjowaniem obu wersji (learning/efficiency) w odpowiednich szafach, inaczej switch_to()
# tylko ostrzeże i pominie plik.
MANAGED_FILES = [
    "aid4u/AGENTS.md",
    "aid4u/tasks/AGENTS.md",
    "aid4u/strategy/learning-protocol.md",
]


def _read_state() -> str:
    if STATE_FILE.exists():
        return STATE_FILE.read_text(encoding="utf-8").strip()
    return "efficiency"


def _write_state(mode: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(mode, encoding="utf-8")


def switch_to(target_mode: str) -> None:
    assert target_mode in ("learning", "efficiency")
    current_mode = _read_state()
    if current_mode == target_mode:
        print(f"Już jesteś w trybie: {target_mode}. Nic do zrobienia.")
        return

    outgoing_closet = CLOSET_ROOT / f"{current_mode}-mode"
    incoming_closet = CLOSET_ROOT / f"{target_mode}-mode"

    for relpath in MANAGED_FILES:
        active_path = PROJECT_ROOT / relpath
        outgoing_path = outgoing_closet / relpath
        incoming_path = incoming_closet / relpath

        if active_path.exists():
            outgoing_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(active_path, outgoing_path)
            print(f"  schowano: {relpath} -> szafa '{current_mode}'")

        if incoming_path.exists():
            active_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(incoming_path, active_path)
            print(f"  przywrócono: {relpath} <- szafa '{target_mode}'")
        else:
            print(f"  UWAGA: brak zapisanej wersji '{target_mode}' dla {relpath} — pominięto")

    _write_state(target_mode)
    print(f"\nTryb aktywny: {target_mode}")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off", "status"):
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "status":
        print(f"Aktywny tryb: {_read_state()}")
        return

    # "on" = włącz tryb nauki (learning), "off" = wyłącz tryb nauki (przełącz na efficiency)
    target = "learning" if command == "on" else "efficiency"
    switch_to(target)


if __name__ == "__main__":
    main()
