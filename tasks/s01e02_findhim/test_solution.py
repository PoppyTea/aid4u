from pathlib import Path

import pytest
from solution import GeoPoint, PowerPlant, Suspect
from test_data import WARSAW

from tasks.s01e02_findhim.test_data import (
    EVIL_DUDE,
    KRAKOW,
    PP_LIST,
    PP_LOCATIONS_LIST,
    RADOM,
    SZCZECIN,
)

# Współrzędne:
#   latitude > 0 =>  North (N)
#   latitude = 0 => Equator (EQ)
#   latitude < 0 => South (S)
#
#   longitude > 0 => East (E)
#   longitude = 0 => Prime Meridian (PM)
#   longitude < 0 => West (W)


# Ścieżki
BASE_PATH: Path = Path(__file__).parent
DATA_PATH: Path = BASE_PATH / "data"
# Suspects
test_dude = EVIL_DUDE.model_copy()
power_plants = PP_LIST.copy()
power_plants_locations = PP_LOCATIONS_LIST.copy()
### TDD CYCLE 01 ###


def test_GeoPoint_calc_distance_to()->float | None:
    """
    Testujemy metodę obliczającą odległość pomiędzy punktem A i B metodą haversine:
    Łuk mierzony po powierzchni Ziemi od pkt A do pkt B
    Wzór:
    Standard case: Warszawa <-|251 km |-> Kraków
    Maksymalny margines błędu ±1% (±2.5km)
    """
    distance:float = WARSAW.distance_to(KRAKOW)
    assert 248.5 <= distance <= 253.5

def test_GeoPoint_calc_distance_from_A_to_A():
    """ Test the haversine distance calculation. Edge case: same location """
    distance: float | None = WARSAW.distance_to(WARSAW)
    assert distance == 0

### TDD CYCLE 02 ###

def test_suspect_age_field():
    """Poprawność obliczania wieku na podstawie roku urodzenia"""
    assert EVIL_DUDE.age == 36

def test_resolve_coordinates(monkeypatch):
    """
    PowerPlant.resolve_coordinates() zamienia PowerPlant.location_name (str)
    na PowerPlant.location (GeoPoint). Rzeczywiste zdobywanie współrzędnych
    (web_search / wiedza modelu) idzie przez seam `_geocode_city`, żeby test
    jednostkowy nie robił realnego wywołania sieciowego/LLM.
    """
    plant = PowerPlant(location_name="Grudziądz", location=None, uuid="PWR7264PL", power_level=1138, active=True)

    def fake_geocode_city(self, city_name: str) -> GeoPoint:
        assert city_name == "Grudziądz"
        return GeoPoint(latitude=53.4837, longitude=18.7536)

    monkeypatch.setattr(PowerPlant, "_geocode_city", fake_geocode_city, raising=False)

    plant.resolve_coordinates()

    assert isinstance(plant.location, GeoPoint)
    assert plant.location.latitude == pytest.approx(53.4837)
    assert plant.location.longitude == pytest.approx(18.7536)


@pytest.mark.skip(reason="następny po is_nearest_to()")
def test_inspect_location_history():
    """
    `inspect_location_history(Suspect)`
    1. Sprawdza czy historia lokalizacji jest None
    1.1 Jeśli nie -> przerwij
    2. Sprawdza czy istnieje plik pod ścieżką `Path(DATA_PATH / {Suspect.name}_{Suspect.surname}_history)`
    2.1 Jeśli nie -> spróbuj pobrać z endpointu centrali `/data`
    3. Jeśli `(2.) == true` sparsuj ten plik i osadź w `Suspect.location_history`
    """
    ...

@pytest.mark.parametrize("single_point, many_points, solution", [
    pytest.param(WARSAW, WARSAW, WARSAW, id="point|<-0->|same_point => same_point"),
    pytest.param(WARSAW, [KRAKOW, SZCZECIN, RADOM], RADOM, id="point|<-?->|[many points] => the_closest_point"),
    pytest.param(WARSAW, [RADOM, SZCZECIN, KRAKOW, RADOM], RADOM, id="point|<-?->|many_closest_points, other_points => [closest_points]"),
    pytest.param(power_plants[5], test_dude.location_history, WARSAW, id="prawdopodobne dane z atrybutów odpowiednich klas"),
])
def test_is_nearest_to__parametrize (single_point, many_points, solution, expected):
    expected = single_point.dist_is_nearest_to(many_points)
    assert expected == solution



@pytest.mark.skip(reason="TDD cycle 2 - test jeszcze niezaprojektowany: brak modelu Answer (payload do /verify)")
def test_answer_completion():
    ...

def test_suspect_location_history_coords_list():
    test_dude: Suspect = Suspect(
        name="John",
        surname="Kowalski",
        born=1992,
        location_history=[KRAKOW, WARSAW])
    assert test_dude.location_history[1].latitude == WARSAW.latitude
    assert test_dude.location_history[1].longitude == WARSAW.longitude
    assert len(test_dude.location_history) == 2

def test_suspect_location_history_path():
    test_dude: Suspect = Suspect(
        name="John",
        surname="Nowak",
        born=1972,
        location_history=Path(DATA_PATH / "test_suspect_locations.json"))
    assert len(test_dude.location_history) == 2
    assert test_dude.location_history[1].latitude == WARSAW.latitude
    assert test_dude.location_history[1].longitude == WARSAW.longitude
