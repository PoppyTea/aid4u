"""
Testy s05e04 — offline, bez sieci.

Sercem pliku jest `TestWskazowkiRadiowe`: **wszystkie 14 komunikatów to zdania zebrane
z żywego API** podczas budowy rozwiązania, sparowane z prawdziwą pozycją skały odczytaną
po ruchu. To jedyne miejsce, gdzie rozwiązanie opiera się o tekst generowany przez
backend, i jednocześnie jedno z trzech, w których to zadanie się przegrywa.

Pozostałe dwa mają własne klasy: ruch w skałę we WŁASNEJ kolumnie (`TestBezpieczneRuchy`)
i zły hash rozbrajający (`TestOdczytSkanera`).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, call

import httpx
import pytest

from tasks.s05e04_goingthere import solution

from tasks.s05e04_goingthere.rocket import (
    MOVE_OFFSETS,
    HintUnreadable,
    choose_move,
    disarm_hash,
    is_clear,
    parse_hint,
    safe_moves,
    salvage_scan,
)

# Komunikat → kierunek, w którym stoi skała. Zebrane z żywego API 2026-08-25/26;
# pozycja skały potwierdzona odczytem `currentColumn` po wykonaniu ruchu.
REAL_HINTS = [
    ("The route is blocked in the one place your nose is currently pointing. "
     "The sides remain empty.", "go"),
    ("Nothing sits off either wing. The rock occupies the path straight ahead.", "go"),
    ("The craft is not being crowded from either side. The problem is sitting "
     "straight ahead.", "go"),
    ("Your left and right escape lanes are clean. The rock sits directly ahead.", "go"),
    ("Your flanks are clean for now. The impact risk lies straight along the "
     "current heading.", "go"),
    ("Ahead is the only place you should not trust right now. Both side paths "
     "remain open.", "go"),
    ("The hazard is not trailing your wings. It is waiting in the exact path of "
     "the bow.", "go"),
    ("Both edges of the route are empty. The center is occupied by a rock.", "go"),
    ("Port is open, starboard is open, and the center lane is the bad choice. "
     "That stone is dead ahead.", "go"),
    ("You have room on both sides, but not in the direction the craft is already "
     "facing.", "go"),
    ("You have room ahead and also on the right-hand side. The obstruction is "
     "lurking beside the opposite window.", "left"),
    ("No evasive move is needed toward starboard, and the front stays open. "
     "The issue is on the port side.", "left"),
    ("The front view shows nothing alarming, and port stays open. All the trouble "
     "is gathered beside starboard.", "right"),
    ("You do not need to fear the space ahead or the port edge. Watch the "
     "starboard side instead.", "right"),
]


class TestWskazowkiRadiowe:
    """`parse_hint()` — żargon żeglarski na jeden z trzech kierunków."""

    @pytest.mark.parametrize(("hint", "blocked"), REAL_HINTS)
    def test_realne_komunikaty(self, hint: str, blocked: str) -> None:
        assert parse_hint(hint) == blocked

    def test_port_to_lewo_a_starboard_prawo(self) -> None:
        """Zmierzone na żywo: `left` = port = wiersz W GÓRĘ, `right` = starboard = w dół."""
        assert MOVE_OFFSETS["left"] == -1
        assert MOVE_OFFSETS["right"] == 1
        assert MOVE_OFFSETS["go"] == 0

    def test_przeczenie_odwraca_sens(self) -> None:
        """
        „Zagrożenia NIE ma po bokach" i „miejsca NIE ma z przodu" to zdania o tej samej
        budowie i przeciwnym znaczeniu — decyduje podmiot, nie samo przeczenie.
        """
        assert parse_hint("The hazard is not trailing your wings. It is waiting "
                          "in the exact path of the bow.") == "go"
        assert parse_hint("You have room on both sides, but not in the direction "
                          "the craft is already facing.") == "go"

    def test_dziala_bez_nazwania_kierunku_skaly(self) -> None:
        """
        „…lurking beside the opposite window" nie nazywa kierunku w ogóle.

        Ratuje ją wyłącznie eliminacja: dwa kierunki opisane jako wolne ⇒ skała
        jest w trzecim.
        """
        assert parse_hint("You have room ahead and also on the right-hand side. "
                          "The obstruction is lurking beside the opposite window.") == "left"

    def test_prawa_strona_nie_myli_sie_z_oboma_bokami(self) -> None:
        """`right-hand side` zawiera słowo `side` — nie wolno z tego zrobić obu boków."""
        assert parse_hint("Only the right-hand side is blocked.") == "right"

    def test_right_now_to_nie_kierunek(self) -> None:
        """Zwrot czasowy „right now" wskazywał fałszywie prawą burtę."""
        assert parse_hint("Ahead is the only place you should not trust right now. "
                          "Both side paths remain open.") == "go"

    def test_nieznane_sformulowanie_podnosi_wyjatek(self) -> None:
        """
        Zgadywanie kosztuje rozbicie i restart od kolumny 1, więc nieczytelna wskazówka
        ma przerwać, a nie wylosować kierunek.
        """
        with pytest.raises(HintUnreadable):
            parse_hint("Zupełnie inne sformułowanie backendu.")

    def test_sprzeczna_wskazowka_podnosi_wyjatek(self) -> None:
        """Dwa kierunki opisane jako zajęte to niezgodność, nie okazja do wyboru."""
        with pytest.raises(HintUnreadable):
            parse_hint("The rock is ahead. The rock is to port.")


class TestBezpieczneRuchy:
    """Skała we własnej kolumnie — błąd, na którym wykłada się większość uczestników."""

    def test_skala_w_biezacej_kolumnie_blokuje_wiersz(self) -> None:
        """
        Rakieta rusza się najpierw w pionie, potem do przodu, więc skała „obok"
        blokuje docelowy wiersz tak samo jak ta „przed". Wskazówka radiowa tego
        nie powie — mówi tylko o następnej kolumnie.
        """
        assert safe_moves(row=2, free_rows=[1, 2], forbidden_row=None) == ["left", "go"]

    def test_krawedz_siatki_odcina_ruch(self) -> None:
        """Wyjście poza siatkę to też rozbicie, nie odbicie od ściany."""
        assert "left" not in safe_moves(row=1, free_rows=[1, 2, 3], forbidden_row=None)
        assert "right" not in safe_moves(row=3, free_rows=[1, 2, 3], forbidden_row=None)

    def test_oba_zrodla_naraz(self) -> None:
        """Bieżąca kolumna odcina jedno wyjście, następna drugie — zostaje jedno."""
        assert safe_moves(row=2, free_rows=[2, 3], forbidden_row=3) == ["go"]

    def test_brak_wyjscia_daje_pusta_liste(self) -> None:
        """Sytuacja bez ruchu ma być widoczna, nie zamaskowana domyślnym `go`."""
        assert safe_moves(row=1, free_rows=[1], forbidden_row=1) == []


class TestWyborRuchu:
    """`choose_move()` — spośród bezpiecznych wybiera zbliżający do bazy."""

    def test_zbliza_do_wiersza_bazy(self) -> None:
        """
        Baza stoi w konkretnym wierszu kolumny 12, a każdy ruch zjada kolumnę —
        więc na wyrównanie wiersza są tylko te kolumny, które zostały.
        """
        assert choose_move(row=1, free_rows=[1, 2], blocked_direction="go", base_row=3) == "right"

    def test_przy_remisie_wygrywa_go(self) -> None:
        """`go` trzyma wiersz i nie zawęża wyborów w następnej kolumnie."""
        assert choose_move(row=2, free_rows=[1, 2, 3], blocked_direction="left", base_row=2) == "go"

    def test_brak_bezpiecznego_ruchu_przerywa(self) -> None:
        with pytest.raises(RuntimeError, match="Brak bezpiecznego ruchu"):
            choose_move(row=1, free_rows=[1], blocked_direction="go", base_row=1)


class TestOdczytSkanera:
    """Zagłuszanie psuje NAZWY PÓL, nie tylko składnię."""

    # Dosłowna odpowiedź skanera przy namierzeniu (zebrana 2026-08-25).
    ZNIEKSZTALCONA = (
        '{\n    "BatA": {\n        "WEAP0nTyPe": "self-guided missile"\n'
        '        "beTeCTi0NC0be`: "0E0JmF"\n    },\n'
        "    'bEINgTRacKEb\": true,\n    \"frEpUeNCy\": 445\n}"
    )

    def test_odczytuje_pola_mimo_zepsutych_nazw(self) -> None:
        """
        `frequency` przychodzi jako `frEpUeNCy`, `detectionCode` jako `beTeCTi0NC0be`.

        Ani `json.loads()`, ani szukanie nazw pól wprost nie ma tu szans — stąd
        dopasowanie rozmyte progiem podobieństwa.
        """
        assert salvage_scan(self.ZNIEKSZTALCONA) == (445, "0E0JmF")

    def test_nieodczytywalna_odpowiedz_przerywa(self) -> None:
        """Zły hash to zestrzelenie, więc brak danych ma podnieść wyjątek, nie zgadywać."""
        with pytest.raises(ValueError, match="Nie odczytano"):
            salvage_scan("kompletnie inna tresc bez pol")

    def test_hash_rozbrajajacy(self) -> None:
        """SHA1 z `detectionCode` i doklejonego słowa `disarm` — format z treści zadania."""
        import hashlib

        assert disarm_hash("0E0JmF") == hashlib.sha1(b"0E0JmFdisarm").hexdigest()

    def test_czysto_mimo_zniekształcenia(self) -> None:
        """
        Treść zadania obiecuje „It's clear!", API realnie zwraca `"Its cleeear"`.

        Dosłowne porównanie uznałoby to za namierzenie i wysłało bezsensowne
        rozbrajanie — a przy okazji zgubiło prawdziwy radar w innej kolumnie.
        """
        assert is_clear('"Its cleeear"') is True
        assert is_clear("It's clear!") is True

    def test_odpowiedz_o_namierzeniu_nie_jest_czysta(self) -> None:
        assert is_clear(self.ZNIEKSZTALCONA) is False


def _passthrough(call, validate=None):
    """
    Atrapa `_insist()`: wykonuje zapytanie i uruchamia walidację, bez ponawiania.

    Musi przyjmować `validate`, bo odczyt skanera dzieje się WEWNĄTRZ pętli ponowień —
    atrapa o jednym parametrze przechodziła, dopóki parsowanie stało poza pętlą.
    """
    response = call()
    if validate is not None:
        validate(response)
    return response


def _state(*, row: int = 2, col: int = 5, free_rows: list[int] | None = None) -> dict:
    """Build the minimal mission state consumed by the orchestrator."""
    return {
        "player": {"row": row, "col": col},
        "currentColumn": {"freeRows": free_rows if free_rows is not None else [1, 2, 3]},
    }


def _response(text: str, *, status_code: int = 200) -> httpx.Response:
    """Build an HTTP response with a request so status checks behave realistically."""
    request = httpx.Request("GET", "https://hub.example/api/test")
    return httpx.Response(status_code, text=text, request=request)


@pytest.fixture
def going_task(monkeypatch: pytest.MonkeyPatch) -> Any:
    """
    Buduje zadanie odcięte od sieci i od kill switcha.

    Typ zwracany to `Any`, nie `GoingThereTask`, i jest to świadome: testy podmieniają
    prywatne metody na `MagicMock`, a potem asertują na nich `assert_called_once_with`.
    Zadeklarowany typ konkretny dawałby siedem błędów kontroli typów w miejscach, gdzie
    obiekt CELOWO nie jest już pełnoprawnym zadaniem. Jedno miejsce zamiast siedmiu
    wyciszeń — ta sama konwencja co `tasks/s03e02_firmware/test_solution.py:49`.
    """
    monkeypatch.setattr(solution, "check_abort", lambda: None)
    task = solution.GoingThereTask(hub=MagicMock(), llm=None)  # type: ignore[arg-type]
    task._key = "test-api-key"
    task._base = "https://hub.example"
    task._http = MagicMock(spec=httpx.Client)
    return task


class TestPlanowanieMisji:
    """`_plan()` combines current-column rocks, radio hints, and the base row."""

    def test_pobiera_wskazowke_i_omija_skale_w_nastepnej_kolumnie(self, going_task: Any) -> None:
        """With several physical exits, the radio hint excludes the next-column rock."""
        going_task._disarm_if_tracked = MagicMock()
        going_task._read_hint = MagicMock(return_value="go")

        command = going_task._plan(_state(), base_row=3)

        assert command == "right"
        going_task._disarm_if_tracked.assert_called_once_with()
        going_task._read_hint.assert_called_once_with()

    def test_jedno_wyjscie_pomija_zbedna_wskazowke(self, going_task: Any) -> None:
        """A single exit must not risk another call to the deliberately noisy hint API."""
        going_task._disarm_if_tracked = MagicMock()
        going_task._read_hint = MagicMock()

        command = going_task._plan(_state(row=1, free_rows=[1]), base_row=3)

        assert command == "go"
        going_task._read_hint.assert_not_called()

    def test_ostatni_ruch_musi_trafic_dokladnie_w_wiersz_bazy(self, going_task: Any) -> None:
        """The final planner selects the required landing row, not merely the closest exit."""
        going_task._disarm_if_tracked = MagicMock()
        going_task._read_hint = MagicMock(return_value="left")

        command = going_task._plan(_state(), base_row=3, required_row=3)

        assert command == "right"

    def test_nieosiagalny_wiersz_bazy_przerywa_misje(self, going_task: Any) -> None:
        """A blocked final row is reported instead of silently choosing another landing row."""
        going_task._disarm_if_tracked = MagicMock()
        going_task._read_hint = MagicMock(return_value="right")

        with pytest.raises(solution.MissionFailed, match="Nie da się wylądować.*3"):
            going_task._plan(_state(), base_row=3, required_row=3)

    def test_brak_fizycznego_wyjscia_przerywa_przed_pobraniem_wskazowki(
        self, going_task: Any
    ) -> None:
        """No free row is a terminal state and must not be masked by radio parsing."""
        going_task._disarm_if_tracked = MagicMock()
        going_task._read_hint = MagicMock()

        with pytest.raises(solution.MissionFailed, match="Brak bezpiecznego ruchu.*kolumnie 5"):
            going_task._plan(_state(free_rows=[]), base_row=2)

        going_task._read_hint.assert_not_called()


class TestWskazowkiApi:
    """`_read_hint()` retries unreadable transmissions and preserves diagnostics."""

    def test_druga_czytelna_wskazowka_konczy_retry(self, going_task: Any) -> None:
        """An unreadable transmission is retried and the first valid replacement wins."""
        going_task._insist = MagicMock(
            side_effect=[
                _response('{"hint": "unknown wording"}'),
                _response('{"hint": "The rock is dead ahead."}'),
            ]
        )

        assert going_task._read_hint() == "go"
        assert going_task._insist.call_count == 2

    def test_wyczerpanie_retry_zawiera_wszystkie_odebrane_tresci(self, going_task: Any) -> None:
        """Failure lists each bad hint so a new backend phrase can be added safely."""
        going_task._insist = MagicMock(
            side_effect=[
                _response('{"hint": "first unknown"}'),
                _response('{"hint": "second unknown"}'),
            ]
        )

        with pytest.raises(solution.MissionFailed) as failure:
            going_task._read_hint()

        assert "first unknown" in str(failure.value)
        assert "second unknown" in str(failure.value)


class TestRozbrajanieRadaru:
    """The scanner path avoids unnecessary writes and submits the exact disarm payload."""

    def test_czysty_skan_nie_wysyla_rozbrojenia(self, going_task: Any) -> None:
        """A distorted clear message returns after the GET without a scanner POST."""
        going_task._http.get.return_value = _response('"Its cleeear"')
        going_task._insist = MagicMock(side_effect=_passthrough)

        going_task._disarm_if_tracked()

        going_task._http.get.assert_called_once_with(
            "https://hub.example/api/frequencyScanner", params={"key": "test-api-key"}
        )
        going_task._http.post.assert_not_called()

    def test_namierzenie_wysyla_frequency_i_hash(self, going_task: Any) -> None:
        """A tracked rocket posts the recovered frequency and SHA-1 disarm hash."""
        scanner_body = '"frEpUeNCy": 445, "beTeCTi0NC0be": "0E0JmF"'
        going_task._http.get.return_value = _response(scanner_body)
        going_task._http.post.return_value = _response('{"ok": true}')
        going_task._insist = MagicMock(side_effect=_passthrough)

        going_task._disarm_if_tracked()

        going_task._http.post.assert_called_once_with(
            "https://hub.example/api/frequencyScanner",
            json={
                "apikey": "test-api-key",
                "frequency": 445,
                "disarmHash": disarm_hash("0E0JmF"),
            },
        )


class TestPonawianieApi:
    """`_insist()` accepts only successful non-HTML responses within its retry budget."""

    def test_html_jest_odrzucany_a_kolejna_odpowiedz_akceptowana(
        self, going_task: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A successful status carrying an error page is retried just like a status failure."""
        sleep = MagicMock()
        monkeypatch.setattr(solution.time, "sleep", sleep)
        request = MagicMock(
            side_effect=[
                _response("<html><body>gateway noise</body></html>"),
                _response('{"ok": true}'),
            ]
        )

        result = going_task._insist(request)

        assert result.text == '{"ok": true}'
        assert request.call_count == 2
        sleep.assert_called_once_with(solution._BACKOFF_S)

    def test_wyczerpanie_limitu_zglasza_ostatni_blad(
        self, going_task: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Persistent transport failures stop at the configured budget with useful context."""
        monkeypatch.setattr(solution, "_ATTEMPTS", 2)
        sleep = MagicMock()
        monkeypatch.setattr(solution.time, "sleep", sleep)
        request = MagicMock(side_effect=httpx.ConnectError("radio offline"))

        with pytest.raises(solution.MissionFailed, match="2 próbach.*radio offline"):
            going_task._insist(request)

        assert request.call_count == 2
        assert sleep.call_args_list == [
            call(solution._BACKOFF_S),
            call(solution._BACKOFF_S),
        ]


class TestWykonanieRuchu:
    """`_advance()` submits the plan and turns malformed hub replies into mission failures."""

    def test_poprawny_ruch_zwraca_nowy_stan(self, going_task: Any) -> None:
        """The planned command is sent under the hub task name exactly once."""
        moved = _state(row=3, col=6)
        going_task._plan = MagicMock(return_value="right")
        going_task.hub.submit.return_value = moved

        assert going_task._advance(_state(), base_row=3) == moved
        going_task.hub.submit.assert_called_once_with("goingthere", {"command": "right"})

    def test_odrzucony_ruch_zawiera_stan_i_odpowiedz_huba(self, going_task: Any) -> None:
        """A generic HTTP 400 gains enough state and body context to diagnose the crash."""
        going_task._plan = MagicMock(return_value="left")
        response = _response("collision with rock", status_code=400)
        going_task.hub.submit.side_effect = httpx.HTTPStatusError(
            "rejected", request=response.request, response=response
        )

        with pytest.raises(solution.MissionFailed) as failure:
            going_task._advance(_state(row=2, col=5, free_rows=[1, 2]), base_row=1)

        message = str(failure.value)
        assert "Ruch 'left' z kolumny 5" in message
        assert "wiersz 2, wolne [1, 2]" in message
        assert "collision with rock" in message

    def test_odpowiedz_bez_gracza_jest_odrzucana(self, going_task: Any) -> None:
        """A nominal hub reply without a position cannot become the next loop state."""
        going_task._plan = MagicMock(return_value="go")
        going_task.hub.submit.return_value = {"ok": True}

        with pytest.raises(solution.MissionFailed, match="nie zwrócił pozycji"):
            going_task._advance(_state(), base_row=2)


class TestPrzebiegSolve:
    """`solve()` owns mission setup and deliberately leaves final submission to BaseTask."""

    def test_zwraca_ostatni_ruch_bez_wysylania_go(
        self, going_task: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression: solve advances only through column 11 and returns the column-12 move."""
        start = {
            **_state(col=9),
            "base": {"row": 3},
        }
        column_10 = _state(row=2, col=10)
        column_11 = _state(row=2, col=11)
        going_task.hub.submit.return_value = start
        going_task._advance = MagicMock(side_effect=[column_10, column_11])
        going_task._plan = MagicMock(return_value="right")
        monkeypatch.setattr(
            solution,
            "get_config",
            lambda: SimpleNamespace(apikey="configured-key", hub_base_url="https://configured"),
        )
        http_client = MagicMock(spec=httpx.Client)
        client_context = MagicMock()
        client_context.__enter__.return_value = http_client
        client_factory = MagicMock(return_value=client_context)
        monkeypatch.setattr(solution.httpx, "Client", client_factory)

        result = going_task.solve(None)

        assert result == {"command": "right"}
        going_task.hub.submit.assert_called_once_with("goingthere", {"command": "start"})
        assert going_task._advance.call_args_list == [call(start, 3), call(column_10, 3)]
        going_task._plan.assert_called_once_with(column_11, 3, required_row=3)
        assert going_task._http is http_client
        client_factory.assert_called_once_with(timeout=25.0)
