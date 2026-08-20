"""
S03E05 savethem — rejestracja zadania w TASK_REGISTRY.

Import `solution` jest OBOWIĄZKOWY: `tasks/__init__.py` auto-importuje pakiety, ale
dekorator `@task` zadziała tylko wtedy, gdy moduł z klasą faktycznie się wczyta.
"""

from tasks.s03e05_savethem import solution  # noqa: F401

__all__ = ["solution"]
