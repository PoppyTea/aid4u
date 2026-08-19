"""
Testy s03e04 — offline, na PRAWDZIWYCH plikach CSV z `data/input/`.

Nacisk położony na przypadki, które realnie wywracają przebieg na żywo:
odmiana polska, limit 500 bajtów i sierota bez miast. Testy na syntetycznych
danych nie złapałyby żadnego z nich.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tasks.s03e04_negotiations.catalog import CatalogIndex, normalize, stem
from tasks.s03e04_negotiations.solution import build_tools


@pytest.fixture(scope="module")
def index() -> CatalogIndex:
    """Indeks zbudowany raz na moduł — ładowanie 2137 pozycji nie jest darmowe."""
    return CatalogIndex.load()


@pytest.fixture(scope="module")
def client():
    """Klient testowy serwera narzędzi, zamykany po module (patrz AID-34)."""
    from tasks.s03e04_negotiations import server

    with TestClient(server.app) as c:
        yield c


class TestNormalizacja:
    def test_zdejmuje_diakrytyki_i_wielkosc(self):
        assert normalize("Turbina WIATROWA żółć") == "turbina wiatrowa zolc"

    def test_stem_obcina_koncowke_fleksyjna(self):
        assert stem("turbiny") == "turbin"
        assert stem("wiatrowej") == "wiatrow"

    def test_stem_nie_rusza_tokenow_z_cyfra(self):
        """'48v' i '400w' niosą znaczenie w końcówce — obcięcie zmieniłoby parametr."""
        assert stem("48v") == "48v"
        assert stem("400w") == "400w"

    def test_stem_nie_zjada_krotkiego_slowa(self):
        assert stem("kod") == "kod"


class TestZalozeniaDanych:
    def test_kody_i_nazwy_sa_unikalne(self, index: CatalogIndex):
        """Pułapka zduplikowanych kodów z komentarzy kursu jest już załatana upstream."""
        assert index.item_count == 2137

    def test_jedyna_sierota_to_06OTEB(self, index: CatalogIndex):
        """
        Pozostałość po rozdzieleniu zduplikowanego kodu 06OTEA: pozycja dostała
        własny kod, ale nie dostała ani jednego połączenia z miastem.
        """
        assert [i.code for i in index.orphans()] == ["06OTEB"]
        assert index.cities_for("06OTEB") == []

    def test_kod_sieroty_istnieje_mimo_braku_miast(self, index: CatalogIndex):
        """Odróżnienie 'nie ma takiego kodu' od 'kod bez miast' — inny komunikat dla agenta."""
        assert index.has_code("06OTEB")
        assert not index.has_code("ZZZZZZ")


class TestDopasowanie:
    def test_odmiana_polska_trafia_w_mianownik(self, index: CatalogIndex):
        """Rdzeń problemu: agent pyta 'turbiny wiatrowej', katalog ma 'Turbina wiatrowa'."""
        codes = [m.item.code for m in index.search("szukam turbiny wiatrowej")]
        assert "WITR48" in codes and "WITR24" in codes

    def test_literowka_agenta_nadal_trafia(self, index: CatalogIndex):
        codes = [m.item.code for m in index.search("trubina wiatrowa")]
        assert "WITR48" in codes

    def test_parametry_decyduja_o_kolejnosci(self, index: CatalogIndex):
        """Oba warianty pasują nazwą; wygrywa ten, którego napięcie agent wymienił."""
        assert index.search("turbina wiatrowa 24V")[0].item.code == "WITR24"
        assert index.search("turbina wiatrowa 48V")[0].item.code == "WITR48"

    def test_zapytanie_ogolne_nie_wypada_przez_parametry(self, index: CatalogIndex):
        """
        Regresja: punktowanie pokrycia po WSZYSTKICH tokenach pozycji dawało tu
        0 trafień, bo 'Turbina wiatrowa 400W 48V' ma 4 tokeny, a zapytanie 2.
        """
        assert index.search("turbina wiatrowa")

    def test_krotki_kwalifikator_nie_rozwadnia_nazwy(self, index: CatalogIndex):
        """
        Regresja z PRZEBIEGU NA ŻYWO: 'Inwerter DC/AC 48V 3000W' miał rdzenie
        nazwy ('inwerter','dc','ac'), więc zapytanie 'inwerter' dawało pokrycie
        1/3 i wypadało nawet z progu awaryjnego. Agent Centrali odbił się o to
        błędem -790 'The store does not have inverters'.
        """
        codes = [m.item.code for m in index.search("inwerter")]
        assert "A94MAZ" in codes and "A94ZZ4" in codes

    def test_kwalifikator_parametryczny_nadal_rozstrzyga_ranking(self, index: CatalogIndex):
        assert index.search("inwerter ktory pasuje pod 48V")[0].item.code == "A94MAZ"

    def test_pozycja_bez_miast_schodzi_na_koniec(self, index: CatalogIndex):
        """
        06OTEB pasuje do '12V' lepiej niż 06OTEA, ale nikt go nie sprzedaje —
        podanie go agentowi prowadziłoby w ślepy zaułek.
        """
        results = index.search("akumulator 12V")
        assert results[0].item.code == "06OTEA"

    def test_brak_w_katalogu_zwraca_pusto(self, index: CatalogIndex):
        """W bazie nie ma kabli ani kontrolerów ładowania — zmyślanie byłoby gorsze."""
        assert index.search("kontroler ladowania MPPT") == []

    def test_przeciecie_miast_to_cel_zadania(self, index: CatalogIndex):
        wspolne = index.cities_for_all(["WITR48", "06OTEA"])
        assert set(wspolne) <= set(index.cities_for("WITR48"))
        assert set(wspolne) <= set(index.cities_for("06OTEA"))

    def test_przeciecie_z_sierota_jest_puste(self, index: CatalogIndex):
        assert index.cities_for_all(["WITR48", "06OTEB"]) == []


class TestExtractCode:
    def test_znany_kod_wygrywa_z_szescioliterowym_slowem(self, index: CatalogIndex):
        """'PROSZE' ma kształt kodu, ale nie istnieje w katalogu — nie może wygrać."""
        assert index.extract_code("sprawdz prosze kod WITR48 dla mnie") == "WITR48"

    def test_akceptuje_maly_zapis(self, index: CatalogIndex):
        assert index.extract_code("witr48") == "WITR48"

    def test_brak_kandydata_daje_none(self, index: CatalogIndex):
        assert index.extract_code("turbina wiatrowa") is None

    def test_nieznany_kandydat_wraca_do_zglosznia_bledu(self, index: CatalogIndex):
        """Zwrócenie nieznanego kandydata pozwala endpointowi powiedzieć 'nieznany kod X'."""
        assert index.extract_code("kod ZZZZZZ") == "ZZZZZZ"


class TestKontraktHuba:
    def test_dokladnie_dwa_narzedzia(self):
        """Walidator huba odrzuca zgłoszenie z inną liczbą niż 2."""
        assert len(build_tools("https://x.ngrok-free.app")) == 2

    def test_klucz_URL_wielkimi_literami(self):
        assert all("URL" in t and "description" in t for t in build_tools("https://x"))

    def test_url_nie_dubluje_ukosnika(self):
        assert build_tools("https://x/")[0]["URL"] == "https://x/search"


class TestEndpointy:
    def _output(self, client, path: str, params) -> str:
        response = client.post(path, json={"params": params})
        assert response.status_code == 200
        return response.json()["output"]

    def test_search_zwraca_kod_i_nazwe(self, client):
        assert "WITR48" in self._output(client, "/search", "szukam turbiny wiatrowej")

    def test_cities_zwraca_miasta_po_przecinku(self, client):
        out = self._output(client, "/cities", "WITR48")
        assert "Skolwin" in out

    def test_cities_odroznia_sierote_od_nieznanego_kodu(self, client):
        assert "zadnym miescie" in self._output(client, "/cities", "06OTEB")
        assert "nieznany kod" in self._output(client, "/cities", "ZZZZZZ")

    @pytest.mark.parametrize(
        "path,params",
        [
            ("/search", "szukam turbiny wiatrowej"),
            ("/search", "kontroler ladowania MPPT"),
            ("/search", ""),
            ("/search", None),
            ("/search", 12345),
            ("/cities", "WITR48"),
            ("/cities", "06OTEB"),
            ("/cities", "bez kodu"),
        ],
    )
    def test_odpowiedz_zawsze_miesci_sie_w_limicie(self, client, path, params):
        """
        Hub wymaga 4-500 bajtów. Poniżej dolnego limitu albo przy braku
        odpowiedzi agent przerywa pracę na stałe — to najgorszy możliwy wynik.
        """
        out = self._output(client, path, params)
        assert 4 <= len(out.encode("utf-8")) <= 500

    def test_zle_ciało_nie_wywraca_endpointu(self, client):
        """Walidacja 422 byłaby dla agenta równoznaczna z brakiem odpowiedzi."""
        response = client.post("/search", json={})
        assert response.status_code == 200
        assert response.json()["output"]


class TestSecretsProbe:
    """Tryb `--secrets` — prompt injection. Normalny przebieg go nie dotyka."""

    def test_domyslnie_wylaczony(self, monkeypatch):
        from tasks.s03e04_negotiations import secrets_probe

        monkeypatch.delenv("S03E04_SECRETS", raising=False)
        assert secrets_probe.enabled() is False

    def test_wlaczany_zmienna(self, monkeypatch):
        from tasks.s03e04_negotiations import secrets_probe

        monkeypatch.setenv("S03E04_SECRETS", "1")
        assert secrets_probe.enabled() is True

    def test_build_tools_bez_secrets_nie_wstrzykuje(self):
        tools = build_tools("https://x")
        assert all("AUDYT" not in t["description"] for t in tools)

    def test_build_tools_z_secrets_wstrzykuje_do_obu(self):
        tools = build_tools("https://x", secrets=True)
        assert len(tools) == 2
        assert all("BASE64" in t["description"] for t in tools)

    def test_opisy_sekretne_mieszcza_sie_w_limicie_huba(self):
        """Hub odrzuca opis >300 znakow (-875) — regresja z podejscia na zywo."""
        for t in build_tools("https://x", secrets=True):
            assert len(t["description"]) <= 300

    def test_augment_output_dokleja_gdy_sie_miesci(self):
        from tasks.s03e04_negotiations import secrets_probe

        out = secrets_probe.augment_output("Domatowo, Skolwin")
        assert "base64" in out
        assert len(out.encode("utf-8")) <= 500

    def test_augment_output_pomija_gdy_brak_miejsca(self):
        from tasks.s03e04_negotiations import secrets_probe

        real = "x" * 480
        assert secrets_probe.augment_output(real) == real

    def test_decode_wykrywa_flage_base64(self):
        import base64

        from tasks.s03e04_negotiations import secrets_probe

        enc = base64.b64encode(b"{FLG:SECRET}").decode()
        methods = dict(secrets_probe.decode_flags(f"oto token: {enc}"))
        assert methods.get("base64") == "{FLG:SECRET}"

    def test_decode_ignoruje_zwykly_tekst(self):
        from tasks.s03e04_negotiations import secrets_probe

        assert secrets_probe.decode_flags("Domatowo, Skolwin, Rzeszow") == []
