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

import keyring
import os
from pathlib import Path
from typing import Optional
from functools import lru_cache

# Lista kluczy domyślnie sprawdzanych w SecretsManager.list()
default_keys:list[str] = [
    "APIKEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
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
    "VPS_PORT_TCP"
]

class SecretsManager:
    """Menadżer sekreów z systemowego keyring + fallback do .env."""

    def __init__(self, service_name: str = "aid4u"):
        self.service = service_name

    def get(self, key: str, *, required: bool = False) -> Optional[str]:
        """Pobierz sekret z keyring, fallback do env, potem .env."""
        # 1. Spróbuj keyring
        try:
            value = keyring.get_password(self.service, key)
            if value:
                return value
        except Exception as e:
            print(f"⚠️  Keyring error ({key}): {e}")

        # 2. Spróbuj OS environment
        if value := os.getenv(key):
            return value

        # 3. Spróbuj .env file
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
        print(f"✓ Stored {key} in keyring")

    def delete(self, key: str) -> None:
        """Usuń sekret z keyring."""
        try:
            keyring.delete_password(self.service, key)
            print(f"✓ Deleted {key} from keyring")
        except keyring.errors.PasswordDeleteError:
            print(f"⚠️  Key not found in keyring: {key}")


    def list(self, keys_list: list[str]=default_keys) -> dict[str, bool]:
        """Wyświetl dostępne sekrety (bez wartości!)."""
        # Nie możemy wylistować, ale możemy sprawdzić znane klucze

        result = {}
        for key in keys_list:
            try:
                exists = keyring.get_password(self.service, key) is not None
                result[key] = exists
            except Exception:
                result[key] = False

        return result

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
