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

import pytest

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
