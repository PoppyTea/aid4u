from __future__ import annotations
from typing import Annotated
from pydantic import BaseModel, Field
import math

class GeoPoint(BaseModel):
    latitude: Annotated[float| None, Field(ge=-90, le=90)]
    longitude: Annotated[float | None, Field(ge=-180, le=180)]

    def distance_to(self, target:GeoPoint):
        if self == target:
            distance:float = 0.0
        else:
            # Promień Ziemi w kilometrach
            R: float = 6356.4445

            lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
            lat2, lon2 = math.radians(target.latitude), math.radians(target.longitude)

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = R * c
        return distance

class PowerPlant(BaseModel):
    location_name: Annotated[str, Field(frozen=True)]
    location: Annotated[GeoPoint| str | None, Field()]
    uuid: Annotated[str,Field(frozen=True)]
    power_level: Annotated[int,Field(frozen=True)]
    active: Annotated[bool, Field(frozen=True, default=True)]

    def nearest_suspect(self, suspect: Suspect):
        """
        Oblicza po kolei odległości pomiędzy daną elektrownią,
        a wszystkimi GeoPoints z LocationHistory podejrzanego.
        Zwraca tylko elektrownię, ktra uzyskała najniższą
        odległość od podejrzanego i zwraca słownik z uuid elektrowni, imieniem, nazwiskiem podejrzanego i odległością
        """
        pass

class Suspect(BaseModel):
    name: Annotated[str,Field(frozen=True)]
    surname: Annotated[str,Field(frozen=True)]
    born: Annotated[int,Field(frozen=True)]
    age: int|None|str
    locations_history=Field(default_factory=list[GeoPoint])
    access_lvl: Annotated[int, Field(True)]
