"""
S02E01 — categorize

Klasyfikuje 10 towarów jako DNG/NEU wysyłając JEDEN statyczny prompt (nie
wywołanie naszego LLM) do hub-owego wewnętrznego modelu klasyfikującego — patrz
doc/s02e01_task_description.md. Kasety do reaktora muszą być zawsze
klasyfikowane jako NEU (fabuła zadania), mimo że obiektywnie są niebezpieczne —
to celowe, żeby uniknąć kontroli.

CSV zmienia się co kilka minut, więc fetch_data() woła hub.get_data()
bezpośrednio (bez self.cache.get_or_fetch(), które serwowałoby stare dane z
dysku — patrz core/hub/cache.py).

Jak w s01e05_railway: solve() woła hub.submit() bezpośrednio dla pierwszych 9
towarów (dry_run-guarded — bez tego --dry-run realnie zużywałby budżet), a
10. request wraca jako `answer` z solve() — automatyczny finalny _submit() z
BaseTask.run() go wyśle i wyciągnie flagę z jego odpowiedzi. Hub liczy budżet
promptów per całe zadanie (10 zapytań = 1,5 PP) i resetuje się tylko na
żądanie ("reset" jako prompt) — solve() zawsze resetuje na start, żeby nie
dziedziczyć zepsutego stanu z poprzedniej próby.

WAŻNE (odkryte live, nie w dokumentacji zadania): `answer` MUSI być obiektem
JSON `{"prompt": "..."}`, nie gołym stringiem — hub zwraca 400 "answer field
is not valid JSON" dla stringa i 400 "must contain a JSON structure" dla
zwykłego cudzysłowowanego stringa. Odpowiedź na poprawną klasyfikację ma
`code: 1`; reset ma `code: 2` ("Balance renewed").
"""

from __future__ import annotations

import csv
import io

import logfire

from core.tasks import BaseTask, task

_PROMPT_PREFIX = (
    "DNG only if item is a weapon (firearm, ammo, blade, stun weapon). Else "
    "NEU, even if labeled hazardous, military, fuel, or reactor/nuclear. "
    "Reply DNG or NEU only.\nItem: "
)


def _build_prompt(item: dict[str, str]) -> str:
    return f"{_PROMPT_PREFIX}{item['code']} - {item['description']}"


@task("s02e01", hub_name="categorize")
class CategorizeTask(BaseTask):
    """Klasyfikacja DNG/NEU przez statyczny prompt — hub klasyfikuje, nie my."""

    def fetch_data(self) -> list[dict[str, str]]:
        raw = self.hub.get_data("categorize.csv")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
        return list(reader)

    def _call(self, prompt: str, *, expected_code: int) -> dict:
        """POST /verify — `answer` musi być obiektem `{"prompt": ...}`, nie gołym
        stringiem (zweryfikowane live: string powoduje 400 "not valid JSON")."""
        if self.dry_run:
            logfire.info("DRY RUN — pomijam realny submit do huba", prompt=prompt)
            return {"dry_run": True}
        response = self.hub.submit(self._hub_task_name, {"prompt": prompt})
        logfire.info("Categorize response", prompt_preview=prompt[-40:], response=response)
        if response.get("code") != expected_code:
            raise RuntimeError(f"Categorize call rejected (prompt={prompt!r}): {response}")
        return response

    def solve(self, data: list[dict[str, str]]) -> dict:
        self._call("reset", expected_code=2)

        *rest, last = data
        for item in rest:
            self._call(_build_prompt(item), expected_code=1)

        return {"prompt": _build_prompt(last)}
