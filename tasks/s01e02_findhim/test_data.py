# Faktyczne dane z zadania
from tasks.s01e02_findhim.solution import GeoPoint, PowerPlant, Suspect

ZABRZE = GeoPoint(
    name="Zabrze",
    latitude=50.3249,
    longitude=18.7858
)
PIOTRKOW_TRYBUNALSKI = GeoPoint(
    name="Piotrków Trybunalski",
    latitude=51.4055,
    longitude=19.7032
)
GRUDZIADZ = GeoPoint(
    name="Grudziądz",
    latitude=53.4841,
    longitude=18.7537
)
TCZEW = GeoPoint(
    name="Tczew",
    latitude=54.0924,
    longitude=18.7779
)
RADOM = GeoPoint(
    name="Radom",
    latitude=51.4025,
    longitude=21.1471
)
CHELMNO = GeoPoint(
    name="Chełmno",
    latitude=53.3486,
    longitude=18.4251
)
ZARNOWIEC = GeoPoint(
    name="Zarnowiec",
    latitude=50.4844,
    longitude=19.8631
)


# Testing data-set

WARSAW = GeoPoint(
    name="Warszawa",
    latitude=52.2297,
    longitude=21.0122
)
KRAKOW = GeoPoint(
    name="Kraków",
    latitude=50.0647,
    longitude=19.9450
)
GDANSK = GeoPoint(
    name="Gdańsk",
    latitude=54.3523,
    longitude=18.6491
)
SZCZECIN = GeoPoint(
    name="Szczecin",
    latitude=53.4289,
    longitude=14.5530
)
OPOLE = GeoPoint(
    name="Opoł",
    latitude=50.6721,
    longitude=17.9253
)
ZAKOPANE = GeoPoint(
    name="Zakopane",
    latitude=49.2990,
    longitude=19.9489
)

EVIL_DUDE = Suspect(
    name="Maurycy",
    born=1990,
    surname="Dreptak",
    access_lvl=2,
    location_history=[
        KRAKOW,
        WARSAW,
        GDANSK,
        SZCZECIN,
        OPOLE,
        ZAKOPANE,
    ])
# Elektrownie
# 1
POWER_PLANT_ZABRZE = PowerPlant(
    name="Elektrownia Zabrze",
    location_name=str(ZABRZE.name),
    location=ZABRZE,
    power_level=35,
    code="PWR3847PL",
    active=True
)
# 2
POWER_PLANT_PIOTRKOW_TRYBUNALSKI = PowerPlant(
    name="Elektrownia Piotrków Trybunalski",
    location_name=str(PIOTRKOW_TRYBUNALSKI.name),
    location=PIOTRKOW_TRYBUNALSKI,
    power_level=28,
    code="PWR5921PL",
    active=True
)
# 3
POWER_PLANT_GRUDZIADZ = PowerPlant(
    name="Elektrownia Grudziądz",
    location_name=str(GRUDZIADZ.name),
    location=GRUDZIADZ,
    power_level=1138,
    code="PWR7264PL",
    active=True
)
# 4
POWER_PLANT_TCZEW = PowerPlant(
    name="Elektrownia Tczew",
    location_name=str(TCZEW.name),
    location=TCZEW,
    power_level=31,
    code="PWR1593PL",
    active=True
)
# 5
POWER_PLANT_RADOM = PowerPlant(
    name="Elektrownia Radom",
    location_name=str(RADOM.name),
    location=RADOM,
    power_level=38,
    code="PWR8406PL",
    active=True
)
# 6
POWER_PLANT_CHELMNO = PowerPlant(
    name="Elektrownia Chelmno",
    location_name=str(CHELMNO.name),
    location=CHELMNO,
    power_level=128,
    code="PWR2758PL",
    active=True
)
# 7
POWER_PLANT_ZARNOWIEC = PowerPlant(
    name="Elektrownia Zarnowiec",
    location_name=str(ZARNOWIEC.name),
    location=ZARNOWIEC,
    power_level=0,
    code="PWR6132PL",
    active=False
)


PP_LIST=[POWER_PLANT_ZABRZE, POWER_PLANT_PIOTRKOW_TRYBUNALSKI, POWER_PLANT_GRUDZIADZ, POWER_PLANT_TCZEW, POWER_PLANT_RADOM, POWER_PLANT_CHELMNO, POWER_PLANT_ZARNOWIEC]

PP_LOCATIONS_LIST=[ZABRZE, PIOTRKOW_TRYBUNALSKI, GRUDZIADZ, TCZEW, RADOM, CHELMNO, ZARNOWIEC]
