"""
Testy s05e03 — offline, bez sieci.

Zakres jest wąski celowo: pokrywamy wyłącznie te trzy miejsca, w których to zadanie
realnie się przegrywa mimo posiadania poprawnych danych — składanie polecenia `echo`,
arytmetykę „dzień przed" i parsowanie wyniku `grep`. Reszta przepływu to trzy zapytania
HTTP, których test jednostkowy nie zweryfikuje lepiej niż `--dry-run` na żywym hubie.

Dane wejściowe w asercjach to REALNE wartości z archiwum (Grudziądz, 2024-11-13,
53.432303 / 18.968774), więc regresja w parserze widać od razu, a nie dopiero na hubie.
"""

from __future__ import annotations

from datetime import date

import pytest

from tasks.s05e03_shellaccess.archive import extract_output
from tasks.s05e03_shellaccess.solution import (
    _LATITUDE_RE,
    _LOG_LINE_RE,
    _LONGITUDE_RE,
    _NAME_RE,
    build_echo_command,
)

# Wiersz dokładnie w kształcie, w jakim oddał go hub (z prefiksem numeru linii od `grep -n`).
REAL_LOG_LINE = (
    "3704:2024-11-13;W jaskini znaleziono ciało mężczyzny. "
    "Policja bada okoliczności zdarzenia;219;954634"
)


class TestParsowanieWpisuLogu:
    """`_LOG_LINE_RE` nad realnym wynikiem `grep`."""

    def test_wyciaga_wszystkie_cztery_pola(self) -> None:
        """Data, opis, location_id i entry_id rozdzielone poprawnie."""
        match = _LOG_LINE_RE.search(REAL_LOG_LINE)
        assert match is not None
        assert match["date"] == "2024-11-13"
        assert match["location"] == "219"
        assert match["place"] == "954634"

    def test_znosi_prefiks_nazwy_pliku(self) -> None:
        """`grep` dokłada `plik:` przy wielu argumentach — to nie może psuć parsera."""
        match = _LOG_LINE_RE.search(f"/data/time_logs.csv:{REAL_LOG_LINE}")
        assert match is not None
        assert match["date"] == "2024-11-13"
        assert match["place"] == "954634"

    def test_opis_ze_srednikiem_nie_przesuwa_pol(self) -> None:
        """
        Kotwica na końcu wiersza, nie zachłanny podział po `;`.

        Opisy zdarzeń bywają zdaniami złożonymi; średnik w treści przesunąłby
        location_id i entry_id o jedno pole, dając poprawnie wyglądającą złą odpowiedź.
        """
        match = _LOG_LINE_RE.search(
            "1:2024-11-13;Znaleziono ciało; trwa śledztwo;219;954634"
        )
        assert match is not None
        assert match["location"] == "219"
        assert match["place"] == "954634"


class TestParsowaniePlikowJSON:
    """Nazwa miasta i współrzędne z wyniku `grep` nad plikami JSON."""

    def test_dekoduje_escape_diakrytykow(self) -> None:
        """`locations.json` trzyma `ą` jako escape — bez dekodowania miasto idzie zniekształcone."""
        import json

        match = _NAME_RE.search('        "name": "Grudzi\\u0105dz"')
        assert match is not None
        assert json.loads(f'"{match["name"]}"') == "Grudziądz"

    def test_wspolrzedne_zostaja_tekstem(self) -> None:
        """Wartości mają zachować dokładnie cyfry z archiwum, bez konwersji na float."""
        block = '    "latitude": 53.432303,\n    "longitude": 18.968774,\n'
        latitude = _LATITUDE_RE.search(block)
        longitude = _LONGITUDE_RE.search(block)
        assert latitude is not None
        assert longitude is not None
        assert latitude["value"] == "53.432303"
        assert longitude["value"] == "18.968774"

    def test_ujemna_dlugosc_geograficzna(self) -> None:
        """W `gps.json` są wpisy z półkuli zachodniej — minus nie może uciąć wartości."""
        match = _LONGITUDE_RE.search('"longitude": -52.76667')
        assert match is not None
        assert match["value"] == "-52.76667"


class TestBudowaniePoleceniaEcho:
    """Finalne polecenie — tu mieszczą się wszystkie znane tryby porażki tego zadania."""

    def test_realna_odpowiedz(self) -> None:
        """Dokładnie to polecenie zwróciło flagę `{FLG:HUGEFILE}` 2026-08-24."""
        assert build_echo_command(date(2024, 11, 12), "Grudziądz", "53.432303", "18.968774") == (
            'echo \'{"date":"2024-11-12","city":"Grudziądz",'
            '"longitude":18.968774,"latitude":53.432303}\''
        )

    def test_uzywa_echo_nigdy_printf(self) -> None:
        """`printf` zwracał walidatorowi ucięte `{city:` mimo poprawnych danych."""
        command = build_echo_command(date(2024, 11, 12), "Grudziądz", "53.4", "18.9")
        assert command.startswith("echo '")
        assert "printf" not in command

    def test_wspolrzedne_nie_sa_stringami_w_json(self) -> None:
        """Format odpowiedzi wymaga liczb, nie tekstu — cudzysłów wokół nich to cicha porażka."""
        import json

        payload = json.loads(
            build_echo_command(date(2024, 11, 12), "Grudziądz", "53.432303", "18.968774")
            .removeprefix("echo '")
            .removesuffix("'")
        )
        assert isinstance(payload["longitude"], float)
        assert isinstance(payload["latitude"], float)

    def test_apostrof_w_miescie_przerywa_zamiast_wysylac(self) -> None:
        """Apostrof zamknąłby cytowanie `echo '…'` — lepiej wyjątek niż zła odpowiedź."""
        with pytest.raises(ValueError, match="Apostrof"):
            build_echo_command(date(2024, 11, 12), "L'Aquila", "42.35", "13.39")


class TestArytmetykaDaty:
    """„DZIEŃ PRZED" — jedyna informacja, której nie ma w archiwum."""

    @pytest.mark.parametrize(
        ("znalezienie", "spotkanie"),
        [
            (date(2024, 11, 13), "2024-11-12"),
            (date(2024, 3, 1), "2024-02-29"),  # rok przestępny
            (date(2024, 1, 1), "2023-12-31"),  # przełom roku
        ],
    )
    def test_odejmuje_dokladnie_jeden_dzien(self, znalezienie: date, spotkanie: str) -> None:
        """Przesunięcie liczone przez `timedelta`, więc granice miesiąca i roku są za darmo."""
        from datetime import timedelta

        command = build_echo_command(znalezienie - timedelta(days=1), "Miasto", "1.0", "2.0")
        assert f'"date":"{spotkanie}"' in command


class TestWyciaganieStdout:
    """`extract_output()` — kształt odpowiedzi huba ustalony sondą, nie z dokumentacji."""

    def test_preferuje_pole_output(self) -> None:
        """`output` niesie stdout; `message` to stały komunikat statusu."""
        response = {"code": 100, "message": "Command executed.", "output": "abc"}
        assert extract_output(response) == "abc"

    def test_pusty_output_nie_spada_na_komunikat_statusu(self) -> None:
        """
        `grep` bez trafień zwraca pusty stdout — i to jest wynik, nie awaria.

        Gdyby pusty string spadał do fallbacku, polecenie bez trafień raportowałoby
        `"Command executed."` jako swoją treść, czyli „nic nie znalazłem" wyglądałoby
        jak „coś znalazłem". Zgłoszone przez CodeRabbita na PR #81.
        """
        assert extract_output({"code": 100, "message": "Command executed.", "output": ""}) == ""

    def test_fallback_na_message(self) -> None:
        """Gdy huba nie stać na `output`, komunikat jest lepszy niż nic — bywa nośnikiem błędu."""
        assert extract_output({"code": 100, "message": "Command executed."}) == "Command executed."

    def test_brak_tresci_daje_pusty_string(self) -> None:
        """Puste wyjście to normalna odpowiedź `grep`, nie awaria — nie może podnosić wyjątku."""
        assert extract_output({"code": 100}) == ""
