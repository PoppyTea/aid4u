"""
Lokalny cache danych z hubu.

Cel: przy TDD uruchamiasz kod wielokrotnie.
Bez cache każde uruchomienie pobiera dane z sieci — wolno i drogie.
Z cache — pierwsze pobranie zapisuje do .cache/, kolejne czytają z dysku.

Użycie w zadaniu:
    raw = self.cache.get_or_fetch(
        "people.csv",
        lambda: self.hub.get_data("people.csv"),
    )

Wyczyszczenie cache:
    rm -rf .cache/
"""

from __future__ import annotations

import hashlib
from pathlib import Path


_CACHE_ROOT = Path(".cache")


class LocalCache:
    """Prosty cache klucz→bajty oparty na systemie plików."""

    def __init__(self, subdir: str = "default") -> None:
        self._dir = _CACHE_ROOT / subdir
        self._dir.mkdir(parents=True, exist_ok=True)
        self.last_key: str | None = None
        """
        Klucz ostatniego get_or_fetch — używany przez BaseTask do nazwania pliku w data/run-
        history/.
        """

    def get(self, key: str) -> bytes | None:
        """Zwraca cached dane lub None jeśli brak."""
        path = self._key_to_path(key)
        return path.read_bytes() if path.exists() else None

    def set(self, key: str, data: bytes) -> None:
        """Zapisuje dane do cache."""
        self._key_to_path(key).write_bytes(data)

    def get_or_fetch(self, key: str, fetch_fn) -> bytes:
        """
        Zwraca dane z cache lub pobiera przez fetch_fn i cachuje.

        Args:
            key: Unikalny klucz (np. nazwa pliku lub URL)
            fetch_fn: Callable() → bytes wywoływany tylko przy cache miss

        Example:
            data = cache.get_or_fetch(
                "electricity.png",
                lambda: hub.get_data("electricity.png"),
            )
        """
        self.last_key = key
        cached = self.get(key)
        if cached is not None:
            return cached
        data = fetch_fn()
        self.set(key, data)
        return data

    def invalidate(self, key: str) -> None:
        """Usuwa wpis z cache (np. po resecie planszy w zadaniu electricity)."""
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()

    def _key_to_path(self, key: str) -> Path:
        safe_name = hashlib.sha256(key.encode()).hexdigest()
        return self._dir / safe_name
