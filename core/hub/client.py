"""
Repository pattern — HubClient.

Cały dostęp do hub.ag3nts.org przez tę klasę.
Izoluje zadania od szczegółów HTTP, retry i parsowania flag.
"""

from __future__ import annotations
from core.observability.decorators import langfuse_observe

import re
import time
from typing import Any

import httpx
import logfire
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from core.config import get_config
from core.hub.throttle import OutgoingThrottle

_FLAG_PATTERN = re.compile(r"\{FLG:[^}]+\}")

# /verify na niektórych zadaniach (np. "railway") celowo symuluje przeciążenie
# (503, bez sensownego czasu oczekiwania) i egzekwuje bardzo restrykcyjny rate
# limit (429). Hub NIE ustawia standardowego nagłówka Retry-After — czas
# oczekiwania jest w polu `retry_after` ciała odpowiedzi. Zbyt wczesny kolejny
# request dokłada rosnącą karę (`penalty_seconds`), więc margines jest ważniejszy
# niż szybkość.
_VERIFY_OUTAGE_WAIT_S = 5.0
_VERIFY_RATE_LIMIT_MARGIN_S = 2.0
_VERIFY_MAX_ATTEMPTS = 20


def _is_retryable_http_error(exc: BaseException) -> bool:
    """4xx to trwały błąd (zły path) — nie ma sensu go powtarzać, w przeciwieństwie do 5xx/timeoutów."""
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


def _is_retryable_transport_error(exc: BaseException) -> bool:
    """
    Awarie warte ponowienia na `/api/*`: 5xx i błędy transportu.

    **429 celowo NIE jest tutaj** (zmiana z 2026-08-20, AID-46). Endpointy `/api/*`
    nie zwracają `retry_after` w ciele (inaczej niż `/verify`), a intel do `s03e02`
    podejrzewa, że każde 429 przedłuża okno blokady — więc ślepy backoff w pętli
    dokładał kary zamiast je przeczekać. Rate limit obsługuje teraz `post_api()`
    jednym odczekaniem przez `OutgoingThrottle`.
    """
    return _is_retryable_http_error(exc)


class HubClient:
    """Repozytorium — wszystkie zapytania do hubu przez tę klasę."""

    def __init__(self) -> None:
        """Ładuje apikey/base_url z configu i tworzy współdzielony klient httpx."""
        cfg = get_config()
        self._apikey = cfg.apikey
        self._base_url = cfg.hub_base_url
        # httpx jest auto-instrumentowany przez Logfire po setup_observability()
        self._http = httpx.Client(timeout=30.0)
        # Jeden throttle na klienta — limit huba jest per klucz API, nie per endpoint,
        # więc liczenie odstępu osobno dla /api/shell i /api/toolsearch by go łamało.
        self._throttle = OutgoingThrottle()

    # ─── Submit ──────────────────────────────────────────────────────────────

    def submit(self, task: str, answer: Any) -> dict:
        """
        POST /verify — zgłoszenie odpowiedzi (finalnej albo jednego kroku
        wieloetapowego protokołu, np. zadanie "railway" gdzie każda akcja
        idzie przez ten sam endpoint).

        Toleruje 503 (symulowane przeciążenie) i 429 (rate limit) — patrz
        _post_verify_resilient(). Inne błędy HTTP (4xx/5xx) propagują się
        natychmiast, bez retry.

        Returns:
            Pełna odpowiedź z hubu jako dict.
            Sprawdź get_flag(response) aby wyciągnąć flagę.
        """
        payload = {"apikey": self._apikey, "task": task, "answer": answer}
        answer_str = str(answer)
        preview = (
            (f"{answer_str[:3]}****{answer_str[-3:]}")
            + (f" <{type(answer).__name__}>")
            + (f" (len: {len(answer)})" if hasattr(answer, "__len__") else "")
        )
        logfire.info(f"Submitting task {task}", answer_preview=preview)

        result = self._post_verify_resilient(payload, task)

        flag = self.get_flag(result)
        if flag:
            logfire.info(f"Flag received for {task}", flag=flag)
        else:
            logfire.warning(f"No flag in response for {task}", response=result)

        return result

    def _post_verify_resilient(self, payload: dict, task: str) -> dict:
        """POST /verify z retry na 503 (przeciążenie) i 429 (rate limit)."""
        for attempt in range(1, _VERIFY_MAX_ATTEMPTS + 1):
            response = self._http.post(f"{self._base_url}/verify", json=payload)

            if response.status_code == 503:
                logfire.info(f"Hub 503 (symulowane przeciążenie) dla {task}, retry", attempt=attempt)
                time.sleep(_VERIFY_OUTAGE_WAIT_S)
                continue

            if response.status_code == 429:
                wait_s = self._parse_retry_after(response) + _VERIFY_RATE_LIMIT_MARGIN_S
                logfire.info(f"Hub 429 rate limit dla {task}, czekam {wait_s}s", attempt=attempt)
                time.sleep(wait_s)
                continue

            if response.status_code >= 400:
                logfire.error("Hub rejected submission", status=response.status_code, body=response.text)
            response.raise_for_status()
            return response.json()

        raise RuntimeError(f"submit({task}): wyczerpano {_VERIFY_MAX_ATTEMPTS} prób (503/429)")

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float:
        """Odczytuje `retry_after` z ciała 429 — odpornie na nie-JSON/brakujące/nienumeryczne body."""
        try:
            body = response.json()
        except ValueError:
            return _VERIFY_OUTAGE_WAIT_S
        if not isinstance(body, dict):
            return _VERIFY_OUTAGE_WAIT_S
        try:
            return max(float(body.get("retry_after", _VERIFY_OUTAGE_WAIT_S)), 0.0)
        except (TypeError, ValueError):
            return _VERIFY_OUTAGE_WAIT_S

    # ─── Data fetching ───────────────────────────────────────────────────────

    def get_data(self, path: str, *, tolerate_503: bool = False) -> bytes:
        """
        GET /data/{apikey}/{path}.

        `tolerate_503=False` (domyślnie): lekki retry (3 próby) dla zwykłych,
        niestabilnych połączeń — 5xx/timeout.
        `tolerate_503=True`: agresywniejszy retry (8 prób, dłuższy backoff) dla zadań z
        celowo symulowanym przeciążeniem (np. "railway"), gdzie 503 jest jawnie
        traktowane jako retryable, nie tylko 5xx ogólnie.

        Jedna publiczna metoda zamiast dwóch osobno nazwanych (`get_data` +
        `get_data_503_tolerant`) — konsolidacja po przeglądzie wszystkich kształtów
        GET-ów używanych w kursie (patrz `get_public()` niżej i `core/AGENTS.md`).
        """
        if tolerate_503:
            return self._get_data_503_tolerant(path)
        return self._get_data_plain(path)

    @retry(
        retry=retry_if_exception(_is_retryable_http_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
    )
    def _get_data_plain(self, path: str) -> bytes:
        """GET /data/{apikey}/{path}; lekki retry, tylko na 5xx/transport errors, nie na trwałe 4xx."""
        url = f"{self._base_url}/data/{self._apikey}/{path}"
        response = self._http.get(url)
        response.raise_for_status()
        return response.content

    @langfuse_observe()
    @retry(
        retry=retry_if_exception(_is_retryable_http_error),
        stop=stop_after_attempt(8),
        wait=wait_exponential(min=3, max=60),
    )
    def _get_data_503_tolerant(self, path: str) -> bytes:
        """Jak `_get_data_plain`, ale 503 jest jawnie zamieniane na wyjątek, żeby retry go złapał, a agresywniejszy backoff (8 prób) toleruje dłuższe symulowane przeciążenia."""
        url = f"{self._base_url}/data/{self._apikey}/{path}"
        response = self._http.get(url)
        if response.status_code == 503:
            raise httpx.HTTPStatusError("503 — retry", request=response.request, response=response)
        response.raise_for_status()
        return response.content

    @retry(
        retry=retry_if_exception(_is_retryable_http_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
    )
    def get_public(self, path: str) -> bytes:
        """
        GET {base_url}/{path} — zasób publiczny, bez apikey. Nie powtarza 4xx (zły
        path to trwały błąd), powtarza 5xx/transport errors — patrz
        _is_retryable_http_error().

        `path` jest ścieżką WZGLĘDEM base_url, bez wiodącego '/' — ta metoda celowo
        NIE zakłada jednego stałego prefiksu. Kurs używa co najmniej czterech różnych
        kształtów publicznych URL-i (zweryfikowane empirycznie, wszystkie zwracają
        200): `dane/doc/{plik}` (dokumenty zadań, S01), `dane/{plik}` (pliki wprost w
        /dane/, np. `drone.html`, `sensors.zip` w S02/S03), `i/{plik}` (obrazy
        referencyjne, np. `solved_electricity.png`), oraz pliki na rootcie (np.
        `reactor_preview.html`, `debug`). Dokładanie osobnej metody na każdy prefiks
        kończyłoby się kilkoma prawie identycznymi, mylącymi się metodami — stąd jedna
        generyczna.

        UWAGA — hub potrafi zwrócić HTTP 200 ze stroną błędu (text/html) zamiast
        prawdziwego 404 dla nieistniejącego zasobu binarnego (potwierdzone: zły URL do
        mapy zwrócił 200+html zamiast image/png). Ta metoda NIE waliduje treści — użyj
        `core.net.expect_binary()`/`expect_not_html()` po stronie wywołującego, gdy
        format ma znaczenie.
        """
        url = f"{self._base_url}/{path.lstrip('/')}"
        response = self._http.get(url)
        response.raise_for_status()
        return response.content

    @retry(
        retry=retry_if_exception(_is_retryable_transport_error),
        stop=stop_after_attempt(6),
        wait=wait_exponential(min=3, max=30),
        reraise=True,
    )
    def post_api(self, path: str, payload: dict) -> dict:
        """POST do dowolnego endpointu hubu (np. /api/zmail, /api/shell, /api/toolsearch).

        **Rate limiting (AID-46): throttle PRZED wysłaniem, nie retry po 429.**
        Każde wywołanie czeka na swoją kolej w `OutgoingThrottle` (jeden na klienta —
        limit huba jest per klucz, nie per endpoint). Po 429 następuje JEDNO długie
        odczekanie i najwyżej jedna ponowna próba; drugie 429 propaguje się do
        wywołującego. To zmiana polityki wobec poprzedniego backoffu 6×3-30s:
        intel społeczności do `s03e02` podejrzewa, że każde 429 PRZEDŁUŻA okno
        blokady, więc seria ponowień aktywnie szkodziła. Model dostaje czytelny
        sygnał przez `core/llm/tool_errors.py` i sam decyduje o ponowieniu.

        5xx i błędy transportu nadal retry'ują z exponential backoffem — to zwykłe
        awarie, nie kara za nasze zachowanie. 4xx inne niż 429 (np. zły parametr
        akcji) propagują się natychmiast. `reraise=True` — wywołujący dostaje
        oryginalny httpx.HTTPStatusError, nie tenacity.RetryError.
        """
        payload = {**payload, "apikey": self._apikey}
        url = f"{self._base_url}{path}"

        self._throttle.wait_turn()
        try:
            response = self._http.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 429:
                raise
            logfire.warning(
                "Rate limit na /api/* — jedno odczekanie, bez pętli ponowień", path=path
            )
            self._throttle.cooldown()
            response = self._http.post(url, json=payload)
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
        """Zamyka klienta httpx przy garbage-collection, tłumiąc błędy zamknięcia."""
        http = getattr(self, "_http", None)
        if http is not None:
            try:
                http.close()
            except httpx.HTTPError as e:
                logfire.warning("Failed to close HubClient HTTP session", error=e)
            except Exception:
                pass
