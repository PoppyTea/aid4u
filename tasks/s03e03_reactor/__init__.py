"""Package entry point — re-eksportuje ReactorTask, żeby `import tasks` zarejestrował ją przez @task."""

from tasks.s03e03_reactor.solution import ReactorTask

__all__ = ["ReactorTask"]
