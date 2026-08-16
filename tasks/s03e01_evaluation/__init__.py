"""Package entry point — re-eksportuje EvaluationTask, żeby `import tasks` zarejestrował ją przez @task."""

from tasks.s03e01_evaluation.solution import EvaluationTask

__all__ = ["EvaluationTask"]
