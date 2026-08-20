"""
Throttle wychodzący dla endpointów `/api/*` (AID-46).

Powód istnienia: shell API w `s03e02` ma limit ~30 req/min, a intel społeczności
podejrzewa, że **każde 429 przedłuża okno blokady**. Jeśli tak, naiwne ponawianie po
429 nie jest neutralne — aktywnie pogarsza sytuację, bo każda próba dokłada karę.
Wszystkie udokumentowane straty $4-10 w komentarzach do S03E02 miały ten kształt.

Stąd dwie zasady, obie wymuszone w kodzie, nie w promptcie:

1. **Odstęp PRZED wysłaniem.** Limit przestrzegamy zawczasu zamiast reagować na 429.
   Jedyny moment, w którym mamy nad tym kontrolę, jest przed requestem.
2. **Po 429 czekamy raz, długo — nie ponawiamy w pętli.** Drugie 429 propaguje się do
   wywołującego. Dzięki `core/llm/tool_errors.py` model dostaje wtedy czytelny sygnał
   („przejściowy, poczekaj i ponów"), zamiast zapętlać się w warstwie transportu.

Zegar jest wstrzykiwany, żeby testy nie musiały realnie spać.
"""

from __future__ import annotations

import time
from collections.abc import Callable

# Limit shella w s03e02 to ~30 req/min. 2.5 s daje ~24/min — margines jest tu
# ważniejszy niż przepustowość, bo kara za przekroczenie (ban, reset VM) jest
# nieproporcjonalnie większa niż koszt czekania.
DEFAULT_MIN_INTERVAL_S = 2.5

# Po 429 odczekujemy jeden długi okres zamiast serii ponowień. Wartość dobrana tak,
# by przetrwać okno minutowe z zapasem.
DEFAULT_COOLDOWN_S = 65.0


class OutgoingThrottle:
    """
    Wymusza minimalny odstęp między wywołaniami i pojedyncze odczekanie po 429.

    Jedna instancja na `HubClient`, współdzielona przez wszystkie `/api/*` — limit
    jest po stronie serwera per klucz, więc liczenie go per endpoint by go nie
    respektowało.
    """

    def __init__(
        self,
        *,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        cooldown_s: float = DEFAULT_COOLDOWN_S,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        """Args: `clock`/`sleep` wstrzykiwane w testach, żeby nie spać naprawdę."""
        self._min_interval_s = min_interval_s
        self._cooldown_s = cooldown_s
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._last_call_at: float | None = None

    def wait_turn(self) -> float:
        """
        Czeka tyle, ile trzeba, by zachować minimalny odstęp. Zwraca długość czekania.

        Wołane PRZED wysłaniem — to jedyny moment, w którym da się nie przekroczyć
        limitu, zamiast dowiadywać się o tym z 429.
        """
        now = self._clock()
        waited = 0.0
        if self._last_call_at is not None:
            elapsed = now - self._last_call_at
            remaining = self._min_interval_s - elapsed
            if remaining > 0:
                self._sleep(remaining)
                waited = remaining
        self._last_call_at = self._clock()
        return waited

    def cooldown(self) -> float:
        """
        Jednorazowe długie odczekanie po 429. Zwraca długość czekania.

        Świadomie NIE jest to backoff w pętli: przy podejrzeniu, że 429 przedłuża
        okno, każda kolejna próba pogarsza sytuację. Wywołujący ponawia najwyżej raz.
        """
        self._sleep(self._cooldown_s)
        self._last_call_at = self._clock()
        return self._cooldown_s
