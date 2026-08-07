"""Package entry point — re-exports MailboxTask so `import tasks` registers it via @task."""

from tasks.s02e04_mailbox.solution import MailboxTask

__all__ = ["MailboxTask"]
