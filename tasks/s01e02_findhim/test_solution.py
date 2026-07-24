from pathlib import Path
import pytest
from solution import GeoPoint, Suspect, PowerPlant



# Współrzędne:
#   latitude > 0 =>  North (N)
#   latitude = 0 => Equator (EQ)
#   latitude < 0 => South (S)
#
#   longitude > 0 => East (E)
#   longitude = 0 => Prime Meridian (PM)
#   longitude < 0 => West (W)

# Testing data-set
WARSAW = GeoPoint(latitude=52.2297, longitude=21.0122)
KRAKOW = GeoPoint(latitude=50.0647, longitude=19.9450)
EVIL_DUDE = Suspect(
    name="Maurycy",
    born=1990,
    surname="Dreptak",
    access_lvl=2,
    location_history=[KRAKOW, WARSAW])
# Ścieżki
BASE_PATH: Path = Path(__file__).parent
DATA_PATH: Path = BASE_PATH / "data"

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


@pytest.mark.skip(reason="TDD cycle 2 - test jeszcze niezaprojektowany: nearest_suspect(suspect) wymaga realnej listy podejrzanych")
def test_inspect_location_history():
    ...


@pytest.mark.skip(reason="TDD cycle 2 - test jeszcze niezaprojektowany")
def test_nearest_powerplant():
    """
    Czy podawana elektrownia jest najbliższa
    """


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
