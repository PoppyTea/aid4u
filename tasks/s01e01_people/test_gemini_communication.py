"""
Diagnostyka komunikacji z Gemini dla S01E01.

Kontekst: hipoteza o warstwie sortowania people.csv została wykluczona
(zob. TestFilterCandidatesRealData w test_solution.py — kolejność wierszy
jest zachowana). Druga hipoteza to komunikacja z Gemini. Ten plik sprawdza
ją w trzech warstwach:

  1. Przed wysłaniem — czy request (prompt + config) jest poprawnie
     zbudowany, zanim pójdzie do sieci. Czyste funkcje, bez mocków.
  2. Komunikacja z adapterem (in/out) — czy GeminiAdapter poprawnie
     serializuje request do SDK i deserializuje odpowiedź z powrotem do
     domenowych typów. Mockuje `genai.Client`, więc działa bez klucza API
     i bez sieci.
  3. Przy odbiorze (integration) — prawdziwy round-trip z Gemini na
     rzeczywistych kandydatach z people.csv. Wymaga GEMINI_API_KEY:
         GEMINI_API_KEY=... uv run pytest -m integration \\
             tasks/s01e01_people/test_gemini_communication.py -v
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from google.genai import types

from core.llm.adapters.gemini import GeminiAdapter
from core.llm.types import LLMMessage
from tasks.s01e01_people.prompts import SYSTEM_TAGGING, USER_TAGGING
from tasks.s01e01_people.solution import (
    TaggedJob,
    TaggingResponse,
    build_tagging_prompt,
    filter_candidates,
    parse_csv,
)

REAL_PEOPLE_CSV = Path(__file__).resolve().parents[2] / "data" / "main_story" / "people.csv"


def _extract_jobs_json(prompt: str) -> list[dict]:
    """Wyciąga embedded jobs_json z USER_TAGGING.

    Uwaga: USER_TAGGING zawiera DWIE tablice JSON — dane (jobs_json) oraz
    przykładowy format odpowiedzi w treści instrukcji. `rindex("]")` łapałoby
    zamknięcie tej drugiej, więc parsujemy raw_decode od pierwszego "[".
    """
    start = prompt.index("[")
    jobs, _ = json.JSONDecoder().raw_decode(prompt, start)
    return jobs


@pytest.fixture(scope="module")
def real_candidates() -> list[dict]:
    people = parse_csv(REAL_PEOPLE_CSV.read_bytes())
    candidates = filter_candidates(people)
    assert candidates, "Brak kandydatów w people.csv — nie da się przetestować tagowania"
    return candidates


# ─── 1. Przed wysłaniem ───────────────────────────────────────────────────────
#
# Czyste funkcje: sprawdzają, że request jest poprawnie zbudowany, zanim
# w ogóle dotrze do adaptera/sieci.


class TestBeforeSend:
    def test_prompt_has_no_unresolved_placeholders(self, real_candidates):
        prompt = build_tagging_prompt(real_candidates)
        assert "{jobs_json}" not in prompt, (
            "USER_TAGGING nie podstawił jobs_json — placeholder poszedłby do modelu"
        )

    def test_prompt_embeds_all_candidates_as_valid_json(self, real_candidates):
        jobs = _extract_jobs_json(build_tagging_prompt(real_candidates))
        assert len(jobs) == len(real_candidates)
        assert [j["index"] for j in jobs] == list(range(len(real_candidates)))

    def test_prompt_has_no_empty_job_descriptions(self, real_candidates):
        jobs = _extract_jobs_json(build_tagging_prompt(real_candidates))
        assert all(isinstance(j["job"], str) and j["job"].strip() for j in jobs), (
            "Pusty/None opis zawodu w requeście — Gemini nie ma czego tagować"
        )

    def test_system_prompt_has_no_unresolved_placeholders(self):
        assert "{" not in SYSTEM_TAGGING and "}" not in SYSTEM_TAGGING

    def test_user_template_declares_jobs_json_placeholder(self):
        assert "{jobs_json}" in USER_TAGGING


# ─── 2. Komunikacja z adapterem — IN (co adapter wysyła do SDK) ──────────────
#
# Mockuje `_client.models.generate_content` — bez sieci, bez prawdziwego
# klucza. Weryfikuje dokładnie to, co faktycznie wychodzi z adaptera.


class FakeResponse:
    def __init__(self, *, parsed=None, text=None, finish_reason=types.FinishReason.STOP):
        self.parsed = parsed
        self.text = text
        self.usage_metadata = None

        class _Candidate:
            def __init__(self, fr):
                self.finish_reason = fr

        self.candidates = [_Candidate(finish_reason)] if finish_reason is not None else []


class TestAdapterOutgoingCommunication:
    @pytest.fixture
    def adapter(self):
        return GeminiAdapter(api_key="test-key-not-real", model="gemini-2.5-flash")

    def test_sends_response_schema_and_thinking_budget_zero(self, adapter, monkeypatch):
        captured = {}

        def fake_generate_content(*, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return FakeResponse(parsed=TaggingResponse(results=[]))

        monkeypatch.setattr(adapter._client.models, "generate_content", fake_generate_content)

        adapter.complete_structured(
            [LLMMessage.user("test prompt")],
            TaggingResponse,
            system=SYSTEM_TAGGING,
        )

        assert captured["model"] == "gemini-2.5-flash"
        assert "test prompt" in captured["contents"]
        assert captured["config"].response_schema is TaggingResponse
        assert captured["config"].response_mime_type == "application/json"
        assert captured["config"].thinking_config.thinking_budget == 0
        assert captured["config"].system_instruction == SYSTEM_TAGGING

    def test_sends_all_messages_joined_into_prompt(self, adapter, monkeypatch):
        captured = {}

        def fake_generate_content(*, model, contents, config):
            captured["contents"] = contents
            return FakeResponse(parsed=TaggingResponse(results=[]))

        monkeypatch.setattr(adapter._client.models, "generate_content", fake_generate_content)

        adapter.complete_structured(
            [LLMMessage.user("wiadomość 1"), LLMMessage.assistant("wiadomość 2")],
            TaggingResponse,
        )

        assert "wiadomość 1" in captured["contents"]
        assert "wiadomość 2" in captured["contents"]


# ─── 3. Komunikacja z adapterem — OUT (jak adapter parsuje odpowiedź) ────────


class TestAdapterIncomingCommunication:
    @pytest.fixture
    def adapter(self):
        return GeminiAdapter(api_key="test-key-not-real", model="gemini-2.5-flash")

    def test_uses_native_parsed_response_when_available(self, adapter, monkeypatch):
        expected = TaggingResponse(results=[TaggedJob(index=0, tags=["transport"])])
        monkeypatch.setattr(
            adapter._client.models,
            "generate_content",
            lambda **kw: FakeResponse(parsed=expected),
        )

        result = adapter.complete_structured([LLMMessage.user("x")], TaggingResponse)
        assert result is expected

    def test_falls_back_to_manual_json_parse_when_parsed_missing(self, adapter, monkeypatch):
        raw_json = '{"results": [{"index": 0, "tags": ["medycyna"]}]}'
        monkeypatch.setattr(
            adapter._client.models,
            "generate_content",
            lambda **kw: FakeResponse(parsed=None, text=raw_json),
        )

        result = adapter.complete_structured([LLMMessage.user("x")], TaggingResponse)
        assert result.results == [TaggedJob(index=0, tags=["medycyna"])]

    def test_raises_readable_error_on_truncated_response(self, adapter, monkeypatch):
        truncated_json = '{"results": [{"index": 0, "tags": ["medyc'  # urwany JSON
        monkeypatch.setattr(
            adapter._client.models,
            "generate_content",
            lambda **kw: FakeResponse(
                parsed=None, text=truncated_json, finish_reason=types.FinishReason.MAX_TOKENS
            ),
        )

        with pytest.raises(ValueError, match="ucięty JSON"):
            adapter.complete_structured([LLMMessage.user("x")], TaggingResponse)

    def test_raises_typeerror_when_no_text_and_no_parsed(self, adapter, monkeypatch):
        monkeypatch.setattr(
            adapter._client.models,
            "generate_content",
            lambda **kw: FakeResponse(
                parsed=None, text=None, finish_reason=types.FinishReason.SAFETY
            ),
        )

        with pytest.raises(TypeError, match="Response text is None"):
            adapter.complete_structured([LLMMessage.user("x")], TaggingResponse)


# ─── 4. Przy odbiorze — prawdziwy round-trip (integration) ──────────────────


@pytest.mark.integration
class TestRealGeminiRoundtrip:
    """
    Wymaga GEMINI_API_KEY w env. Odtwarza dokładnie krok 3 z PeopleTask.solve():
    build_tagging_prompt → complete_structured → sprawdzenie, że wszystkie
    indeksy kandydatów wróciły otagowane (bez luk, bez ucięcia).
    """

    @pytest.fixture(scope="class")
    @classmethod
    def gemini_provider(cls):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            pytest.skip("GEMINI_API_KEY nie ustawiony — pomijam integration test")
        return GeminiAdapter(api_key=api_key, model="gemini-2.5-flash")

    def test_real_tagging_call_covers_all_candidates(self, gemini_provider, real_candidates):
        prompt = build_tagging_prompt(real_candidates)
        result = gemini_provider.complete_structured(
            [LLMMessage.user(prompt)],
            TaggingResponse,
            system=SYSTEM_TAGGING,
        )

        assert isinstance(result, TaggingResponse)
        returned_indices = {r.index for r in result.results}
        expected_indices = set(range(len(real_candidates)))
        missing = expected_indices - returned_indices
        assert not missing, (
            f"Gemini nie otagował {len(missing)} kandydatów — indeksy: {sorted(missing)}"
        )
