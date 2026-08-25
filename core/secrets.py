"""
Zarządzanie sekretami przez systemowy keyring.

Keyring jest bezpieczniejszy niż .env — klucze nie trafiają do historii gita.
Komplementarny do config.py, ale z więcej kontrolą nad operacjami keyring.

CLI examples:
    uv run python -m keyring set aid4u OPENAI_API_KEY
    uv run python -m keyring get aid4u OPENAI_API_KEY
    uv run python -m keyring delete aid4u OPENAI_API_KEY
"""

from __future__ import annotations

import logfire
import keyring
import os
import concurrent.futures
import threading
import time
from functools import lru_cache

# Headless/VPS bez uruchomionego keyring daemon (D-Bus secret service) potrafi
# zawiesić keyring.get_password() na zawsze zamiast rzucić wyjątek — złapane
# 2026-08-05: całe `uv run pytest` wisiało w nieskończoność na module-level
# setup_observability() w tasks/s01e03_proxy/server.py, bo _setup_logfire()
# czyta cfg.logfire_token -> Config.get() -> Config._from_keyring() ->
# _keyring_get_with_timeout() -> keyring.get_password(). Wątek daemon (nie
# ThreadPoolExecutor — jego atexit handler i tak by czekał na zawieszony
# wątek) + join(timeout) daje twardy limit czasu.
_KEYRING_TIMEOUT_SECONDS = 2.0

# Python nie potrafi bezpiecznie zabić zawieszonego wątku — jeśli keyring w
# danym środowisku jest trwale zepsuty (jak wyżej), KAŻDE kolejne wywołanie
# get()/list() odpalałoby nowy wątek i zostawiało go żywym na zawsze,
# akumulując je bez końca. Circuit breaker: po jednym timeout nie próbuj
# ponownie przez _KEYRING_BACKOFF_SECONDS — od razu fallback do env, zero
# nowych wątków, aż do wygaśnięcia okna.
_KEYRING_BACKOFF_SECONDS = 300.0
_keyring_unavailable_until: float | None = None


def _keyring_get_with_timeout(service: str, key: str, *, timeout: float = _KEYRING_TIMEOUT_SECONDS):
    """keyring.get_password(), ale nigdy nie wisi dłużej niż `timeout` sekund.

    Patrz komentarze przy _KEYRING_TIMEOUT_SECONDS i _KEYRING_BACKOFF_SECONDS
    dla pełnego kontekstu (incydent 2026-08-05 + circuit breaker).
    """
    global _keyring_unavailable_until

    if _keyring_unavailable_until is not None:
        if time.monotonic() < _keyring_unavailable_until:
            raise TimeoutError(f"keyring pominięty (circuit breaker aktywny) dla {key!r}")
        _keyring_unavailable_until = None  # okno backoff minęło, spróbuj ponownie

    box: dict[str, object] = {}

    def _worker() -> None:
        try:
            import keyring  # lokalnie, nie na poziomie modułu — patrz core/config.py

            box["value"] = keyring.get_password(service, key)
        except Exception as exc:  # noqa: BLE001 — przekazujemy dalej, nie tłumimy tutaj
            box["error"] = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        _keyring_unavailable_until = time.monotonic() + _KEYRING_BACKOFF_SECONDS
        raise TimeoutError(f"keyring.get_password({service!r}, {key!r}) przekroczył {timeout}s")
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box.get("value")

# Lista kluczy domyślnie sprawdzanych w SecretsManager.list()
default_keys: list[str] = [
    "APIKEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_PREMIUM",
    "OPENROUTER_API_KEY",
    "OPENROUTER_FREE_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LOGFIRE_TOKEN",
    "LOGFIRE_BASE_URL",
    "LM_STUDIO_KEY_AGENT",
    "LM_STUDIO_API_KEY_FIM",
    "VPS_HOST",
    "VPS_PORT_SSH",
    "VPS_PORT_MOSH",
    "VPS_PORT_TCP",
]


class SecretsManager:
    """Menadżer sekreów z systemowego keyring + fallback do .env."""

    def __init__(self, service_name: str = "aid4u"):
        self.service = service_name

    def get(self, key: str, *, required: bool = False) -> str | None:
        """Pobierz sekret z keyring, fallback do .env"""
        # 1. Spróbuj keyring (z timeoutem — patrz komentarz przy _KEYRING_TIMEOUT_SECONDS)
        try:
            value = _keyring_get_with_timeout(self.service, key)
            if value:
                return value
        except Exception:
            logfire.warning(f"Keyring error/timeout ({key})", exc_info=True)

        # 2. Spróbuj OS environment
        if value := os.getenv(key):
            return value

        if required:
            raise ValueError(
                f"❌ Secret not found: {key}\n"
                f"   Set via keyring:  uv run python -m keyring set {self.service} {key}\n"
                f"   Or in .env file:  {key}=value"
            )

        return None

    def set(self, key: str, value: str) -> None:
        """Przechowaj sekret w keyring."""
        keyring.set_password(self.service, key, value)
        logfire.info(f"Stored {key} in keyring")

    def delete(self, key: str) -> None:
        """Usuń sekret z keyring."""
        try:
            keyring.delete_password(self.service, key)
            logfire.info(f"Deleted {key} from keyring")
        except keyring.errors.PasswordDeleteError:
            logfire.warning(f"Key not found in keyring: {key}")

    def list(self, keys_list: list[str] = default_keys) -> dict[str, bool]:
        """Wyświetl dostępne sekrety (bez wartości!)."""
        # Nie możemy wylistować, ale możemy sprawdzić znane klucze

        def _check_key(key: str) -> tuple[str, bool]:
            try:
                exists = _keyring_get_with_timeout(self.service, key) is not None
                return key, exists
            except Exception:
                return key, False

        with concurrent.futures.ThreadPoolExecutor() as executor:
            return dict(executor.map(_check_key, keys_list))

    def info(self) -> dict:
        """Informacje o aktualnym keyring backend."""
        backend = keyring.get_keyring()
        return {
            "backend": str(backend.__class__.__name__),
            "service": self.service,
            "available_secrets": self.list(),
        }


@lru_cache(maxsize=1)
def get_secrets() -> SecretsManager:
    """Zwraca singleton SecretsManager."""
    return SecretsManager()
