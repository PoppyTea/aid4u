"""
Testy throttle'a wychodzącego i polityki 429 (AID-46).

Sedno zmiany nie jest wydajnościowe, tylko strategiczne: przy podejrzeniu, że każde
429 PRZEDŁUŻA okno blokady, seria ponowień pogarsza sytuację zamiast ją przeczekać.
Te testy pilnują, że po drugim 429 błąd propaguje się do wywołującego, zamiast
zapętlać się w warstwie transportu.

Zegar i sen są wstrzykiwane — testy sprawdzają decyzje, nie to, czy `time.sleep()` śpi.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from core.hub.client import HubClient
from core.hub.throttle import OutgoingThrottle


class FakeClock:
    """Zegar sterowany ręcznie; `sleep()` przesuwa czas zamiast czekać."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def time(self) -> float:
        """Bieżąca wartość zegara."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Rejestruje czekanie i przesuwa zegar."""
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    """Wstrzykiwany zegar dla throttle'a."""
    return FakeClock()


class TestOdstepMiedzyWywolaniami:
    """Limit przestrzegamy PRZED wysłaniem — to jedyny moment, w którym mamy kontrolę."""

    def test_pierwsze_wywolanie_nie_czeka(self, clock):
        """Pierwsze żądanie w przebiegu nie ma na co czekać."""
        t = OutgoingThrottle(min_interval_s=2.5, clock=clock.time, sleep=clock.sleep)
        assert t.wait_turn() == 0.0
        assert clock.slept == []

    def test_drugie_wywolanie_dopelnia_odstep(self, clock):
        """Drugie żądanie tuż po pierwszym musi dopełnić pełny odstęp."""
        t = OutgoingThrottle(min_interval_s=2.5, clock=clock.time, sleep=clock.sleep)
        t.wait_turn()
        assert t.wait_turn() == pytest.approx(2.5)

    def test_nie_czeka_gdy_odstep_juz_minal(self, clock):
        """Gdy odstęp minął naturalnie, nie dokładamy sztucznego czekania."""
        t = OutgoingThrottle(min_interval_s=2.5, clock=clock.time, sleep=clock.sleep)
        t.wait_turn()
        clock.now += 10.0
        assert t.wait_turn() == 0.0

    def test_czeka_tylko_brakujaca_reszte(self, clock):
        """Czekamy różnicę, nie pełny odstęp — inaczej throttle dławiłby dwukrotnie."""
        t = OutgoingThrottle(min_interval_s=2.5, clock=clock.time, sleep=clock.sleep)
        t.wait_turn()
        clock.now += 1.0
        assert t.wait_turn() == pytest.approx(1.5)

    def test_zerowy_odstep_wylacza_czekanie(self, clock):
        """Używane w testach i tam, gdzie limit nie obowiązuje."""
        t = OutgoingThrottle(min_interval_s=0, clock=clock.time, sleep=clock.sleep)
        t.wait_turn()
        assert t.wait_turn() == 0.0


class TestCooldownu:
    """Po 429 czekamy raz i długo, zamiast ponawiać w pętli."""

    def test_cooldown_czeka_pelny_okres(self, clock):
        """Po 429 odczekujemy cały zadeklarowany okres, nie jego część."""
        t = OutgoingThrottle(cooldown_s=65.0, clock=clock.time, sleep=clock.sleep)
        assert t.cooldown() == pytest.approx(65.0)
        assert clock.slept == [65.0]

    def test_cooldown_oznacza_slot_jako_zuzyty(self, clock):
        """
        Po cooldownie `post_api()` ponawia request OD RAZU, z pominięciem `wait_turn()`
        — bo właśnie odczekało 65 s. `cooldown()` musi więc zaznaczyć ten moment jako
        ostatnie wywołanie, żeby KOLEJNE żądanie znów zachowało pełny odstęp. Gdyby
        tego nie robiło, ponowienie i następny request poszłyby jedno po drugim.
        """
        t = OutgoingThrottle(
            min_interval_s=2.5, cooldown_s=65.0, clock=clock.time, sleep=clock.sleep
        )
        t.cooldown()
        assert t.wait_turn() == pytest.approx(2.5)


class TestPolityki429:
    """Zachowanie `post_api()` — to tutaj mieszka właściwa zmiana strategii."""

    def _client(self) -> HubClient:
        """HubClient z throttlem bez czekania (wzorzec z `tests/core/test_hub.py`)."""
        hub = HubClient.__new__(HubClient)
        hub._apikey = "test-key"
        hub._base_url = "https://hub.ag3nts.org"
        hub._http = httpx.Client()
        hub._throttle = OutgoingThrottle(min_interval_s=0, cooldown_s=0)
        return hub

    @respx.mock
    def test_jedno_429_jest_przeczekane_i_ponowione(self):
        """
        Po 429 następuje odczekanie, a potem JEDNA ponowna próba.

        Liczba żądań to za słaba asercja: przy `cooldown_s=0` test przeszedłby także
        wtedy, gdyby `post_api()` ponawiało NATYCHMIAST, w ogóle nie wołając
        `cooldown()`. Liczymy więc wywołania cooldownu wprost.
        """
        hub = self._client()
        cooldowns: list[int] = []
        original = hub._throttle.cooldown
        hub._throttle.cooldown = lambda: (cooldowns.append(1), original())[1]  # type: ignore[method-assign]

        route = respx.post("https://hub.ag3nts.org/api/shell").mock(
            side_effect=[
                httpx.Response(429, json={"rate_limited": True}),
                httpx.Response(200, json={"ok": True}),
            ]
        )
        assert hub.post_api("/api/shell", {"cmd": "ls"}) == {"ok": True}
        assert route.call_count == 2
        assert len(cooldowns) == 1, "odczekanie po 429 musi faktycznie nastąpić"
        hub._http.close()

    @respx.mock
    def test_drugie_429_propaguje_zamiast_petlic(self):
        """
        Sedno AID-46: przy podejrzeniu, że 429 przedłuża okno, kolejne próby szkodzą.
        Model dostaje czytelny sygnał przez `tool_errors` i sam decyduje o ponowieniu.
        """
        hub = self._client()
        route = respx.post("https://hub.ag3nts.org/api/shell").mock(
            return_value=httpx.Response(429, json={"rate_limited": True})
        )
        with pytest.raises(httpx.HTTPStatusError) as exc:
            hub.post_api("/api/shell", {"cmd": "ls"})
        assert exc.value.response.status_code == 429
        assert route.call_count == 2, "dokładnie jedna ponowna próba, nie pętla"
        hub._http.close()

    @respx.mock
    def test_404_propaguje_natychmiast_bez_cooldownu(self):
        """Trwałe 4xx nie jest karą za tempo — ponawianie nic nie da."""
        hub = self._client()
        route = respx.post("https://hub.ag3nts.org/api/vehicles").mock(
            return_value=httpx.Response(404, json={"code": -1})
        )
        with pytest.raises(httpx.HTTPStatusError):
            hub.post_api("/api/vehicles", {"query": "car"})
        assert route.call_count == 1
        hub._http.close()

    @respx.mock
    def test_kazde_wywolanie_czeka_na_swoja_kolej(self):
        """Throttle musi być wołany PRZED wysłaniem, nie po."""
        hub = self._client()
        calls: list[str] = []
        hub._throttle = OutgoingThrottle(min_interval_s=0, cooldown_s=0)
        original = hub._throttle.wait_turn
        hub._throttle.wait_turn = lambda: (calls.append("wait"), original())[1]  # type: ignore[method-assign]

        respx.post("https://hub.ag3nts.org/api/x").mock(return_value=httpx.Response(200, json={}))
        hub.post_api("/api/x", {})
        assert calls == ["wait"]
        hub._http.close()
