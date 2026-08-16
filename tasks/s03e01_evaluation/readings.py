"""
Warstwa deterministyczna — reguły anomalii #1 i #4, zero tokenów LLM.

Progi i mapowanie `sensor_type` → pole są PODANE WPROST w treści zadania
(`doc/zadanie.md`), nie wyprowadzane z danych — w odróżnieniu od zadań, gdzie próg
trzeba odgadnąć profilowaniem rozkładu, tutaj nie ma czego zgadywać.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections import Counter
from dataclasses import dataclass

# Mapowanie tokenu `sensor_type` -> pole, którego dotyczy. Nieznany token to
# TWARDY BŁĄD (KeyError), nie ciche pominięcie — literówka w danych nie może po
# cichu zamienić się w niewykrytą anomalię reguły #4.
_SENSOR_FIELD = {
    "temperature": "temperature_K",
    "pressure": "pressure_bar",
    "water": "water_level_meters",
    "voltage": "voltage_supply_v",
    "humidity": "humidity_percent",
}

# Zakresy poprawnych wartości dla AKTYWNYCH sensorów — z doc/zadanie.md, nie z danych.
_RANGES: dict[str, tuple[float, float]] = {
    "temperature_K": (553, 873),
    "pressure_bar": (60, 160),
    "water_level_meters": (5.0, 15.0),
    "voltage_supply_v": (229.0, 231.0),
    "humidity_percent": (40.0, 80.0),
}

_ALL_FIELDS = tuple(_SENSOR_FIELD.values())


@dataclass(frozen=True)
class Reading:
    """Jeden odczyt sensora — jeden plik JSON z archiwum, plus jego ID."""

    file_id: str
    """Nazwa pliku BEZ rozszerzenia, jako string — NIGDY konwertowana przez
    int()->str() z powrotem, bo to po cichu ścięłoby zera wiodące."""
    doc: dict


def load_readings(zip_bytes: bytes) -> list[Reading]:
    """
    Rozpakowuje `sensors.zip` W PAMIĘCI i parsuje każdy człon `.json` na `Reading`.

    Nigdy `extractall()` — unika path traversal i 10 000 plików na dysku. Wołający
    (patrz `solution.py: fetch_data`) waliduje magic bytes PRZED wywołaniem tej
    funkcji — tu zakładamy, że `zip_bytes` to już potwierdzony ZIP.
    """
    readings: list[Reading] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            if not name.endswith(".json"):
                continue
            file_id = name.rsplit("/", 1)[-1].removesuffix(".json")
            doc = json.loads(archive.read(name))
            readings.append(Reading(file_id=file_id, doc=doc))

    return readings


def sensor_type_histogram(readings: list[Reading]) -> Counter[str]:
    """Histogram wartości `sensor_type` — diagnostyka `--dry-run` i implicit sanity
    check: jeśli pojawi się nieznany token, `active_fields()` i tak rzuci KeyError
    przy pierwszym wywołaniu reguł niżej."""
    return Counter(r.doc["sensor_type"] for r in readings)


def active_fields(sensor_type: str) -> list[str]:
    """
    Rozbija `sensor_type` (np. "voltage/temperature") na listę pól, które ten
    odczyt POWINIEN mierzyć — pozostałe pola MUSZĄ być zerem (reguła #4).
    """
    return [_SENSOR_FIELD[token] for token in sensor_type.split("/")]


def range_violations(reading: Reading) -> list[str]:
    """Reguła #1: pola AKTYWNE (wg `sensor_type`) poza dozwolonym zakresem. Zwraca nazwy pól."""
    violations = []
    for field in active_fields(reading.doc["sensor_type"]):
        lo, hi = _RANGES[field]
        if not (lo <= reading.doc[field] <= hi):
            violations.append(field)
    return violations


def zero_violations(reading: Reading) -> list[str]:
    """Reguła #4: pola NIEAKTYWNE różne od zera — "czujnik zwraca dane, których nie powinien"."""
    active = set(active_fields(reading.doc["sensor_type"]))
    return [field for field in _ALL_FIELDS if field not in active and reading.doc[field] != 0]


def data_is_bad(reading: Reading) -> bool:
    """Suma reguł #1 i #4 — jedyny bit, którego potrzebuje kompozycja z regułami #2/#3
    (patrz `solution.py`: `anomalia = data_bad ∨ note_failure`)."""
    return bool(range_violations(reading) or zero_violations(reading))
