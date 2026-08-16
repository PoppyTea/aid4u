"""
Testy s03e01 — po działającym rozwiązaniu (weryfikacja przez `--dry-run`/hub liczy
się bardziej niż testy jednostkowe, patrz `tasks/AGENTS.md`). Zero wywołań LLM —
`_classify_phrases` nie jest tu testowane (wymagałoby mocka `LLMClient`), tylko
czyste funkcje deterministyczne i kompozycja fraz→notatek.

Kontrakt nie był znany z góry — trzeba było go odkryć z realnych danych (nazwy
plików w archiwum, komplet tokenów `sensor_type`, separatory w notatkach), więc
te testy zamrażają fakty potwierdzone `--dry-run`em na żywych danych, nie
przypuszczenia sprzed ich obejrzenia.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from tasks.s03e01_evaluation import notes as notes_mod
from tasks.s03e01_evaluation import readings as readings_mod


def _make_reading(
    *,
    file_id: str = "0001",
    sensor_type: str = "temperature",
    # Domyślnie WSZYSTKO zero, zgodnie ze specyfikacją ("dla sensorów nieaktywnych
    # wartość powinna być ustawiona na 0") — testy dopisują jawnie tylko pola, które
    # mają być aktywne. Domyślne temperature_K=600 (poprzednia wersja) po cichu
    # psuło testy innych sensor_type, bo temperature_K stawało się "nieaktywnym
    # polem ≠ 0" wszędzie, gdzie test go nie nadpisał.
    temperature_K: float = 0,
    pressure_bar: float = 0,
    water_level_meters: float = 0,
    voltage_supply_v: float = 0,
    humidity_percent: float = 0,
    operator_notes: str = "Readings look stable.",
) -> readings_mod.Reading:
    return readings_mod.Reading(
        file_id=file_id,
        doc={
            "sensor_type": sensor_type,
            "timestamp": 1774064280,
            "temperature_K": temperature_K,
            "pressure_bar": pressure_bar,
            "water_level_meters": water_level_meters,
            "voltage_supply_v": voltage_supply_v,
            "humidity_percent": humidity_percent,
            "operator_notes": operator_notes,
        },
    )


class TestActiveFields:
    def test_single_sensor(self):
        assert readings_mod.active_fields("temperature") == ["temperature_K"]

    def test_integrated_sensor_splits_on_slash(self):
        assert readings_mod.active_fields("voltage/temperature") == [
            "voltage_supply_v",
            "temperature_K",
        ]

    def test_unknown_token_is_a_hard_error(self):
        """Nieznany token sensor_type MUSI rzucić, nie zostać po cichu pominięty —
        inaczej literówka w danych zamieniłaby się w niewykrytą anomalię reguły #4."""
        with pytest.raises(KeyError):
            readings_mod.active_fields("radiation")


class TestRangeViolations:
    def test_in_range_reading_has_no_violations(self):
        reading = _make_reading(sensor_type="temperature", temperature_K=600)
        assert readings_mod.range_violations(reading) == []

    def test_out_of_range_active_field_is_a_violation(self):
        reading = _make_reading(sensor_type="temperature", temperature_K=1200)
        assert readings_mod.range_violations(reading) == ["temperature_K"]

    def test_only_active_fields_are_checked(self):
        """Pole NIEAKTYWNE poza zakresem (gdyby ktoś tam coś wpisał) nie jest regułą #1
        — to domena reguły #4 (zero_violations), nie range_violations."""
        reading = _make_reading(sensor_type="temperature", temperature_K=600, pressure_bar=999)
        assert readings_mod.range_violations(reading) == []


class TestZeroViolations:
    def test_clean_reading_has_no_violations(self):
        reading = _make_reading(sensor_type="temperature", temperature_K=600)
        assert readings_mod.zero_violations(reading) == []

    def test_inactive_field_nonzero_is_a_violation(self):
        """Czujnik zwraca dane, których nie powinien — reguła #4 dosłownie z treści zadania."""
        reading = _make_reading(sensor_type="water", water_level_meters=10.0, voltage_supply_v=230.4)
        assert readings_mod.zero_violations(reading) == ["voltage_supply_v"]

    def test_multi_sensor_only_flags_truly_inactive_fields(self):
        """Czujnik wielozadaniowy (2-3 pola aktywne) — voltage/temperature aktywne,
        pressure/water/humidity nieaktywne i muszą być zerem."""
        reading = _make_reading(
            sensor_type="voltage/temperature",
            temperature_K=600,
            voltage_supply_v=230.0,
            pressure_bar=0,
            water_level_meters=0,
            humidity_percent=5,  # jedyne nieaktywne pole ≠ 0
        )
        assert readings_mod.zero_violations(reading) == ["humidity_percent"]


class TestDataIsBad:
    def test_perfect_data_with_failure_note_is_still_flagged_by_data_is_bad_as_false(self):
        """`data_is_bad` widzi TYLKO liczby — sam nie wykrywa pułapki #3. To solution.py,
        przez sumę `data_bad ∨ note_failure`, dopiero łapie plik z dobrymi danymi i złą
        notatką. Ten test dokumentuje granicę odpowiedzialności modułu, nie luki w nim."""
        reading = _make_reading(
            sensor_type="temperature", temperature_K=600, operator_notes="Critical failure detected."
        )
        assert readings_mod.data_is_bad(reading) is False

    def test_range_violation_makes_it_bad(self):
        reading = _make_reading(sensor_type="temperature", temperature_K=1200)
        assert readings_mod.data_is_bad(reading) is True

    def test_zero_violation_makes_it_bad(self):
        reading = _make_reading(sensor_type="water", water_level_meters=10.0, voltage_supply_v=1.0)
        assert readings_mod.data_is_bad(reading) is True


class TestLoadReadings:
    def test_file_id_keeps_zero_padding_verbatim(self):
        """ID plików liczone od 1, zero-padded (`0001.json`) — konwersja przez
        int()->str() by je po cichu ścięła. `load_readings` musi zostawić string as-is."""
        payload = _make_reading(file_id="ignored").doc
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("0001.json", __import__("json").dumps(payload))
            zf.writestr("0042.json", __import__("json").dumps(payload))

        result = readings_mod.load_readings(buf.getvalue())

        assert {r.file_id for r in result} == {"0001", "0042"}

    def test_ignores_non_json_members(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("0001.json", __import__("json").dumps(_make_reading().doc))
            zf.writestr("README.txt", "not a reading")

        result = readings_mod.load_readings(buf.getvalue())

        assert len(result) == 1


class TestSplitPhrases:
    def test_splits_on_commas(self):
        assert notes_mod.split_phrases("pressure nominal, temperature nominal") == [
            "pressure nominal",
            "temperature nominal",
        ]

    def test_no_comma_returns_single_phrase(self):
        assert notes_mod.split_phrases("all clear") == ["all clear"]

    def test_strips_whitespace_and_drops_empty_phrases(self):
        assert notes_mod.split_phrases("  ok  , , still ok ") == ["ok", "still ok"]

    def test_never_splits_on_spaces(self):
        """Krytyczne dla zasięgu negacji — 'no leak detected' musi zostać jedną frazą."""
        assert notes_mod.split_phrases("no leak detected") == ["no leak detected"]


class TestUniqueNotesAndPhrases:
    def test_unique_notes_groups_by_normalised_text(self):
        raw = ["All OK", "all ok", "  ALL   OK  ", "Different note"]
        grouped = notes_mod.unique_notes(raw)
        assert len(grouped) == 2
        assert grouped["all ok"] == [0, 1, 2]

    def test_unique_phrases_maps_phrase_to_containing_notes(self):
        notes = ["pressure nominal, temperature nominal", "temperature nominal"]
        phrases = notes_mod.unique_phrases(notes)
        assert phrases["temperature nominal"] == set(notes)
        assert phrases["pressure nominal"] == {notes[0]}


class TestMapLocalIndices:
    def test_valid_indices_map_back_to_phrases(self):
        batch = ["a", "b", "c"]
        assert notes_mod.map_local_indices([0, 2], batch) == ["a", "c"]

    def test_out_of_range_index_is_dropped_not_raised(self):
        """Model, który zwróci indeks spoza zakresu (halucynacja), nie może po cichu
        skazić zbioru anomalii — ani wysadzić programu."""
        batch = ["a", "b"]
        assert notes_mod.map_local_indices([0, 99], batch) == ["a"]

    def test_non_int_index_is_dropped(self):
        batch = ["a", "b"]
        assert notes_mod.map_local_indices([0, "b"], batch) == ["a"]  # type: ignore[list-item]


class TestNoteSaysFailure:
    def test_true_when_any_phrase_is_a_failure(self):
        is_failure = {"clean": False, "failure": True}
        assert notes_mod.note_says_failure("clean, failure", is_failure) is True

    def test_false_when_all_phrases_are_clean(self):
        is_failure = {"clean": False, "also clean": False}
        assert notes_mod.note_says_failure("clean, also clean", is_failure) is False

    def test_unknown_phrase_defaults_to_not_failure(self):
        """Fraza spoza słownika (np. odrzucona przez map_local_indices) domyślnie NIE
        zgłasza problemu — fail-safe w stronę mniejszej liczby fałszywych trafień,
        zgodnie z ostrzeżeniem 'setki ⇒ prompt za luźny' z doc/community_notes.md."""
        assert notes_mod.note_says_failure("nieznana fraza", {}) is False


class TestAnomalyUnionComposition:
    """
    Odtwarza dokładnie kompozycję z `solution.py: solve()` —
    `anomalia = data_bad ∨ note_failure` — na garści syntetycznych odczytów, bez
    mockowania `EvaluationTask`/`BaseTask` (wymagałoby `hub`/`llm`/`cache`, a to jest
    czysto logika kompozycji, nie orkiestracja I/O).

    `test_perfect_data_with_failure_note_is_anomaly` to nazwany test na pułapkę
    pojęciową #3 z `doc/community_notes.md` — najczęstszą pomyłkę w komentarzach
    społeczności: plik z idealnymi odczytami, ale notatką o awarii, WCIĄŻ jest
    anomalią. Broni się sam, bo suma jest strukturalna — nie ma gdzie tej reguły
    przeoczyć w kodzie.
    """

    @staticmethod
    def _anomaly_ids(readings: list[readings_mod.Reading], is_failure: dict[str, bool]) -> set[str]:
        """`is_failure` musi być kluczowane frazami wyciętymi z ZNORMALIZOWANEJ notatki —
        dokładnie jak w `solve()` (`unique_notes()` normalizuje, dopiero potem
        `unique_phrases()` dzieli na frazy). Stąd `normalise()` tutaj, nie surowy tekst."""
        deterministic_bad = {r.file_id for r in readings if readings_mod.data_is_bad(r)}
        note_failure = {
            r.file_id
            for r in readings
            if notes_mod.note_says_failure(notes_mod.normalise(r.doc["operator_notes"]), is_failure)
        }
        return deterministic_bad | note_failure

    def test_perfect_data_with_failure_note_is_anomaly(self):
        reading = _make_reading(
            sensor_type="temperature", temperature_K=600, operator_notes="Critical failure detected."
        )
        assert readings_mod.data_is_bad(reading) is False  # dane same w sobie: czyste

        is_failure = {"critical failure detected.": True}
        anomalies = self._anomaly_ids([reading], is_failure)

        assert reading.file_id in anomalies  # ale suma i tak go łapie

    def test_bad_data_with_clean_note_is_still_anomaly(self):
        """Symetryczny przypadek — reguła #2 (operator mówi OK, dane złe). Wnosi zero
        NOWYCH ID względem `data_is_bad` samego, ale union i tak musi go zawierać."""
        reading = _make_reading(
            sensor_type="temperature", temperature_K=1200, operator_notes="All good."
        )
        is_failure = {"all good.": False}

        anomalies = self._anomaly_ids([reading], is_failure)

        assert reading.file_id in anomalies

    def test_clean_data_and_clean_note_is_not_an_anomaly(self):
        reading = _make_reading(sensor_type="temperature", temperature_K=600, operator_notes="All good.")
        is_failure = {"all good.": False}

        anomalies = self._anomaly_ids([reading], is_failure)

        assert anomalies == set()
