"""
Singleton konfiguracji projektu.

Klucze API pobierane z OS keychain (keyring), z fallbackiem do .env.
Keyring jest bezpieczniejszy niż .env — klucze nie trafiają do historii gita.

Ustawianie kluczy przez keyring:
    keyring set aid4u APIKEY
    keyring set aid4u ANTHROPIC_API_KEY

Fallback do .env (przydatny na VPS gdzie keyring może być niedostępny):
    cp .env.example .env && vim .env
"""

from __future__ import annotations

import os
import zoneinfo
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ─── Constants configuration ───────────────────────────────────────────────────

_KEYRING_SERVICE = "aid4u"
WARSAW_TZ = zoneinfo.ZoneInfo("Europe/Warsaw")

GEMINI_TIERS = frozenset({"free", "premium"})
"""Tiery rozliczeniowe Gemini — osobne projekty Google Cloud, osobne klucze API."""

GEMINI_TIER_DEFAULT = "free"


class Config:
    """Singleton. Klucze z keyring, fallback do env."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def get(self, key: str, *, required: bool = True) -> str:
        if key not in self._cache:
            value = self._from_keyring(key) or os.getenv(key, "")
            if not value and required:
                raise ValueError(
                    f"Brak klucza: {key}\n"
                    f"Ustaw przez keyring:  keyring set {_KEYRING_SERVICE} {key}\n"
                    f"Lub dodaj do .env:    {key}=wartość"
                )
            self._cache[key] = value
        return self._cache[key]

    def _from_keyring(self, key: str) -> str:
        # Headless/VPS bez keyring daemon może WISIEĆ na get_password() zamiast
        # rzucić wyjątek — _keyring_get_with_timeout() ogranicza to do kilku
        # sekund (patrz jego docstring w core/secrets.py dla pełnego kontekstu
        # zdarzenia z 2026-08-05: to zawieszało cały `uv run pytest`).
        try:
            from core.secrets import _keyring_get_with_timeout

            return _keyring_get_with_timeout(_KEYRING_SERVICE, key) or ""
        except Exception:
            return ""

    # ─── Convenience properties ───────────────────────────────────────────────

    @property
    def apikey(self) -> str:
        return self.get("APIKEY")

    @property
    def anthropic_key(self) -> str:
        return self.get("ANTHROPIC_API_KEY")

    @property
    def openai_key(self) -> str:
        return self.get("OPENAI_API_KEY", required=False)

    @property
    def openrouter_key(self) -> str:
        return self.get("OPENROUTER_API_KEY", required=False)

    @property
    def gemini_key(self) -> str:
        """Klucz Gemini dla tieru 'free' (projekt Google Cloud BEZ billingu)."""
        return self.get("GEMINI_API_KEY", required=False)

    @property
    def gemini_key_premium(self) -> str:
        """
        Klucz Gemini dla tier 'premium' (płatny — osobny projekt Google Cloud Z billingiem).

        Free i paid tier Gemini API są własnością różnych projektów Google Cloud —
        jeden klucz API nie może obsłużyć obu. Stąd dwa osobne klucze zamiast jednego
        z przełącznikiem. Szczegóły: strategy/llm-selection.md.
        """
        return self.get("GEMINI_API_KEY_PREMIUM", required=False)

    def gemini_key_for_tier(self, tier: str = GEMINI_TIER_DEFAULT) -> str:
        """
        Zwraca klucz Gemini dla podanego tieru rozliczeniowego (`free` | `premium`).

        Waliduje wprost, zamiast traktować wszystko poza `premium` jako darmowe — przy
        cichym fallbacku literówka w nazwie tieru dawała klucz darmowy i objawiała się
        dopiero jako 429 albo 404 w środku przebiegu, w miejscu niezwiązanym z przyczyną.
        """
        if tier not in GEMINI_TIERS:
            raise ValueError(
                f"Nieznany tier Gemini: {tier!r}. Dopuszczalne: {', '.join(sorted(GEMINI_TIERS))}."
            )
        return self.gemini_key_premium if tier == "premium" else self.gemini_key

    @property
    def langfuse_public_key(self) -> str:
        return self.get("LANGFUSE_PUBLIC_KEY", required=False)

    @property
    def langfuse_secret_key(self) -> str:
        return self.get("LANGFUSE_SECRET_KEY", required=False)

    @property
    def langfuse_host(self) -> str:
        return os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    @property
    def logfire_token(self) -> str:
        # Write token tylko — Read token NIE jest potrzebny.
        # Utwórz na: https://logfire.pydantic.dev → projekt → Settings → Write Tokens
        return self.get("LOGFIRE_TOKEN", required=False)

    @property
    def langfuse_environment(self) -> str:
        # Oddziela trace z różnych środowisk (dev/prod) w Langfuse UI.
        # Ustaw przez env var: LANGFUSE_TRACING_ENVIRONMENT=dev
        return os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "dev")

    @property
    def hub_base_url(self) -> str:
        return os.getenv("HUB_BASE_URL", "https://hub.ag3nts.org")

    @property
    def vps_host(self) -> str:
        return self.get("VPS_HOST", required=False)


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Zwraca singleton Config. Bezpieczne do wielokrotnego wywoływania."""
    return Config()
