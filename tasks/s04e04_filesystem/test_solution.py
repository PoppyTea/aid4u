"""
Testy s04e04 — offline, bez sieci.

Sercem pliku jest `TestZgodnoscZNiezaleznymZrodlem`: `ogloszenia.txt` opisuje to samo
zapotrzebowanie ośmiu miast, co `food4cities.json` pobrane w **innym zadaniu** (`s04e05`).
Porównanie z tamtym plikiem jest niezależnym wzorcem dla parsera polskiej odmiany —
i to ono wyłapało trzy osobne usterki, zanim cokolwiek poszło na hub:

1. rdzeń `woda` nie skracał się i największa pozycja każdego zamówienia znikała,
2. przy „ziemniaki 100 kg, kapusta 70" cały akapit rozjeżdżał się o jedną pozycję,
3. `fold()` nie usuwał `ł`, więc `lopata` i `wolowina` szły z polskim znakiem.
"""

from __future__ import annotations

import io
import json
import pathlib
import zipfile

import pytest

from tasks.s04e04_filesystem.notes import (
    build_operations,
    city_path,
    file_name,
    fold,
    match_known,
    read_managers,
    read_notes,
    read_transactions,
)

NOTES_ZIP = pathlib.Path("data/input/s04e04_filesystem/natan_notes.zip")
REFERENCE = pathlib.Path("data/input/s04e05_foodwarehouse/food4cities.json")


@pytest.fixture(scope="module")
def ledger():
    """
    Notatki Natana wczytane z zacommitowanej paczki — bez sieci.

    Czytamy z ZIP-a, nie z rozpakowanych plików: `.gitignore` ma globalne `*.txt`, więc
    `ogloszenia.txt` i spółka nie trafiają do repo i na świeżym klonie by ich nie było.
    Ta droga jest też bliższa temu, co robi `solution.py`.
    """
    with zipfile.ZipFile(io.BytesIO(NOTES_ZIP.read_bytes())) as archive:
        files = {
            name: archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if not name.endswith("/")
        }
    return read_notes(files)


class TestSkladanieNazw:
    """`fold()` i `file_name()` — trzy reguły, z czego dwie niepisane."""

    def test_usuwa_l_z_kreska(self) -> None:
        """
        `ł` to jedyna polska litera BEZ dekompozycji kanonicznej.

        Samo `unicodedata.normalize("NFD", …)` + odsiew znaków łączących jej nie rusza,
        więc `łopata` i `wołowina` szłyby do nazw plików z polskim znakiem — wprost
        wbrew treści zadania.
        """
        assert fold("łopata") == "lopata"
        assert fold("wołowina") == "wolowina"
        assert fold("młotek") == "mlotek"

    def test_usuwa_pozostale_ogonki(self) -> None:
        assert fold("mąka") == "maka"
        assert fold("ryż") == "ryz"

    def test_nazwa_pliku_jest_mala_litera(self) -> None:
        """Niepisana reguła API: `/miasta/Brudzewo` odbija się z `code -940`."""
        assert file_name("Brudzewo") == "brudzewo"

    def test_nazwa_pliku_bez_kropek(self) -> None:
        """Niepisana reguła API: `code -935`, „File extensions are not allowed."""
        assert "." not in file_name("Natan Rams.")

    def test_spacja_zamienia_sie_w_podkreslenie(self) -> None:
        assert file_name("Lena Konkel") == "lena_konkel"


class TestDopasowanieOdmiany:
    """`match_known()` — rdzeń zamiast rozumienia języka."""

    @pytest.mark.parametrize(
        ("form", "base"),
        [
            ("chlebow", "chleb"),
            ("mlotkow", "młotek"),
            ("wiertarek", "wiertarka"),
            ("wody", "woda"),
            ("ziemniakow", "ziemniaki"),
            ("Opalina", "Opalino"),
            ("Domatowie", "Domatowo"),
            ("Darzlubiem", "Darzlubie"),
        ],
    )
    def test_rozpoznaje_forme_odmieniona(self, form: str, base: str) -> None:
        assert match_known(form, ["chleb", "młotek", "wiertarka", "woda", "ziemniaki",
                                  "Opalino", "Domatowo", "Darzlubie"]) == base

    def test_dluzszy_rdzen_wygrywa_z_krotszym(self) -> None:
        """
        `maka` jest prefiksem `makaron`.

        Przy kolejności „pierwszy pasujący" mąka wchodziłaby wszędzie tam, gdzie jest
        makaron — cicho i w każdym mieście naraz.
        """
        assert match_known("makaronu", ["maka", "makaron"]) == "makaron"
        assert match_known("maki", ["maka", "makaron"]) == "maka"

    def test_jednostki_nie_sa_towarami(self) -> None:
        """„butelek", „workow", „porcji" mają nie pasować do niczego."""
        for unit in ("butelek", "workow", "porcji"):
            assert match_known(unit, ["woda", "ryz", "chleb"]) is None


class TestOdczytTransakcji:
    """`transakcje.txt` — jedyne źródło form podstawowych w paczce."""

    def test_lewa_strona_strzalki_to_sprzedawca(self, ledger) -> None:
        """`Miasto -> towar -> Miasto`: oferta należy do nadawcy, nie odbiorcy."""
        cities, goods, offers = read_transactions("Darzlubie -> ryż -> Puck\n")
        assert cities == ["Darzlubie", "Puck"]
        assert goods == ["ryż"]
        assert offers == {"ryż": ["Darzlubie"]}

    def test_wszystkie_miasta_z_obu_stron(self, ledger) -> None:
        assert len(ledger.cities) == 8

    def test_towar_moze_miec_kilku_sprzedawcow(self, ledger) -> None:
        """Chleb sprzedają trzy miasta — plik `/towary/chleb` musi linkować do każdego."""
        assert len(ledger.offers["chleb"]) > 1


class TestZgodnoscZNiezaleznymZrodlem:
    """Parser polskiej odmiany kontra `food4cities.json` z zadania s04e05."""

    def test_zapotrzebowanie_zgadza_sie_co_do_sztuki(self, ledger) -> None:
        reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
        parsed = {
            fold(city).casefold(): {fold(good): count for good, count in goods.items()}
            for city, goods in ledger.demand.items()
        }
        assert parsed == {city.casefold(): goods for city, goods in reference.items()}


class TestOsobyOdpowiedzialne:
    """`rozmowy.txt` — plik, na którym wykładały się modele."""

    OCZEKIWANI = {
        "Brudzewo": "Rafal Kisiel",
        "Celbowo": "Oskar Radtke",
        "Darzlubie": "Marta Frantz",
        "Domatowo": "Natan Rams",
        "Karlinkowo": "Lena Konkel",
        "Mechowo": "Eliza Redmann",
        "Opalino": "Iga Kapecka",
        "Puck": "Damian Kroll",
    }

    def test_kazde_miasto_ma_swoja_osobe(self, ledger) -> None:
        assert ledger.managers == self.OCZEKIWANI

    def test_naglowek_pliku_nie_jest_zrodlem_nazwiska(self, ledger) -> None:
        """
        Nagłówek podaje „Notatki przygotowane przez Natana Ramsa z Domatowa" —
        w DOPEŁNIACZU. Wpuszczony do przebiegu ustawiał Domatowu „Natana Ramsa".
        """
        assert ledger.managers["Domatowo"] == "Natan Rams"

    def test_sklada_nazwisko_rozbite_na_dwa_akapity(self) -> None:
        """
        Dwie osoby są przedstawione na raty — nazwisko w jednym zdaniu, imię w innym.
        To jest ta „polska semantyka", o którą rozbijały się modele lokalne.
        """
        text = (
            "= naglowek =\n\n"
            "- zalatwilem wode dla Brudzewa. Kisiel ma do mnie dzwonic w sprawie ryzu.\n\n"
            "- Rafal oddzwonil wieczorem. Woda dla Brudzewa bedzie szybciej.\n"
        )
        assert read_managers(text, ["Brudzewo"], ["woda", "ryz"]) == {"Brudzewo": "Rafal Kisiel"}

    def test_wyraz_otwierajacy_zdanie_nie_jest_imieniem(self) -> None:
        """
        „Najpierw krotki sygnal od Konkel, potem… Teraz to Lena pilnuje tam handlu."

        Filtr po POZYCJI tu nie wystarcza i to jest zmierzone: „Kisiel" też stoi
        na początku zdania. Bez odsiewu wychodziło „Konkel Najpierw".
        """
        text = (
            "= naglowek =\n\n"
            "- Karlinkowo odkrecilo sie po poludniu. Najpierw krotki sygnal od Konkel, "
            "potem dluzsza rozmowa. Teraz to Lena pilnuje tam handlu. Reszta moze poczekac.\n"
        )
        assert read_managers(text, ["Karlinkowo"], []) == {"Karlinkowo": "Lena Konkel"}


class TestNiekompletnyOdczytPrzerywa:
    """Cicha porażka jest tu droższa niż głośna — zła struktura ląduje na hubie."""

    def test_miasto_bez_zapotrzebowania(self) -> None:
        files = {
            "transakcje.txt": "Puck -> ryż -> Mechowo\n",
            "ogloszenia.txt": "Do Pucka: ryz 10 workow.\n",
            "rozmowy.txt": "= x =\n\n- z Pucka dzwonil Damian Kroll.\n",
        }
        with pytest.raises(ValueError, match="Brak zapotrzebowania"):
            read_notes(files)

    def test_brakujacy_plik_zrodlowy(self) -> None:
        with pytest.raises(ValueError, match="brakuje pliku"):
            read_notes({"transakcje.txt": "A -> b -> C\n"})


class TestKolejnoscOperacji:
    """API wymaga, żeby linki wskazywały na ISTNIEJĄCE pliki."""

    def test_miasta_powstaja_przed_linkujacymi_do_nich(self, ledger) -> None:
        """
        `help`: „markdown links must point to existing files".

        `/osoby` i `/towary` linkują do `/miasta`, więc odwrotna kolejność w `batch_mode`
        wywaliłaby cały request.
        """
        operations = build_operations(ledger)
        paths = [op["path"] for op in operations]
        last_city = max(i for i, p in enumerate(paths) if p.startswith("/miasta/"))
        first_linking = min(
            i for i, p in enumerate(paths) if p.startswith(("/osoby/", "/towary/"))
        )
        assert last_city < first_linking

    def test_katalogi_powstaja_najpierw(self, ledger) -> None:
        operations = build_operations(ledger)
        assert [op["action"] for op in operations[:3]] == ["createDirectory"] * 3

    def test_linki_wskazuja_na_realne_sciezki_plikow(self, ledger) -> None:
        operations = build_operations(ledger)
        existing = {op["path"] for op in operations if op["action"] == "createFile"}
        for op in operations:
            for city in ledger.cities:
                target = city_path(city)
                if f"]({target})" in op.get("content", ""):
                    assert target in existing

    def test_kazdy_link_w_osobnej_linii(self, ledger) -> None:
        """Walidator zgłasza „Each link…" (`code -789`) przy sklejeniu linków w jedno zdanie."""
        operations = build_operations(ledger)
        for op in operations:
            if op["path"].startswith("/towary/"):
                for line in op["content"].splitlines():
                    assert line.count("](") <= 1

    def test_json_miast_bez_polskich_znakow(self, ledger) -> None:
        """Treść zadania zabrania polskich znaków także w JSON-ie, nie tylko w nazwach."""
        operations = build_operations(ledger)
        for op in operations:
            if op["path"].startswith("/miasta/"):
                assert op["content"].isascii()
