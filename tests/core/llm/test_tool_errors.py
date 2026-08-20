"""
Testy formatera błędów narzędzi (AID-48).

Nacisk na dwie rzeczy, które realnie kosztowały ludzi pieniądze albo bezpieczeństwo:
odróżnienie błędu przejściowego od trwałego (model przestaje pętlić się na tym samym
wywołaniu) i redakcję sekretów (hub przyjmuje `apikey` w query stringu, więc treść
wyjątku sieciowego niesie klucz wprost do historii rozmowy).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.llm.tool_errors import format_tool_error, redact

_FAKE_KEY = "1f2e3d4c-5b6a-7988-9a0b-1c2d3e4f5a6b"


def http_error(status: int, body: str = "", message: str = "") -> Exception:
    """Buduje wyjątek o kształcie `httpx.HTTPStatusError` — z atrybutem `.response`."""
    exc = RuntimeError(message or f"Server error '{status}'")
    response = MagicMock()
    response.status_code = status
    response.text = body
    exc.response = response  # type: ignore[attr-defined]
    return exc


class TestRedakcjaSekretow:
    """Nic, co wygląda na poświadczenie, nie może trafić do kontekstu modelu."""

    def test_apikey_w_query_stringu_nie_przechodzi(self):
        """
        Ten test jest powodem istnienia `redact()`: hub przyjmuje apikey w URL-u,
        więc bez niego każdy błąd sieciowy wstrzykiwałby klucz do historii rozmowy.
        """
        text = f"GET https://hub.ag3nts.org/api/x?apikey={_FAKE_KEY}&q=1 failed"
        out = redact(text)
        assert _FAKE_KEY not in out
        assert "<REDACTED>" in out

    def test_goly_uuid_tez_jest_redagowany(self):
        """Klucz bywa w ciele odpowiedzi, nie tylko w query — kształt wystarczy."""
        assert _FAKE_KEY not in redact(f"body: {{'apikey': '{_FAKE_KEY}'}}")

    def test_naglowek_bearer(self):
        out = redact("Authorization: Bearer abc123XYZ.def-456")
        assert "abc123XYZ" not in out
        assert "Bearer <REDACTED>" in out

    def test_klucz_providera_po_prefiksie(self):
        assert "sk-proj-abcdefgh12345678" not in redact("key=sk-proj-abcdefgh12345678")

    def test_nie_zjada_zwyklego_tekstu(self):
        """Redakcja nie może kaleczyć treści diagnostycznej."""
        assert redact("Nie znaleziono miasta Skolwin") == "Nie znaleziono miasta Skolwin"


class TestKlasyfikacjaBledow:
    """Model musi wiedzieć, czy ponawiać, czy poprawiać argumenty."""

    @pytest.mark.parametrize("status", [408, 425, 429, 500, 502, 503, 504])
    def test_przejsciowe_kaza_ponowic(self, status: int):
        out = format_tool_error("fetch", http_error(status))
        assert "PRZEJSCIOWY" in out
        assert str(status) in out

    def test_429_nie_sugeruje_zmiany_argumentow(self):
        """Rate limit z podpowiedzią 'popraw argumenty' pcha model w błędną pętlę."""
        out = format_tool_error("fetch", http_error(429))
        assert "ponow" in out.lower()
        assert "popraw argumenty" not in out.lower()

    @pytest.mark.parametrize("status", [400, 404, 422])
    def test_trwale_4xx_kaza_poprawic_wywolanie(self, status: int):
        out = format_tool_error("fetch", http_error(status))
        assert "TRWALY" in out
        assert "opraw argumenty" in out

    @pytest.mark.parametrize("status", [401, 403])
    def test_brak_uprawnien_zabrania_ponawiania(self, status: int):
        out = format_tool_error("fetch", http_error(status))
        assert "Nie powtarzaj" in out

    def test_kod_http_jest_widoczny_dla_modelu(self):
        """Bez kodu agent nie odróżni bana od literówki — to sedno AID-48."""
        assert "HTTP 429" in format_tool_error("fetch", http_error(429))

    def test_cialo_odpowiedzi_trafia_do_modelu(self):
        out = format_tool_error("fetch", http_error(400, body='{"code":-9999}'))
        assert "-9999" in out

    def test_cialo_odpowiedzi_jest_ograniczone(self):
        """Ciało 5xx bywa stroną HTML — nie może zalać kontekstu."""
        out = format_tool_error("fetch", http_error(500, body="x" * 5000))
        assert len(out) < 1000


class TestBledyNiesieciowe:
    """Zwykłe wyjątki Pythona też muszą nieść użyteczną wskazówkę."""

    def test_zawiera_typ_i_tresc_wyjatku(self):
        out = format_tool_error("parse", ValueError("zly format daty"))
        assert "ValueError" in out
        assert "zly format daty" in out

    def test_nazwa_narzedzia_jest_w_komunikacie(self):
        """Przy kilku narzędziach model musi wiedzieć, które padło."""
        assert "[parse]" in format_tool_error("parse", ValueError("x"))

    def test_bledy_argumentow_kieruja_na_opis_narzedzia(self):
        out = format_tool_error("parse", KeyError("city"))
        assert "rgumenty" in out

    def test_wyjatek_bez_tresci_nie_daje_pustki(self):
        """Pusty komunikat zostawiłby model bez jakiejkolwiek informacji."""
        out = format_tool_error("parse", RuntimeError())
        assert "RuntimeError" in out

    def test_sekret_w_tresci_wyjatku_jest_redagowany(self):
        """Redakcja obowiązuje też na ścieżce niesieciowej."""
        out = format_tool_error("fetch", ValueError(f"url=https://x/?apikey={_FAKE_KEY}"))
        assert _FAKE_KEY not in out


class TestRedakcjaPolJson:
    """
    Sekrety bywają w ciele odpowiedzi HTTP, nie tylko w query stringu.

    `format_tool_error()` wkleja ciało odpowiedzi do kontekstu modelu, więc pole
    `"token": "..."` musi być redagowane tak samo jak `?token=...`.
    """

    def test_token_w_json_jest_redagowany(self):
        out = redact('body: {"token":"opaque-secret-value"}')
        assert "opaque-secret-value" not in out

    def test_apikey_w_json_ze_spacjami(self):
        out = redact('{ "apikey" : "plain-text-secret" }')
        assert "plain-text-secret" not in out

    def test_klucz_google_bez_separatora(self):
        """Klucze Google idą `AIza…` wprost — wymóg `[-_]` po prefiksie je przepuszczał."""
        out = redact("key AIzaSyD9tR4vNm2QpXcYbZ1234567890abcd failed")
        assert "AIzaSyD9tR4vNm2QpXcYbZ1234567890abcd" not in out

    def test_czlon_key_nie_lapie_sie_w_srodku_slowa(self):
        """Bez wiodącego `\\b` wzorzec `key` trafiałby w 'monkey' i kaleczył diagnostykę."""
        assert redact("monkey business") == "monkey business"

    def test_cialo_odpowiedzi_jest_redagowane_w_pelnej_sciezce(self):
        """Test end-to-end: sekret z ciała HTTP nie może dotrzeć do modelu."""
        exc = RuntimeError("bad request")
        response = MagicMock()
        response.status_code = 400
        response.text = '{"token":"leaked-token-value"}'
        exc.response = response  # type: ignore[attr-defined]
        assert "leaked-token-value" not in format_tool_error("fetch", exc)
