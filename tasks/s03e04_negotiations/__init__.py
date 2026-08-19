"""
S03E04 negotiations — rejestracja zadania w TASK_REGISTRY.

Import `solution` jest tu OBOWIĄZKOWY: `tasks/__init__.py` auto-importuje
pakiety zadań, ale dekorator `@task` zadziała tylko wtedy, gdy moduł z klasą
faktycznie zostanie wczytany.
"""

from tasks.s03e04_negotiations import solution  # noqa: F401

__all__ = ["solution"]
