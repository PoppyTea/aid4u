"""
S03E01 — evaluation

10 000 odczytów sensorów elektrowni; zgłoś ID plików zawierających anomalie. Cztery
reguły (`doc/zadanie.md`) zwijają się algebraicznie: niech `data_bad` = reguła #1 ∨ #4
(obie deterministyczne — `readings.py`), `note_failure` = notatka zgłasza problem.
Reguła #2 (operator mówi OK, dane złe) = `¬note_failure ∧ data_bad` jest PODZBIOREM
`data_bad` — wnosi zero nowych ID. Zostaje:

    anomalia = data_bad ∨ note_failure

Konsekwencja: LLM nigdy nie widzi odczytu i nigdy nie porównuje notatki z danymi —
klasyfikuje wyłącznie unikalne FRAZY notatek (~261 z ~9953, patrz
`doc/community_notes.md`). To jest cały powód, dla którego budżet <2 centy jest
osiągalny, i jednocześnie strukturalne usunięcie pułapki pojęciowej #3 (plik z
idealnymi danymi, ale notatką o awarii, WCIĄŻ jest anomalią) — nie ma miejsca w
kodzie, w którym dałoby się ją przeoczyć.

Kontrakt jednostrzałowy: treść zadania wymaga "w jednym zapytaniu" kompletnej listy
ID, więc `solve()` NIE prowadzi własnej pętli `/verify` — `BaseTask.run()` wysyła
odpowiedź dokładnie raz (A1, `core/tasks/base.py:119`, tu nie dotyczy).

Nazwa zadania w hubie: evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path

import logfire
from pydantic import BaseModel, Field

from core.llm.types import LLMMessage
from core.net import expect_binary
from core.observability.prompts import sync_prompt
from core.tasks import BaseTask, task
from tasks.s03e01_evaluation import notes as notes_mod
from tasks.s03e01_evaluation import readings as readings_mod
from tasks.s03e01_evaluation.prompts import PROMPT_NAME, SYSTEM_CLASSIFY, build_batch_prompt

_SENSORS_ZIP_PATH = "dane/sensors.zip"
_SENSORS_ZIP_ARCHIVE = Path("data/input/s03e01_evaluation/sensors.zip")
_PHRASE_LABELS_DIR = Path("data/output/s03e01_evaluation")

# Punkty kontrolne z konsensusu społeczności (doc/community_notes.md) — logujemy
# OSTRZEŻENIE, nie wyjątek: chcemy zobaczyć wszystkie liczby naraz, bo interpretują
# się wzajemnie ("46 deterministycznych ale 900 fraz" to inna diagnoza niż "200
# deterministycznych i 261 fraz").
_EXPECTED_DETERMINISTIC = (40, 55)
_EXPECTED_NOTE_ONLY = (3, 12)
_EXPECTED_PHRASES = (200, 350)
_KNOWN_BROKEN_FILTER_COUNTS = (22, 43)


class FailurePhraseIndices(BaseModel):
    """Indeksy fraz (lokalne dla batcha) zgłaszających awarię/problem."""

    indices: list[int] = Field(
        default_factory=list,
        description="Numery pozycji z listy wejściowej (licząc od 0). Wyłącznie liczby — nigdy treść frazy.",
    )


@task("s03e01", hub_name="evaluation")
class EvaluationTask(BaseTask):
    """Wykrywa anomalie w odczytach sensorów — deterministycznie (#1/#4) + LLM na frazach notatek (#2/#3)."""

    def fetch_data(self) -> bytes:
        """
        Pobiera `sensors.zip`. Zapisane raz do `data/input/` (commitowane, patrz
        `data/AGENTS.md`) zamiast `.cache/` (efemeryczny z kontraktu) — jedno małe
        archiwum, nigdy nie rozpakowywane na dysk (`load_readings` czyta w pamięci).
        `expect_binary` jako pierwsza operacja sieciowa — hub potrafi zwrócić
        HTTP 200 + HTML zamiast 404 dla złego adresu (patrz `core/net.py`).
        """
        if _SENSORS_ZIP_ARCHIVE.exists():
            return _SENSORS_ZIP_ARCHIVE.read_bytes()

        raw = self.hub.get_public(_SENSORS_ZIP_PATH)
        expect_binary(raw, "zip", source=_SENSORS_ZIP_PATH)
        _SENSORS_ZIP_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        _SENSORS_ZIP_ARCHIVE.write_bytes(raw)
        return raw

    def solve(self, data: bytes) -> dict:
        """Deterministyczny filtr (#1/#4) → dedup+klasyfikacja LLM fraz (#2/#3) → suma → odpowiedź."""
        all_readings = readings_mod.load_readings(data)
        self._check_id_range(all_readings)
        logfire.info(
            "s03e01_sensor_types",
            histogram=dict(readings_mod.sensor_type_histogram(all_readings)),
        )

        by_range_ids = {r.file_id for r in all_readings if readings_mod.range_violations(r)}
        by_zero_ids = {r.file_id for r in all_readings if readings_mod.zero_violations(r)}
        deterministic_bad_ids = by_range_ids | by_zero_ids

        raw_notes = [r.doc["operator_notes"] for r in all_readings]
        unique_note_groups = notes_mod.unique_notes(raw_notes)
        unique_note_texts = list(unique_note_groups.keys())
        phrase_list = sorted(notes_mod.unique_phrases(unique_note_texts).keys())

        logfire.info(
            "s03e01_dedup",
            raw_notes=len(raw_notes),
            unique_notes=len(unique_note_texts),
            unique_phrases=len(phrase_list),
        )
        if not (_EXPECTED_PHRASES[0] <= len(phrase_list) <= _EXPECTED_PHRASES[1]):
            logfire.warning(
                f"s03e01: {len(phrase_list)} unikalnych fraz poza oczekiwanym zakresem "
                f"{_EXPECTED_PHRASES} — sprawdź regułę podziału (notes.split_phrases)."
            )

        is_failure = self._classify_phrases(phrase_list)

        note_failure_ids: set[str] = set()
        for note, idxs in unique_note_groups.items():
            if notes_mod.note_says_failure(note, is_failure):
                note_failure_ids.update(all_readings[idx].file_id for idx in idxs)

        by_note_only_ids = note_failure_ids - deterministic_bad_ids
        anomaly_ids = deterministic_bad_ids | note_failure_ids

        logfire.info(
            "s03e01_counts",
            by_range=len(by_range_ids),
            by_zero_violation=len(by_zero_ids),
            deterministic_total=len(deterministic_bad_ids),
            by_note_only=len(by_note_only_ids),
            total_anomalies=len(anomaly_ids),
        )
        self._check_counts(deterministic_bad_ids, by_note_only_ids, anomaly_ids)

        return {"recheck": sorted(anomaly_ids, key=int)}

    def _classify_phrases(self, phrases: list[str]) -> dict[str, bool]:
        """
        Klasyfikuje unikalne frazy jako failure/nie-failure. Cache PER (MODEL, FRAZA)
        (`core/hub/cache.py`), nie per batch — zmiana `_BATCH_SIZE` albo reguły
        podziału unieważniłaby wszystkie klucze per-batch, ale nie per-frazę.

        Model wchodzi w klucz celowo: etykieta ZALEŻY od modelu (to jest cały sens
        A/B — Haiku i Gemini mogą się nie zgadzać na tej samej frazie), więc klucz
        bez modelu byłby zwyczajnie niepoprawnym cache'owaniem — przełączenie modelu
        po cichu czytałoby etykiety innego modelu zamiast klasyfikować ponownie.
        """
        model_prefix = f"phrase-label:{self.llm.model}:"
        is_failure: dict[str, bool] = {}
        to_classify: list[str] = []
        for phrase in phrases:
            cached = self.cache.get(f"{model_prefix}{phrase}")
            if cached is not None:
                is_failure[phrase] = cached == b"1"
            else:
                to_classify.append(phrase)

        logfire.info(
            "s03e01_cache",
            total_phrases=len(phrases),
            cached=len(phrases) - len(to_classify),
            to_classify=len(to_classify),
        )

        if to_classify:
            sync_prompt(PROMPT_NAME, SYSTEM_CLASSIFY)
            for batch in notes_mod.batches(to_classify):
                response = self.llm.structured(
                    [LLMMessage.user(build_batch_prompt(batch))],
                    FailurePhraseIndices,
                    system=SYSTEM_CLASSIFY,
                    prompt_name=PROMPT_NAME,
                )
                failing = set(notes_mod.map_local_indices(response.indices, batch))
                for phrase in batch:
                    label = phrase in failing
                    is_failure[phrase] = label
                    self.cache.set(f"{model_prefix}{phrase}", b"1" if label else b"0")

        self._save_phrase_labels_artifact(is_failure, model=self.llm.model)
        return is_failure

    @staticmethod
    def _check_id_range(all_readings: list[readings_mod.Reading]) -> None:
        """Loguje (nie rzuca) zakres/liczbę ID — sanity PRZED jakimkolwiek wywołaniem LLM."""
        ids = sorted(int(r.file_id) for r in all_readings)
        expected = list(range(1, len(ids) + 1))
        logfire.info(
            "s03e01_ids",
            count=len(ids),
            min_id=ids[0] if ids else None,
            max_id=ids[-1] if ids else None,
            forms_contiguous_range_from_1=(ids == expected),
        )
        if ids != expected:
            logfire.warning(
                "s03e01: ID plików NIE tworzą ciągłego zakresu 1..N — sprawdź parsowanie nazw plików."
            )

    @staticmethod
    def _check_counts(
        deterministic_bad_ids: set[str], by_note_only_ids: set[str], anomaly_ids: set[str]
    ) -> None:
        """Punkty kontrolne z `doc/community_notes.md` jako ostrzeżenia, nigdy wyjątki."""
        if not (_EXPECTED_DETERMINISTIC[0] <= len(deterministic_bad_ids) <= _EXPECTED_DETERMINISTIC[1]):
            hint = (
                " (dokładnie 22 albo 43 — znany, nazwany tryb awarii filtru "
                "deterministycznego, patrz doc/community_notes.md)"
                if len(deterministic_bad_ids) in _KNOWN_BROKEN_FILTER_COUNTS
                else ""
            )
            logfire.warning(
                f"s03e01: {len(deterministic_bad_ids)} anomalii deterministycznych poza "
                f"oczekiwanym zakresem {_EXPECTED_DETERMINISTIC}{hint}"
            )
        if not (_EXPECTED_NOTE_ONLY[0] <= len(by_note_only_ids) <= _EXPECTED_NOTE_ONLY[1]):
            logfire.warning(
                f"s03e01: {len(by_note_only_ids)} anomalii tylko-z-notatek poza oczekiwanym "
                f"zakresem {_EXPECTED_NOTE_ONLY} — setki sugerują zbyt luźny prompt klasyfikacji."
            )
        if len(anomaly_ids) >= 100:
            logfire.warning(f"s03e01: {len(anomaly_ids)} anomalii łącznie — sprawdź czy prompt nie jest zbyt luźny.")

    @staticmethod
    def _save_phrase_labels_artifact(is_failure: dict[str, bool], *, model: str) -> None:
        """
        Dubluje mapowanie fraza→etykieta do `data/output/` — `.cache/` jest z kontraktu
        efemeryczny (wolno go skasować), to jest trwała, przeglądalna kopia.

        Nazwa pliku zawiera model (jak klucz cache'a w `_classify_phrases`) — inaczej
        drugi przebieg A/B (inny model) nadpisałby etykiety pierwszego, uniemożliwiając
        realne porównanie.
        """
        path = _PHRASE_LABELS_DIR / f"phrase_labels-{model}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(is_failure, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        logfire.info(f"Zapisano etykiety fraz: {path}")
