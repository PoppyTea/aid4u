import uuid
import code
from pydantic import Field, BaseModel
from typing import Annotated
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
KIJOW = GeoPoint(latitude=50.27, longitude=30.31)
NEAR_GRUDZIADZ = GeoPoint(latitude=51.15, longitude=30.14)
GRUDZIADZ = GeoPoint(latitude=51.16127, longitude=30.13095)
LOCATION_A = GeoPoint(latitude=11.0, longitude=22.0)
TARGET_PLANT= PowerPlant(location_name="Grudziądz", location=NEAR_GRUDZIADZ, uuid="PWR2764PL", power_level=9001, active=True )
RANDOM_PLANT=PowerPlant(location_name="za lasami", location=LOCATION_A, uuid="abs123pl", power_level=12)
EVIL_DUDE = Suspect(name="Maurycy", born=1990, surname="Dreptak", locations_history=[WARSAW, KRAKOW], access_lvl=2, age=None)

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

def test_calc_age():
    """Poprawność obliczania wieku na podstawie roku urodzenia"""
    test_dude = EVIL_DUDE.model_copy()
    test_dude.calc_age()
    assert EVIL_DUDE.age == 26

def test_get_coordinats_to_city():


def test_inspect_location_history():
    near_suspect = GeoPoint(longitude=None,latitude=None)
    assert TARGET_PLANT.nearest_suspect()


def test_nearest_powerplant():
    """
    Czy podawana elektrownia jest najbliższa
    """

def test_answer_completion():
    payload=Answer(
        name=EVIL_DUDE.name,
        surname=EVIL_DUDE.surname,
        access_lvl=
    )
