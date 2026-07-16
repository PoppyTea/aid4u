"""
S01E01 — people

Pobierz listę osób z people.csv, przefiltruj według kryteriów
(mężczyźni, 20-40 lat w 2026, urodzeni w Grudziądzu),
otaguj zawody przez LLM i wyślij tych z tagiem 'transport'.

Nazwa zadania w hubie: people
"""
from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any

from pydantic import BaseModel

from core.tasks import BaseTask, task
from tasks.s01e01_people.prompts import SYSTEM_TAGGING, USER_TAGGING

REFERENCE_YEAR = 2026
MIN_AGE, MAX_AGE = 20, 40
TARGET_CITY = "Grudziądz"
TARGET_GENDER = "M"
TARGET_TAG = "transport"


# ─── Pydantic schema dla structured output ───────────────────────────────────

class TaggedJob(BaseModel):
    index: int
    tags: list[str]


class TaggingResponse(BaseModel):
    results: list[TaggedJob]


# ─── Czyste funkcje (łatwe do testowania jednostkowego) ──────────────────────

def parse_csv(raw: bytes) -> list[dict]:
    """Parsuje surowe bajty CSV do listy słowników."""
    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(StringIO(text))
    return list(reader)


def _get_birth_year(person: dict) -> int:
    """
    Wyciąga rok urodzenia niezależnie od formatu źródła:
    - "born" / "year_of_birth" → już sam rok (np. "1990")
    - "birthDate" → pełna data ISO (np. "1975-07-07") — bierzemy część przed '-'
    """
    raw = person.get("born") or person.get("year_of_birth") or person.get("birthDate")
    if not raw:
        return 0
    return int(str(raw).split("-")[0])


def _get_city(person: dict) -> str:
    """Pobiera miasto z pliku csv z zadania.
    Uzasadnienie: Miasto bywa pod kluczem 'city' (dane testowe) albo 'birthPlace' (dane z huba)."""
    val = person.get("city") or person.get("birthPlace") or ""
    return str(val).strip()


def filter_candidates(people: list[dict]) -> list[dict]:
    """
    Filtruje osoby według kryteriów zadania.
    Czysta funkcja — idealna do unit testów bez mocków.
    """
    result = []
    for person in people:
        try:
            born = _get_birth_year(person)
            age = REFERENCE_YEAR - born
            gender = person.get("gender", "").strip().upper()
            city = _get_city(person)
        except (ValueError, TypeError):
            continue

        if gender == TARGET_GENDER and city == TARGET_CITY and MIN_AGE <= age <= MAX_AGE:
            result.append(person)

    return result


def build_tagging_prompt(people: list[dict]) -> str:
    """Buduje JSON z zawodami do otagowania przez LLM."""
    jobs = [
        {"index": i, "job": p.get("job", "")}
        for i, p in enumerate(people)
    ]
    return USER_TAGGING.format(jobs_json=json.dumps(jobs, ensure_ascii=False, indent=2))


def apply_tags(people: list[dict], tagged: list[TaggedJob]) -> list[dict]:
    """Łączy listę osób z wynikami tagowania."""
    tags_by_index = {t.index: t.tags for t in tagged}
    result = []
    for i, person in enumerate(people):
        result.append({**person, "tags": tags_by_index.get(i, [])})
    return result


def filter_by_tag(people: list[dict], tag: str) -> list[dict]:
    """Zostawia tylko osoby posiadające dany tag."""
    return [p for p in people if tag in p.get("tags", [])]


def format_answer(people: list[dict]) -> list[dict]:
    """Formatuje odpowiedź w strukturze wymaganej przez hub."""
    return [
        {
            "name": p.get("name", ""),
            "surname": p.get("surname", ""),
            "gender": p.get("gender", ""),
            "born": _get_birth_year(p),
            "city": _get_city(p),
            "tags": p.get("tags", []),
        }
        for p in people
    ]


# ─── Task ─────────────────────────────────────────────────────────────────────

@task("s01e01", hub_name="people")
class PeopleTask(BaseTask):

    def fetch_data(self) -> bytes:
        return self.cache.get_or_fetch(
            "people.csv",
            lambda: self.hub.get_data("people.csv"),
        )

    def solve(self, data: bytes) -> Any:
        # 1. Parse
        all_people = parse_csv(data)

        # 2. Filter by demographics
        candidates = filter_candidates(all_people)
        if not candidates:
            raise ValueError("Brak kandydatów po filtracji — sprawdź kryteria")

        # 3. Tag jobs via LLM (structured output)
        from core.llm import LLMMessage
        prompt = build_tagging_prompt(candidates)
        tagged_response = self.llm.structured(
            [LLMMessage.user(prompt)],
            TaggingResponse,
            system=SYSTEM_TAGGING,
        )

        # 4. Apply tags + filter by "transport"
        with_tags = apply_tags(candidates, tagged_response.results)
        transport_people = filter_by_tag(with_tags, TARGET_TAG)

        return format_answer(transport_people)
