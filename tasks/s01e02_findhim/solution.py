from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any

import httpx
from pydantic import BaseModel, Field, computed_field, field_validator

from core.hub import HubClient
from core.llm import LLMMessage
from core.llm.types import Tool
from core.tasks import BaseTask, task
from tasks.common.const import REFERENCE_YEAR
from tasks.s01e02_findhim.prompts import SYSTEM_AGENT_FINDHIM, USER_AGENT_FINDHIM

_NOMINATIM_USER_AGENT = "aid4u-findhim-course-project/1.0"


class GeoPoint(BaseModel):
    name: Annotated[None | str, Field(default=None, description="")] = None
    latitude: Annotated[
        float | None,
        Field(
            ge=-90,
            le=90,
            default=None,
            description="Decimal degrees, up to 6 decimal places. Null if unknown.",
        ),
    ]
    longitude: Annotated[
        float | None,
        Field(
            ge=-180,
            le=180,
            default=None,
            description="Decimal degrees, up to 6 decimal places. Null if unknown.",
        ),
    ]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GeoPoint):
            return False
        return self.latitude == other.latitude and self.longitude == other.longitude

    def __add__(self: GeoPoint, other: GeoPoint) -> GeoConnection:
        return GeoConnection(alpha_point=self, beta_point=other)

    def distance_to(self, target:GeoPoint) -> float:
        if self == target:
            distance: float = 0.0
        elif self.latitude and self.longitude and target.latitude and target.longitude is not None:
            # Promień Ziemi w kilometrach
            R: float = 6356.4445

            lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
            lat2, lon2 = math.radians(target.latitude), math.radians(target.longitude)

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
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

    def __reversed__(self) -> Iterator[GeoPoint]:
        yield self.beta_point
        yield self.alpha_point

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GeoConnection):
            return False
        standard_eq: bool = (
            self.alpha_point == other.alpha_point and self.beta_point == other.beta_point
        )
        reverse_eq: bool = (
            self.alpha_point == other.beta_point and self.beta_point == other.alpha_point
        )
        return standard_eq or reverse_eq

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, GeoConnection):
            return False
        return self.shortest_distance < other.shortest_distance

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, GeoConnection):
            return False
        return self.shortest_distance > other.shortest_distance

    @property
    def points_dict(self) -> dict[str, GeoPoint]:
        """Zwraca punkty jako słownik, umożliwiając wygodną iterację."""
        return {
            "alpha_point": self.alpha_point,
            "beta_point": self.beta_point,
        }

    @computed_field
    @property
    def name(self) -> str:
        if self.alpha_point.name:
            name_prefix: str = f"{self.alpha_point.name}"
        else:
            name_prefix: str = (
                f"<alpha [lat:{self.alpha_point.latitude}, lon:{self.alpha_point.longitude}]>"
            )
        if self.beta_point.name:
            name_suffix: str = f"{self.beta_point.name}"
        else:
            name_suffix: str = (
                f"<beta [lat:{self.beta_point.latitude}, lon:{self.beta_point.longitude}]>"
            )
        if self.shortest_distance:
            name: str = f"{name_prefix!r}|<--{self.shortest_distance!r}[km]-->|{name_suffix!r}"
            return name
        return f"{name_prefix!r}<--a-->{name_suffix!r}"

    @computed_field
    @property
    def shortest_distance(self) -> float:
        return self.alpha_point.distance_to(self.beta_point)


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
            alfa_beta_conect: GeoConnection = GeoConnection(alpha_point=p1, beta_point=p2)
            if alfa_beta_conect not in all_connections:
                all_connections.append(alfa_beta_conect)
    return all_connections


def shortest_conection(connections: list[GeoConnection]) -> GeoConnection:
    """
    Zwraca połączenie z najmniejszą odległością.
    """
    return min(connections, key=lambda c: c.shortest_distance)


class PowerPlant(BaseModel):
    location_name: Annotated[str | None, Field(default=None)]
    location: Annotated[GeoPoint | None, Field(default=None)]
    code: Annotated[str | None, Field(default=None)]
    power_level: Annotated[int | str | None, Field(default=None)]
    active: Annotated[bool | None, Field(default=None)]

    @field_validator("power_level", mode="before")
    @classmethod
    def parse_power(cls, value: int | str | None) -> int | None:
        if value is None or isinstance(value, int):
            return value
        # split() automatycznie dzieli po białych znakach.
        # "35 MW" -> ["35", "MW"] -> bierze "35" i robi z tego int.
        # Działa niezależnie od długości jednostki (MW, kW, W).
        return int(str(value).split()[0])

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

    def _geocode_city(self, city_name: str | None) -> GeoPoint | None:
        """
        Geokoduje przez Nominatim (OpenStreetMap) — realne API geograficzne,
        nie zgadywanie przez LLM. Próbuje najpierw "Elektrownia Jądrowa {miasto}"
        (żeby trafić w faktyczną elektrownię, jeśli istnieje — np. Żarnowiec,
        jedyna realna elektrownia jądrowa w Polsce, myli się z inną miejscowością
        o tej samej nazwie), potem fallback na samą nazwę miasta.
        """
        if city_name is None:
            return None

        for query in (f"Elektrownia Jądrowa {city_name}, Poland", f"{city_name}, Poland"):
            response = httpx.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1},
                headers={"User-Agent": _NOMINATIM_USER_AGENT},
                timeout=10.0,
            )
            response.raise_for_status()
            results = response.json()
            if results:
                return GeoPoint(
                    name=city_name,
                    latitude=float(results[0]["lat"]),
                    longitude=float(results[0]["lon"]),
                )
        return None

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
    name: Annotated[str, Field(frozen=True)]
    surname: Annotated[str, Field(frozen=True)]
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
            base_dir = (Path(__file__).parent / "data").resolve()
            resolved_path = path.resolve()
            if not resolved_path.is_relative_to(base_dir):
                raise ValueError(f"Path traversal detected: {path} is not in {base_dir}")
            # Pusty plik traktujemy jako brak historii
            if os.path.getsize(resolved_path) == 0:
                raise ValueError("Plik wskazany jako historia lokacji nie istnieje lub jest pusty.")
            with open(resolved_path, mode="r", encoding="utf-8") as f:
                raw_json = json.load(f)
                return [GeoPoint(**data_point) for data_point in raw_json]
        if isinstance(v, list):
            bad_data_type_elements: list = []
            for element in v:
                if isinstance(element, GeoPoint):
                    continue
                else:
                    bad_data_type_elements.append(element)
            if len(bad_data_type_elements) == 0:
                return v
            raise ValueError(f"Lista wewnątrz pliku wskazanego jako historia lokacji zawiera błędne typy danych.\nIlość błędów: {len(bad_data_type_elements)},\nBłędne wartości: {bad_data_type_elements}\noczekiwany typ danych wewnątrz listy: GeoPoint")
        raise ValueError(f"Pojęcia nie mam co Ty tu rzuciłeś jako listę historii lokacji.\n Sam zobacz:\n{v.__repr__()} ")

# ─── Agent + Function Calling — narzędzia dla LLMClient.run_agent_loop ───────


def resolve_all_power_plants(
    plants: list[PowerPlant], *, delay_seconds: float = 1.1
) -> list[PowerPlant]:
    """
    Geokoduje wszystkie elektrownie NA STARCIE (jednorazowo), zanim agent zacznie
    działać — żeby model nie musiał podawać współrzędnych elektrowni przy każdym
    wywołaniu narzędzia, i żeby to nie liczyło się do jego max_iterations.

    `delay_seconds` — throttling między wywołaniami Nominatim (polityka usage:
    max 1 zapytanie/sekundę).
    """
    to_resolve = [p for p in plants if p.location is None]
    for i, plant in enumerate(to_resolve):
        if i > 0:
            time.sleep(delay_seconds)
        plant.resolve_coordinates()
    return plants


def search_suspect_history_for_nearest_power_plant(
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

    results = [plant.nearest_suspect(suspect) for plant in plants if plant.location is not None]
    results = [r for r in results if r is not None]

    if not results:
        return {"plant_code": None, "distance_km": None}

    best = min(results, key=lambda r: r["distance"])
    return {"plant_code": best["code"], "distance_km": round(best["distance"], 2)}


FIND_NEAREST_PLANT_TOOL = Tool(
    name="search_suspect_history_for_nearest_power_plant",
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
        if name == "search_suspect_history_for_nearest_power_plant":
            result = search_suspect_history_for_nearest_power_plant(
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
        [{"name": s.name, "surname": s.surname, "birth_year": s.born} for s in suspects],
        ensure_ascii=False,
    )
    return [LLMMessage.user(USER_AGENT_FINDHIM.format(suspects_json=suspects_json))]


def _extract_json(text: str) -> dict:
    """Model ma zwrócić czysty JSON, ale jeśli owinie w markdown ```, zdejmij to."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    return json.loads(cleaned)


# ─── Task ─────────────────────────────────────────────────────────────────────


@task("s01e02", hub_name="findhim")
class FindhimTask(BaseTask):
    def fetch_data(self) -> bytes:
        return self.cache.get_or_fetch(
            "findhim_locations.json",
            lambda: self.hub.get_data("findhim_locations.json"),
        )

    def solve(self, data: bytes) -> Any:
        # 1. Elektrownie: parsuj + geokoduj raz na start (agent nie robi tego per suspect)
        plants = parse_power_plants(json.loads(data))
        resolve_all_power_plants(plants)

        # 2. Podejrzani: lista z S01E01 (tylko ci wysłani jako podejrzani, tag "transport")
        suspects = self._load_suspects()

        # 3. Agent + Function Calling — LLMClient.run_agent_loop, nie własna pętla
        executor = build_tool_executor(self.hub, plants)
        messages = build_initial_messages(suspects)
        final_text = self.llm.run_agent_loop(
            messages,
            FINDHIM_TOOLS,
            executor,
            system=SYSTEM_AGENT_FINDHIM["v3-EN"],
            max_iterations=12,
        )

        return _extract_json(final_text)

    def _load_suspects(self) -> list[Suspect]:
        suspects_path = Path(__file__).parent / "data" / "suspects.json"
        raw = json.loads(suspects_path.read_text(encoding="utf-8"))
        return [
            Suspect(name=s["name"], surname=s["surname"], born=s["birthYear"], location_history=[])
            for s in raw
        ]
