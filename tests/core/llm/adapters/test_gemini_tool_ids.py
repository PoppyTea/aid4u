"""
Testy identyfikatorów wywołań narzędzi w adapterze Gemini (AID-18).

Kontrakt „`id` jednoznacznie identyfikuje wywołanie" trzymają adaptery Anthropic
i OpenAI. Gemini go łamał, gdy SDK nie podało `id`, a model wywołał to samo narzędzie
dwa razy w jednej odpowiedzi — oba wywołania dostawały wtedy nazwę narzędzia jako `id`.

Dlaczego to bloker `s03e02`, mimo pozornej drobnicy: strategia kosztowa dla e02 brzmi
„zaczynaj tanio", a społeczność raportuje `gemini-3-flash` rozwiązujące to zadanie za
$0.05 wobec $7.20 na Sonnecie. Tania ścieżka JEST ścieżką Gemini, więc pętla agentowa
na tym adapterze musi być poprawna.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.llm.adapters.gemini import GeminiAdapter
from core.llm.types import LLMMessage, Tool


def part(name: str | None = None, *, call_id: str | None = None, text: str = "") -> MagicMock:
    """Buduje część odpowiedzi Gemini: wywołanie narzędzia albo tekst."""
    p = MagicMock()
    if name is None:
        p.function_call = None
        p.text = text
        return p
    p.function_call = MagicMock()
    p.function_call.name = name
    p.function_call.id = call_id
    p.function_call.args = {"q": name}
    p.text = ""
    return p


def response_with(*parts: MagicMock) -> MagicMock:
    """Owija części w kształt odpowiedzi SDK, jakiego oczekuje adapter."""
    response = MagicMock()
    candidate = MagicMock()
    candidate.content.parts = list(parts)
    response.candidates = [candidate]
    response.usage_metadata.prompt_token_count = 10
    response.usage_metadata.candidates_token_count = 5
    return response


@pytest.fixture
def adapter() -> GeminiAdapter:
    """Adapter z zamockowanym klientem SDK — bez sieci i bez klucza."""
    with patch("google.genai.Client"):
        instance = GeminiAdapter(api_key="test-key")
    instance._client = MagicMock()
    return instance


def call_tools(adapter: GeminiAdapter, response: MagicMock) -> list:
    """Uruchamia `complete_with_tools()` na spreparowanej odpowiedzi SDK."""
    adapter._client.models.generate_content.return_value = response
    result = adapter.complete_with_tools(
        [LLMMessage.user("x")],
        [Tool(name="search", description="d", parameters={})],
    )
    return result.tool_calls


class TestUnikalnosciId:
    """Każde wywołanie w jednej odpowiedzi musi mieć własny identyfikator."""

    def test_dwa_wywolania_tego_samego_narzedzia_maja_rozne_id(self, adapter):
        """Regresja AID-18: bez indeksu oba dostawały nazwę narzędzia i się dublowały."""
        calls = call_tools(adapter, response_with(part("search"), part("search")))
        assert len(calls) == 2
        assert calls[0].id != calls[1].id

    def test_id_z_sdk_ma_pierwszenstwo(self, adapter):
        """Gdy SDK poda własny `id`, nie nadpisujemy go fallbackiem."""
        calls = call_tools(adapter, response_with(part("search", call_id="sdk-abc")))
        assert calls[0].id == "sdk-abc"

    def test_fallback_zawiera_nazwe_narzedzia(self, adapter):
        """Identyfikator ma pozostać czytelny w logach i trace'ach, nie być gołym numerem."""
        calls = call_tools(adapter, response_with(part("search")))
        assert "search" in calls[0].id

    def test_rozne_narzedzia_tez_sa_rozroznialne(self, adapter):
        """Różne narzędzia w jednej odpowiedzi też dostają odrębne id."""
        calls = call_tools(adapter, response_with(part("search"), part("maps")))
        assert {c.name for c in calls} == {"search", "maps"}
        assert calls[0].id != calls[1].id

    def test_indeks_liczy_sie_po_wszystkich_czesciach(self, adapter):
        """
        Część tekstowa między wywołaniami przesuwa indeks — i dobrze, bo indeks ma
        być unikalny w obrębie odpowiedzi, a nie kolejnym numerem wywołania.
        """
        calls = call_tools(adapter, response_with(part("search"), part(text="myślę"), part("search")))
        assert len(calls) == 2
        assert calls[0].id != calls[1].id

    def test_trzy_wywolania_daja_trzy_rozne_id(self, adapter):
        """Trzy wywołania dają trzy różne identyfikatory, nie dwa."""
        calls = call_tools(adapter, response_with(part("search"), part("search"), part("search")))
        assert len({c.id for c in calls}) == 3
