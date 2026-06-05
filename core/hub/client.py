"""
Repository pattern — HubClient.

Cały dostęp do hub.ag3nts.org przez tę klasę.
Izoluje zadania od szczegółów HTTP, retry i parsowania flag.
"""
from __future__ import annotations

import re
from typing import Any

import httpx
import logfire
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import get_config

_FLAG_PATTERN = re.compile(r"\{FLG:[^}]+\}")


class HubClient:
    """Repozytorium — wszystkie zapytania do hubu przez tę klasę."""

    def __init__(self) -> None:
        cfg = get_config()
        self._apikey = cfg.apikey
        self._base_url = cfg.hub_base_url
        # httpx jest auto-instrumentowany przez Logfire po setup_observability()
        self._http = httpx.Client(timeout=30.0)

    # ─── Submit ──────────────────────────────────────────────────────────────

    def submit(self, task: str, answer: Any) -> dict:
        """
        POST /verify — standardowe zgłoszenie odpowiedzi.

        Returns:
            Pełna odpowiedź z hubu jako dict.
            Sprawdź get_flag(response) aby wyciągnąć flagę.
        """
        payload = {"apikey": self._apikey, "task": task, "answer": answer}
        logfire.info(f"Submitting task {task}", answer_preview="***REDACTED***")

        response = self._http.post(f"{self._base_url}/verify", json=payload)
        response.raise_for_status()
        result = response.json()

        flag = self.get_flag(result)
        if flag:
            logfire.info(f"Flag received for {task}", flag=flag)
        else:
            logfire.warning(f"No flag in response for {task}", response=result)

        return result

    # ─── Data fetching ───────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def get_data(self, path: str) -> bytes:
        """GET /data/{apikey}/{path} — z retry dla niestabilnych połączeń."""
        url = f"{self._base_url}/data/{self._apikey}/{path}"
        response = self._http.get(url)
        response.raise_for_status()
        return response.content

    @retry(stop=stop_after_attempt(8), wait=wait_exponential(min=3, max=60))
    def get_data_503_tolerant(self, path: str) -> bytes:
        """
        GET z tolerancją na błędy 503 (celowe przeciążenie, np. zadanie 'railway').
        Używa agresywniejszego retry z dłuższym backoffem.
        """
        url = f"{self._base_url}/data/{self._apikey}/{path}"
        response = self._http.get(url)
        if response.status_code == 503:
            raise httpx.HTTPStatusError(
                "503 — retry", request=response.request, response=response
            )
        response.raise_for_status()
        return response.content

    def post_api(self, path: str, payload: dict) -> dict:
        """POST do dowolnego endpointu hubu (np. /api/zmail, /api/packages)."""
        payload = {**payload, "apikey": self._apikey}
        response = self._http.post(f"{self._base_url}{path}", json=payload)
        response.raise_for_status()
        return response.json()

    # ─── Flag extraction ─────────────────────────────────────────────────────

    def get_flag(self, response: dict) -> str | None:
        """Wyciąga flagę {FLG:...} z dowolnego pola odpowiedzi."""
        # Sprawdź typowe pola
        for key in ("message", "msg", "answer", "flag", "note"):
            value = str(response.get(key, ""))
            match = _FLAG_PATTERN.search(value)
            if match:
                return match.group()

        # Fallback: przeszukaj całą odpowiedź jako string
        full = str(response)
        match = _FLAG_PATTERN.search(full)
        return match.group() if match else None

    def __del__(self) -> None:
        try:
            self._http.close()
        except Exception:
            pass
