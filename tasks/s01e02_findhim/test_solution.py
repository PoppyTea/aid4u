from typing import Iterable
from pathlib import Path

import pytest
from solution import (
    GeoConnection,
    GeoPoint,
    PowerPlant,
    Suspect,
    connecion_bruteforce,
    get_access_level,
    get_person_locations,
    parse_power_plants,
    shortest_conection,
)
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

# Perfect city doubler creation
double_of_radom = RADOM.model_copy()

# Fake copy creation
fake_radom = double_of_radom.model_copy()
fake_radom.longitude = KRAKOW.longitude

# city_in_equal_dist_to_radom
point_x = GeoPoint(
    name="Odbicie_Radomia_na_Zachod",
    latitude=51.4025,
    longitude=20.8773
)

@pytest.mark.parametrize("single_point, many_points, solution, run", [
    #1. point|<-0->|same_point => same_point
    pytest.param(WARSAW, WARSAW, WARSAW, 1, id="same_2_same"),
    #2. point|<-?->|[many points] => the_closest_point
    pytest.param(WARSAW, [KRAKOW, SZCZECIN, RADOM], RADOM, 2, id="one_2_one_from_many"),
    #3. point|<-?->|many_closest_points, other_points => [closest_points]
    pytest.param(WARSAW, [double_of_radom, SZCZECIN, KRAKOW, RADOM, fake_radom, point_x], [RADOM, point_x], 3, id="many_diff_nearest"),
    #4. prawdopodobne dane z atrybutów odpowiednich klas
    pytest.param(power_plants[4].location, test_dude.location_history, WARSAW, 4, id="simulation_2_one_of_many"),
    # 5 Dedup candidates
    pytest.param(WARSAW, [RADOM, SZCZECIN, KRAKOW, RADOM, KRAKOW], RADOM, 5, id="many_nearest_with_doubles")
])
def test_is_nearest_to__parametrize (single_point, many_points, solution, run):
    expected = single_point.is_nearest_to(many_points)

    if run == 1:
        no_distance = single_point.distance_to(expected) == 0.0
        assert no_distance
    if isinstance(expected, list):
        expected_count: int = len(expected)
        many_points_count: int = len(many_points)
        predicted_count: int = len(solution)
        check_count: bool = expected_count < many_points_count
        assert check_count
        count_checked: int = predicted_count == expected_count
        assert count_checked

        for i in range(len(expected)):
            for j in range(len(solution)):
                # Czy wszystkie punkty są równo oddalone od single_point (leżą na okręgu O(single_point) i R=distance_between)?
                same_distance = single_point.distance_to(expected[i]) == single_point.distance_to(expected[j])
                assert same_distance
                distance_as_expected = single_point.distance_to(expected[i]) == single_point.distance_to(solution[j])
                assert distance_as_expected
                # Czy wszystkie imiona w wyniku są inne i nie ma duplikatów?
                same_name_count: int = 0
                if expected[i].name == solution[j].name:
                    same_name_count += 1
                diff_but_no_dup: bool = same_name_count <= 1
                assert diff_but_no_dup
                inside_starting_group: bool = expected[i] in many_points
                assert inside_starting_group
    else:
        expected_distance = single_point.distance_to(expected)
        predicted_distance = single_point.distance_to(solution)
        good_predction: bool = (( expected.latitude == solution.latitude) and (expected.longitude == solution.longitude))
        assert good_predction
        distance_as_expected = expected_distance == predicted_distance
        assert distance_as_expected
        zero_distance = expected_distance == 0.0
        if run == 1:
            assert zero_distance
        else:
            assert not zero_distance



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


### TDD CYCLE 03 — GeoConnection, connecion_bruteforce, shortest_conection ###

def test_geo_connection_shortest_distance():
    connection = GeoConnection(alpha_point=WARSAW, beta_point=KRAKOW)
    assert 248.5 <= connection.shortest_distance <= 253.5


def test_geo_connection_equality_is_order_independent():
    forward = GeoConnection(alpha_point=WARSAW, beta_point=KRAKOW)
    backward = GeoConnection(alpha_point=KRAKOW, beta_point=WARSAW)
    assert forward == backward


def test_geo_connection_reversed_swaps_points():
    connection = GeoConnection(alpha_point=WARSAW, beta_point=KRAKOW)
    flipped = reversed(connection)
    assert flipped.alpha_point == KRAKOW
    assert flipped.beta_point == WARSAW


def test_geo_connection_ordering_by_distance():
    close = GeoConnection(alpha_point=WARSAW, beta_point=RADOM)
    far = GeoConnection(alpha_point=WARSAW, beta_point=SZCZECIN)
    assert close < far
    assert far > close


def test_connecion_bruteforce_pairs_every_point_with_every_collection_point():
    connections = connecion_bruteforce([WARSAW], [KRAKOW, RADOM])
    assert len(connections) == 2
    assert GeoConnection(alpha_point=WARSAW, beta_point=KRAKOW) in connections
    assert GeoConnection(alpha_point=WARSAW, beta_point=RADOM) in connections


def test_connecion_bruteforce_flattens_multiple_collections():
    connections = connecion_bruteforce([WARSAW], [KRAKOW], [RADOM, SZCZECIN])
    assert len(connections) == 3


def test_connecion_bruteforce_dedupes_equal_connections():
    connections = connecion_bruteforce([WARSAW, WARSAW], [KRAKOW])
    assert len(connections) == 1


def test_shortest_conection_picks_the_minimum():
    connections = connecion_bruteforce([WARSAW], [KRAKOW, RADOM, SZCZECIN])
    winner = shortest_conection(connections)
    assert winner == GeoConnection(alpha_point=WARSAW, beta_point=RADOM)


### TDD CYCLE 04 — PowerPlant.nearest_suspect, parse_power_plants ###

def test_nearest_suspect_returns_distance_and_identity():
    plant = PowerPlant(location_name="Radom", location=RADOM, code="PWR8406PL", power_level=38, active=True)
    result = plant.nearest_suspect(test_dude)
    assert result is not None
    assert result["code"] == "PWR8406PL"
    assert result["name"] == test_dude.name
    assert result["surname"] == test_dude.surname
    assert result["distance"] == pytest.approx(RADOM.distance_to(WARSAW))


def test_nearest_suspect_returns_none_when_location_unresolved():
    plant = PowerPlant(location_name="Radom", location=None, code="PWR8406PL", power_level=38, active=True)
    assert plant.nearest_suspect(test_dude) is None


def test_parse_power_plants_builds_models_from_raw_json():
    raw = {
        "power_plants": {
            "Zabrze": {"is_active": True, "power": "35 MW", "code": "PWR3847PL"},
            "Żarnowiec": {"is_active": False, "power": "0 MW", "code": "PWR6132PL"},
        }
    }
    plants = parse_power_plants(raw)
    assert len(plants) == 2

    zabrze = next(p for p in plants if p.location_name == "Zabrze")
    assert zabrze.code == "PWR3847PL"
    assert zabrze.power_level == 35
    assert zabrze.active is True
    assert zabrze.location is None  # geokodowanie robi resolve_coordinates() osobno

    zarnowiec = next(p for p in plants if p.location_name == "Żarnowiec")
    assert zarnowiec.active is False


### TDD CYCLE 05 — adaptery HTTP (granica sieci zamockowana, jak w s01e01) ###

class FakeHub:
    """Zamiast prawdziwego HubClient — przechwytuje wywołania post_api bez sieci."""

    def __init__(self, response):
        self.response = response
        self.calls: list[tuple[str, dict]] = []

    def post_api(self, path: str, payload: dict):
        self.calls.append((path, payload))
        return self.response


def test_get_person_locations_sends_name_and_surname():
    hub = FakeHub(response=[{"latitude": 52.2297, "longitude": 21.0122}])
    get_person_locations(hub, "Wacław", "Jasiński")

    path, payload = hub.calls[0]
    assert path == "/api/location"
    assert payload == {"name": "Wacław", "surname": "Jasiński"}


def test_get_person_locations_parses_response_into_geopoints():
    hub = FakeHub(response=[
        {"latitude": 52.2297, "longitude": 21.0122},
        {"latitude": 50.0647, "longitude": 19.9450},
    ])
    result = get_person_locations(hub, "Wacław", "Jasiński")

    assert result == [WARSAW, KRAKOW]


def test_get_access_level_sends_birth_year_as_int():
    hub = FakeHub(response={"name": "Wacław", "surname": "Jasiński", "accessLevel": 2})
    get_access_level(hub, "Wacław", "Jasiński", 1986)

    path, payload = hub.calls[0]
    assert path == "/api/accesslevel"
    assert payload == {"name": "Wacław", "surname": "Jasiński", "birthYear": 1986}


def test_get_access_level_returns_just_the_level():
    hub = FakeHub(response={"name": "Wacław", "surname": "Jasiński", "accessLevel": 2})
    assert get_access_level(hub, "Wacław", "Jasiński", 1986) == 2
