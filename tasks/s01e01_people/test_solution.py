"""
Testy dla S01E01 — people.

Dwie warstwy:
  - Unit testy (szybkie, offline, mock LLM) — domyślnie uruchamiane
  - Integration test (wymaga kluczy, sieci) — tylko z flagą: pytest -m integration

TDD workflow z Claude Code:
  1. Napisz test opisujący zachowanie (co, nie jak)
  2. Uruchom: uv run pytest tasks/s01e01_people/ -v → RED
  3. Zaimplementuj minimum kodu żeby test przeszedł → GREEN
  4. Refaktoryzuj → GREEN
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tasks.s01e01_people.solution import (
    MAX_AGE,
    MIN_AGE,
    REFERENCE_YEAR,
    TaggedJob,
    _get_birth_year,
    apply_tags,
    filter_by_tag,
    filter_candidates,
    format_answer,
    parse_csv,
)

REAL_PEOPLE_CSV = Path(__file__).resolve().parents[2] / "data" / "main_story" / "people.csv"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_CSV = """\
name,surname,gender,born,city,job
Jan,Kowalski,M,1990,Grudziądz,kierowca TIR-a
Anna,Nowak,F,1995,Warszawa,lekarz
Piotr,Wiśniewki,M,1985,Grudziądz,operator koparki
Maria,Wójcik,F,1992,Grudziądz,nauczycielka
Tomasz,Zieliński,M,2000,Grudziądz,programista
Krzysztof,Dąbrowski,M,1980,Grudziądz,spedytor
Marek,Lewandowski,M,1988,Gdańsk,kierowca autobusu
""".encode("utf-8")


@pytest.fixture
def sample_people() -> list[dict]:
    return parse_csv(SAMPLE_CSV)


@pytest.fixture
def filtered_people(sample_people) -> list[dict]:
    return filter_candidates(sample_people)


@pytest.fixture
def real_people() -> list[dict]:
    """Parsuje faktyczny people.csv z huba (data/main_story/), nie mockową fixturę."""
    return parse_csv(REAL_PEOPLE_CSV.read_bytes())


# ─── parse_csv ────────────────────────────────────────────────────────────────


class TestParseCsv:
    def test_returns_list_of_dicts(self):
        result = parse_csv(SAMPLE_CSV)
        assert isinstance(result, list)
        assert all(isinstance(p, dict) for p in result)

    def test_correct_number_of_rows(self):
        result = parse_csv(SAMPLE_CSV)
        assert len(result) == 7

    def test_has_required_fields(self):
        result = parse_csv(SAMPLE_CSV)
        assert {"name", "surname", "gender", "born", "city", "job"}.issubset(result[0].keys())

    def test_handles_utf8_encoding(self):
        result = parse_csv(SAMPLE_CSV)
        cities = {p["city"] for p in result}
        assert "Grudziądz" in cities

    def test_handles_empty_csv(self):
        result = parse_csv(b"name,surname\n")
        assert result == []


# ─── filter_candidates ───────────────────────────────────────────────────────


class TestFilterCandidates:
    def test_keeps_only_males(self, sample_people):
        result = filter_candidates(sample_people)
        assert all(p["gender"].upper() == "M" for p in result)

    def test_keeps_only_grudziądz(self, sample_people):
        result = filter_candidates(sample_people)
        assert all(p["city"] == "Grudziądz" for p in result)

    def test_age_range_lower_bound(self):
        # 2026 - 2006 = 20 → minimalny wiek, powinien przejść
        people = [
            {
                "name": "X",
                "surname": "Y",
                "gender": "M",
                "born": "2006",
                "city": "Grudziądz",
                "job": "test",
            }
        ]
        assert len(filter_candidates(people)) == 1

    def test_age_range_upper_bound(self):
        # 2026 - 1986 = 40 → maksymalny wiek, powinien przejść
        people = [
            {
                "name": "X",
                "surname": "Y",
                "gender": "M",
                "born": "1986",
                "city": "Grudziądz",
                "job": "test",
            }
        ]
        assert len(filter_candidates(people)) == 1

    def test_too_old_excluded(self):
        # 2026 - 1985 = 41 → za stary
        people = [
            {
                "name": "X",
                "surname": "Y",
                "gender": "M",
                "born": "1985",
                "city": "Grudziądz",
                "job": "test",
            }
        ]
        assert len(filter_candidates(people)) == 0

    def test_too_young_excluded(self):
        # 2026 - 2007 = 19 → za młody
        people = [
            {
                "name": "X",
                "surname": "Y",
                "gender": "M",
                "born": "2007",
                "city": "Grudziądz",
                "job": "test",
            }
        ]
        assert len(filter_candidates(people)) == 0

    def test_wrong_city_excluded(self, sample_people):
        # Marek Lewandowski jest z Gdańska
        result = filter_candidates(sample_people)
        names = [p["name"] for p in result]
        assert "Marek" not in names

    def test_female_excluded(self, sample_people):
        result = filter_candidates(sample_people)
        assert all(p["name"] != "Anna" for p in result)
        assert all(p["name"] != "Maria" for p in result)

    def test_returns_correct_count(self, sample_people):
        # Jan (1990, M, Grudziądz) → OK
        # Piotr (1985, M, Grudziądz) → za stary (41)
        # Tomasz (2000, M, Grudziądz) → OK
        # Krzysztof (1980, M, Grudziądz) → za stary (46)
        result = filter_candidates(sample_people)
        assert len(result) == 2

    def test_handles_invalid_born(self):
        people = [
            {
                "name": "X",
                "surname": "Y",
                "gender": "M",
                "born": "nie-liczba",
                "city": "Grudziądz",
                "job": "test",
            }
        ]
        result = filter_candidates(people)
        assert result == []


# ─── filter_candidates na realnych danych (people.csv) ───────────────────────
#
# Diagnostyka s01e01: hipoteza była, że problem leży w warstwie sortowania
# people.csv (druga hipoteza — komunikacja z Gemini — wymaga klucza API i nie
# jest tu testowalna). Ten test sprawdza, czy filter_candidates zachowuje
# oryginalną kolejność wierszy z pliku, czy gdzieś je przestawia — bo
# apply_tags łączy wyniki tagowania z kandydatami po indeksie, więc jakiekolwiek
# resortowanie między filtrowaniem a tagowaniem rozjeżdża przypisanie tagów.


class TestFilterCandidatesRealData:
    def test_real_csv_parses(self, real_people):
        assert len(real_people) > 0
        assert {"name", "surname", "gender", "birthDate", "birthPlace", "job"}.issubset(
            real_people[0].keys()
        )

    def test_returns_some_candidates(self, real_people):
        result = filter_candidates(real_people)
        assert len(result) > 0, (
            "Brak kandydatów na realnym people.csv — sprawdź kryteria filtrowania"
        )

    def test_preserves_original_row_order(self, real_people):
        """filter_candidates nie może przestawiać wierszy względem kolejności w CSV."""
        result = filter_candidates(real_people)
        indices = []
        iterator = enumerate(real_people)
        for p in result:
            idx = next(
                i
                for i, orig in enumerate(real_people[search_start:], start=search_start)
                if orig == p
            )
            indices.append(idx)
            search_start = idx + 1
        assert indices == sorted(indices), (
            "Kolejność kandydatów rozjechała się z kolejnością w people.csv"
        )

    def test_candidates_match_filter_criteria(self, real_people):
        """Każdy kandydat realnie spełnia kryteria (płeć/miasto/wiek) — nie tylko liczba się zgadza."""
        result = filter_candidates(real_people)
        for person in result:
            assert person["gender"].strip().upper() == "M"
            assert person.get("city") or person.get("birthPlace")
            assert (person.get("city") or person.get("birthPlace")).strip() == "Grudziądz"
            born = _get_birth_year(person)
            assert MIN_AGE <= REFERENCE_YEAR - born <= MAX_AGE


# ─── apply_tags ──────────────────────────────────────────────────────────────


class TestApplyTags:
    def test_applies_tags_by_index(self):
        people = [{"name": "Jan"}, {"name": "Anna"}]
        tagged = [TaggedJob(index=0, tags=["transport"]), TaggedJob(index=1, tags=["medycyna"])]
        result = apply_tags(people, tagged)
        assert result[0]["tags"] == ["transport"]
        assert result[1]["tags"] == ["medycyna"]

    def test_missing_index_gets_empty_tags(self):
        people = [{"name": "Jan"}, {"name": "Anna"}]
        tagged = [TaggedJob(index=0, tags=["transport"])]
        result = apply_tags(people, tagged)
        assert result[1]["tags"] == []

    def test_preserves_original_fields(self):
        people = [{"name": "Jan", "city": "Grudziądz"}]
        tagged = [TaggedJob(index=0, tags=["transport"])]
        result = apply_tags(people, tagged)
        assert result[0]["city"] == "Grudziądz"
        assert result[0]["name"] == "Jan"


# ─── filter_by_tag ────────────────────────────────────────────────────────────


class TestFilterByTag:
    def test_keeps_matching_tag(self):
        people = [
            {"name": "Jan", "tags": ["transport", "praca z pojazdami"]},
            {"name": "Anna", "tags": ["medycyna"]},
        ]
        result = filter_by_tag(people, "transport")
        assert len(result) == 1
        assert result[0]["name"] == "Jan"

    def test_empty_when_no_match(self):
        people = [{"name": "Anna", "tags": ["medycyna"]}]
        assert filter_by_tag(people, "transport") == []

    def test_empty_tags_excluded(self):
        people = [{"name": "Jan", "tags": []}]
        assert filter_by_tag(people, "transport") == []


# ─── format_answer ────────────────────────────────────────────────────────────


class TestFormatAnswer:
    def test_output_has_required_fields(self):
        people = [
            {
                "name": "Jan",
                "surname": "K",
                "gender": "M",
                "born": "1990",
                "city": "Grudziądz",
                "tags": ["transport"],
            }
        ]
        result = format_answer(people)
        assert result[0].keys() == {"name", "surname", "gender", "born", "city", "tags"}

    def test_born_is_int(self):
        people = [
            {
                "name": "Jan",
                "surname": "K",
                "gender": "M",
                "born": "1990",
                "city": "Grudziądz",
                "tags": [],
            }
        ]
        result = format_answer(people)
        assert isinstance(result[0]["born"], int)

    def test_empty_input_returns_empty(self):
        assert format_answer([]) == []


# ─── Integration test ─────────────────────────────────────────────────────────


@pytest.mark.integration
def test_full_solution_against_hub():
    """
    Pełne E2E: pobiera dane z hubu, taguje przez Anthropic, submituje.
    Uruchom świadomie: uv run pytest -m integration tasks/s01e01_people/
    """
    from core.config import get_config
    from core.hub import HubClient
    from core.llm import LLMClient, create_provider
    from core.observability.setup import setup_observability

    setup_observability()
    cfg = get_config()

    hub = HubClient()
    provider = create_provider("gemini-2.5-flash", cfg)
    llm = LLMClient(provider)

    from tasks.s01e01_people.solution import PeopleTask

    task_instance = PeopleTask(hub, llm)
    flag = task_instance.run()

    assert flag is not None, "Nie otrzymano flagi — sprawdź odpowiedź w logach"
    assert flag.startswith("{FLG:") or len(flag) > 3, f"Nieoczekiwany format flagi: {flag}"
