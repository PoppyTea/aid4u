from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, computed_field, field_validator

from core.config import get_config
from core.hub import HubClient
from core.llm import LLMClient, LLMMessage, create_provider
from core.llm.types import Tool
from tasks.common.const import REFERENCE_YEAR
from tasks.s01e02_findhim.prompts import SYSTEM_AGENT_FINDHIM, USER_AGENT_FINDHIM

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GeoPoint):
            return False
        return self.latitude == other.latitude and self.longitude == other.longitude

    def __add__(self: GeoPoint, other: GeoPoint) -> GeoConnection:
        return GeoConnection(alpha_point=self, beta_point=other)

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



    def is_nearest_to(self, *other: GeoPoint | list[GeoPoint]) -> GeoPoint | list[GeoPoint] | None:
        """
        Zwraca wszystkie najbliższe self, unikalne punkty z zadanej puli punktów geograficznych.
        """
        candidates: list[GeoPoint] = []
        for item in other:
            if isinstance(item, list):
                candidates.extend(item)
            else:
                candidates.append(item)

        if not candidates:
            return None

        # Pętla 1: rozdziel kandydatów do kategorii (kubełków) wg dystansu.
        by_distance: dict[float, list[GeoPoint]] = {}
        for point in candidates:
            distance = self.distance_to(point)
            by_distance.setdefault(distance, []).append(point)

        lowest_distance = min(by_distance)
        winners = by_distance[lowest_distance]

        # Pętla 2: złóż odpowiedź z kategorii zwycięskiej, usuwając duplikaty co do wartości
        # (ten sam punkt podany dwa razy w historii nie powinien liczyć się podwójnie).
        unique_winners: list[GeoPoint] = []
        for point in winners:
            if point not in unique_winners:
                unique_winners.append(point)

        if len(unique_winners) == 1:
            return unique_winners[0]
        return unique_winners


class GeoConnection(BaseModel):
    """
    Reprezentuje połączenie dwóch punktów geograficznych.
    """
    alpha_point: GeoPoint
    beta_point: GeoPoint

    def __repr__(self):
        return f"""
            object type: {type(self).__name__!r}
            string representation: {self.name!r}
            alpha point: {self.alpha_point!r}
            beta point: {self.beta_point!r}
            shortest distance: {self.shortest_distance!r}
            """
    
    def __name__(self):
        return self.name
    
    def __str__(self):
        return self.name
    
    @computed_field
    @property
    def name(self) -> str:
        if self.alpha_point.name:
            name_prefix: str = f"{self.alpha_point.name}"
        else:
            name_prefix: str = f"<alpha [lat:{self.alpha_point.latitude}, lon:{self.alpha_point.longitude}]>"
        if self.beta_point.name:
            name_suffix: str = f"{self.beta_point.name}"
        else:
            name_suffix: str = f"<beta [lat:{self.beta_point.latitude}, lon:{self.beta_point.longitude}]>"
        if self.shortest_distance:
            name: str = f"{name_prefix!r}|<--{self.shortest_distance!r}[km]-->|{name_suffix!r}"
            return name
        return f"{name_prefix!r}<--a-->{name_suffix!r}"

    @computed_field
    @property
    def shortest_distance(self) -> float:
        return self.alpha_point.distance_to(self.beta_point)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GeoConnection):
            return False
        standard_eq: bool = self.alpha_point == other.alpha_point and self.beta_point == other.beta_point
        reverse_eq: bool = self.alpha_point == other.beta_point and self.beta_point == other.alpha_point
        return standard_eq or reverse_eq

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, GeoConnection):
            return False
        return self.shortest_distance < other.shortest_distance

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, GeoConnection):
            return False
        return self.shortest_distance > other.shortest_distance

    def __reversed__(self) -> GeoConnection:
        return GeoConnection(alpha_point=self.beta_point, beta_point=self.alpha_point)


def connecion_bruteforce(point: list[GeoPoint], *collection: list[GeoPoint]) -> list[GeoConnection]:
    """
    Zwraca wszystkie pary punktów Geograficznych, unikalne punkty z zadanej puli punktów geograficznych.
    """
    flattened: list[GeoPoint] = []
    for group in collection:
        flattened.extend(group)

    all_connections: list[GeoConnection] = []
    for p1 in point:
        for p2 in flattened:
            alfa_beta_conect:GeoConnection = GeoConnection(alpha_point=p1, beta_point=p2)
            if alfa_beta_conect not in all_connections:
                all_connections.append(alfa_beta_conect)
    return all_connections

def shortest_conection(connections: list[GeoConnection]) -> GeoConnection:
    """
    Zwraca połączenie z najmniejszą odległością.
    """
    return min(connections, key=lambda c: c.shortest_distance)

class NamedPlace(GeoPoint):
    """Kształt odpowiedzi LLM dla pojedynczego zapytania o współrzędne miasta."""
    city_name: str

class PowerPlant(BaseModel):
    location_name: Annotated[str | None, Field(default=None)]
    location: Annotated[GeoPoint | None, Field(default=None)]
    code: Annotated[str | None, Field(default=None)]
    power_level: Annotated[int | None, Field(default=None)]
    active: Annotated[bool | None, Field(default=None)]

    def nearest_suspect(self, suspect: Suspect) -> dict | None:
        """
        Oblicza po kolei odległości pomiędzy daną elektrownią,
        a wszystkimi GeoPoints z LocationHistory podejrzanego.
        Zwraca tylko elektrownię, ktra uzyskała najniższą
        odległość od podejrzanego i zwraca słownik z uuid elektrowni, imieniem, nazwiskiem podejrzanego i odległością
        """
        if self.location is None or not suspect.location_history:
            return None

        nearest = self.location.is_nearest_to(suspect.location_history)
        if nearest is None:
            return None
        # Remis (kilka lokalizacji w tej samej, najmniejszej odległości) -> bierzemy pierwszą,
        # dystans i tak jest ten sam dla wszystkich w remisie.
        nearest_point = nearest[0] if isinstance(nearest, list) else nearest

        return {
            "code": self.code,
            "name": suspect.name,
            "surname": suspect.surname,
            "distance": self.location.distance_to(nearest_point),
        }

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


def parse_power_plants(raw: dict) -> list[PowerPlant]:
    """
    Parsuje surowy JSON z `findhim_locations.json` (klucz "power_plants": {nazwa: {...}})
    na listę `PowerPlant`. `location` zostaje `None` — geokodowanie robi `resolve_coordinates()`
    osobno, ta funkcja tylko przenosi dane strukturalne (nazwa/kod/moc/status).
    """
    plants: list[PowerPlant] = []
    for city_name, details in raw.get("power_plants", {}).items():
        power_raw = str(details.get("power", "0")).split()[0]
        plants.append(
            PowerPlant(
                location_name=city_name,
                location=None,
                code=details.get("code"),
                power_level=int(power_raw),
                active=bool(details.get("is_active", False)),
            )
        )
    return plants


def get_person_locations(hub: HubClient, name: str, surname: str) -> list[GeoPoint]:
    """POST /api/location — lista miejsc, w których widziano daną osobę."""
    raw = hub.post_api("/api/location", {"name": name, "surname": surname})
    return [GeoPoint(**point) for point in raw]


def get_access_level(hub: HubClient, name: str, surname: str, birth_year: int) -> int:
    """POST /api/accesslevel — wymaga birthYear jako int (rzutuj przed wywołaniem, jeśli źródło ma pełną datę)."""
    raw = hub.post_api(
        "/api/accesslevel",
        {"name": name, "surname": surname, "birthYear": birth_year},
    )
    return raw["accessLevel"]


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


# ─── Agent + Function Calling — narzędzia dla LLMClient.run_agent_loop ───────

def resolve_all_power_plants(plants: list[PowerPlant]) -> list[PowerPlant]:
    """
    Geokoduje wszystkie elektrownie NA STARCIE (jednorazowo), zanim agent zacznie
    działać — żeby model nie musiał podawać współrzędnych elektrowni przy każdym
    wywołaniu narzędzia, i żeby to nie liczyło się do jego max_iterations.
    """
    for plant in plants:
        if plant.location is None:
            plant.resolve_coordinates()
    return plants


def find_nearest_plant_for_suspect(
    hub: HubClient, plants: list[PowerPlant], name: str, surname: str, birth_year: int
) -> dict:
    """
    Dla jednej osoby: pobiera jej historię lokalizacji i zwraca kod najbliższej
    elektrowni + dystans w km. Jedno wywołanie HTTP (`/api/location`) + redukcja
    w kodzie po wszystkich elektrowniach — agent nie woła osobnego narzędzia per
    elektrownia.
    """
    locations = get_person_locations(hub, name, surname)
    suspect = Suspect(name=name, surname=surname, born=birth_year, location_history=locations)

    results = [
        plant.nearest_suspect(suspect)
        for plant in plants
        if plant.location is not None
    ]
    results = [r for r in results if r is not None]

    if not results:
        return {"plant_code": None, "distance_km": None}

    best = min(results, key=lambda r: r["distance"])
    return {"plant_code": best["code"], "distance_km": round(best["distance"], 2)}


FIND_NEAREST_PLANT_TOOL = Tool(
    name="find_nearest_plant_for_suspect",
    description=(
        "Dla podanej osoby (imię, nazwisko, rok urodzenia) sprawdza jej historię "
        "lokalizacji i zwraca kod najbliższej elektrowni oraz dystans w km. Użyj "
        "dla KAŻDEJ osoby z listy podejrzanych, żeby znaleźć tę najbliżej elektrowni."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Imię podejrzanego"},
            "surname": {"type": "string", "description": "Nazwisko podejrzanego"},
            "birth_year": {"type": "integer", "description": "Rok urodzenia podejrzanego"},
        },
        "required": ["name", "surname", "birth_year"],
    },
)

GET_ACCESS_LEVEL_TOOL = Tool(
    name="get_access_level",
    description=(
        "Zwraca poziom dostępu (accessLevel) danej osoby. Użyj TYLKO dla osoby, "
        "która okazała się najbliżej elektrowni ze wszystkich sprawdzonych."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Imię podejrzanego"},
            "surname": {"type": "string", "description": "Nazwisko podejrzanego"},
            "birth_year": {"type": "integer", "description": "Rok urodzenia podejrzanego"},
        },
        "required": ["name", "surname", "birth_year"],
    },
)

FINDHIM_TOOLS = [FIND_NEAREST_PLANT_TOOL, GET_ACCESS_LEVEL_TOOL]


def build_tool_executor(hub: HubClient, plants: list[PowerPlant]):
    """
    Domyka `hub`/`plants` w funkcji dispatchującej wywołania narzędzi —
    dokładnie te dwa argumenty NIGDY nie są polami, które model wypełnia.
    """
    def tool_executor(name: str, args: dict) -> str:
        if name == "find_nearest_plant_for_suspect":
            result = find_nearest_plant_for_suspect(
                hub, plants, args["name"], args["surname"], args["birth_year"]
            )
            return json.dumps(result, ensure_ascii=False)
        if name == "get_access_level":
            level = get_access_level(hub, args["name"], args["surname"], args["birth_year"])
            return json.dumps({"accessLevel": level}, ensure_ascii=False)
        raise ValueError(f"Unknown tool: {name}")

    return tool_executor


def build_initial_messages(suspects: list[Suspect]) -> list[LLMMessage]:
    suspects_json = json.dumps(
        [
            {"name": s.name, "surname": s.surname, "birth_year": s.born}
            for s in suspects
        ],
        ensure_ascii=False,
    )
    return [LLMMessage.user(USER_AGENT_FINDHIM.format(suspects_json=suspects_json))]
