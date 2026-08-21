"""
S03E02 firmware — rejestracja zadania w TASK_REGISTRY.

Import `solution` jest OBOWIĄZKOWY: `tasks/__init__.py` auto-importuje pakiety, ale
dekorator `@task` zadziała tylko wtedy, gdy moduł z klasą faktycznie się wczyta.
"""

from tasks.s03e02_firmware import solution  # noqa: F401

__all__ = ["solution"]
