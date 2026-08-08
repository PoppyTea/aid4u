"""Package entry point — re-exports DroneTask so `import tasks` registers it via @task."""

from tasks.s02e05_drone.solution import DroneTask

__all__ = ["DroneTask"]
