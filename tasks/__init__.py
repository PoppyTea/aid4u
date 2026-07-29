"""
Auto-import wszystkich modułów zadań.

Dzięki temu dekoratory @task rejestrują klasy w TASK_REGISTRY
zanim run.py zapyta o dostępne zadania.

Gdy dodajesz nowe zadanie, dodaj import tutaj.
"""

import importlib
import pkgutil
from pathlib import Path


def _auto_import_tasks() -> None:
    tasks_dir = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(tasks_dir)]):
        if not module_info.ispkg:
            continue
        try:
            importlib.import_module(f"tasks.{module_info.name}")
        except Exception as e:
            import warnings

            warnings.warn(f"Could not import task '{module_info.name}': {e}")


_auto_import_tasks()
