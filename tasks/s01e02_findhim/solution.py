from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field, computed_field, field_validator

from core.config import get_config
from core.llm import LLMClient, LLMMessage, create_provider
from tasks.common.const import REFERENCE_YEAR

_llm_client: LLMClient | None = None



def _get_llm_client() -> LLMClient:
    """
    Leniwy singleton LLMClient (gemini-2.5-flash, tier standard — domyślny
    model projektu). PowerPlant nie dostaje klienta wstrzykniętego z zewnątrz,
    bo to zadanie nie ma jeszcze klasy @task(BaseTask) — do rewizji, gdy powstanie.
    """
    global _llm_client
    if _llm_client is None:
        provider = create_provider("gemini-2.5-flash", get_config())
        _llm_client = LLMClient(provider)
    return _llm_client



class GeoPoint(BaseModel):
    name: Annotated[None | str, Field(default=None, description="")] = None
    latitude: Annotated[float | None, Field(ge=-90, le=90, default=None, description="Decimal degrees, up to 6 decimal places. Null if unknown.")]
    longitude: Annotated[float | None, Field(ge=-180, le=180, default=None, description="Decimal degrees, up to 6 decimal places. Null if unknown.")]

    def distance_to(self, target:GeoPoint):
        if self == target:
            distance:float = 0.0
        elif self.latitude and self.longitude and target.latitude and target.longitude is not None:
            # Promień Ziemi w kilometrach
            R: float = 6356.4445

            lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
            lat2, lon2 = math.radians(target.latitude), math.radians(target.longitude)

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = R * c
        else:
            raise ValueError("Neither latitude nor longitude can be None")
        return distance



    def is_nearest_to(self, *other)-> GeoPoint | list[GeoPoint]:
        """
        patrz `test_is_nearest_to_parametrize`, powinien wystarczyć do zaaimplementowania logiki
        1. najniższą wartość znajdź przy pomocy min(set(distances))
        2. pętla po hostorii pobytu:
            - new_distance == lowest_distance -> answer_list.append(location)

            - new_distance < lowest_distance -> answer_list.clear(), answer_list.append(location)

            - new_distance > lowest_distance -> continue
        3. jeśli len(answer_list)=1 to zwróć answer_list[0]
        3.1 jeśli len(answer_list)>1 to zwróć answer_list
        3.2 jeśli len(answer_list)=0 to zwróć false
        """


class NamedPlace(GeoPoint):
    """Kształt odpowiedzi LLM dla pojedynczego zapytania o współrzędne miasta."""
    city_name: str

class PowerPlant(BaseModel):
    location_name: Annotated[str | None, Field(default=None)]
    location: Annotated[GeoPoint | None, Field(default=None)]
    code: Annotated[str | None, Field(default=None)]
    power_level: Annotated[int | None, Field(default=None)]
    active: Annotated[bool | None, Field(default=None)]

    def nearest_suspect(self, suspect: Suspect):
        """
        Oblicza po kolei odległości pomiędzy daną elektrownią,
        a wszystkimi GeoPoints z LocationHistory podejrzanego.
        Zwraca tylko elektrownię, ktra uzyskała najniższą
        odległość od podejrzanego i zwraca słownik z uuid elektrowni, imieniem, nazwiskiem podejrzanego i odległością
        """

    def _geocode_city(self, city_name: str | None)-> GeoPoint | None:
        """
        Pyta LLM o współrzędne miasta (wiedza parametryczna modelu — bez web_search,
        decyzja z 2026-07-20: dla znanych miast search nic nie dodaje, patrz notatka
        w pamięci projektu). Seam do mockowania w testach jednostkowych.
        """
        result = _get_llm_client().structured(
            messages=[LLMMessage.user(f"City: {city_name}")],
            schema=NamedPlace,
            system="Provide geographic coordinates for the given city. If unsure about a city, return null for latitude and longitude.",
        )
        if result.latitude is None or result.longitude is None:
            return None
        return GeoPoint(latitude=result.latitude, longitude=result.longitude)

    def resolve_coordinates(self) -> None:
        """
        Zamienia self.location_name (str) na self.location (GeoPoint | None),
        korzystając z _geocode_city.
        """
        self.location = self._geocode_city(self.location_name)

class Suspect(BaseModel):
    name: Annotated[str,Field(frozen=True)]
    surname: Annotated[str,Field(frozen=True)]
    born: Annotated[int, Field(le=REFERENCE_YEAR, ge=1900)]
    location_history: list[GeoPoint]
    access_lvl: Annotated[int | None, Field(ge=0, le=10)] = None

    @computed_field
    @property
    def age(self) -> int:
        return REFERENCE_YEAR - self.born

    @field_validator("location_history", mode="before")
    @classmethod
    def parse_location_history(cls, v) -> list[GeoPoint]:
        if isinstance(v, Path):
            path = Path(v)
            with open(path, mode="r", encoding="utf-8") as f:
                raw_json = json.load(f)
                return [GeoPoint(**data_point) for data_point in raw_json]
        return v if isinstance(v, list) else []
