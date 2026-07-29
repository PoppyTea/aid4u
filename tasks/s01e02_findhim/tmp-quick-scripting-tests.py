from core.config import get_config
import json
from pathlib import Path

from solution import GeoPoint, PowerPlant


    def belka(nadruk:str = "TERMINAL ZAKŁADOWY - S01E02") -> str:
        szyld: str= f"""\
        |-------------<< {nadruk} >>-------------|
        """
        return szyld

    print(belka())


plik = Path(__file__).parent / "data" / "suspects.json"
with plik.open("r", encoding="utf-8") as f:
    data = json.load(f)



from core.hub import HubClient

# Inicjalizacja klienta Hub do pobrania lokalizacji
config = get_config()
hub = HubClient()

# Utworzenie folderu docelowego
output_dir = Path(__file__).parent / "data" / "lokalizacje"
PP_file = Path(__file__).parent / "data" / "power-plants-coordinates-precise.json"
with open(PP_file,'r',encoding="utf-8") as f:
    pp_data = json.load(f)

print(belka("JSON FILE ODCZYTANY LOG"))
print(f"dane w .json: \n\n{pp_data}")



pp_list: list[PowerPlant] = [
    PowerPlant(nazwa=key,
        is_active=attrib["is_active"],
        location=GeoPoint(nazwa=key, latitude=attrib["latitude"], longitude=attrib["longitude"]),
        power_level= None,
        code=attrib["code"])
        for key, attrib in pp_data["power_plants"].items()
]
print(belka(f"PARSED PP_list: {len(pp_list)}"))
print("\n\n", pp_list)


from typing import Any, Dict  # noqa: UP035

import requests

# 1. Mapowanie kluczy z JSON na identyfikatory z pliku image_783c94.png
API_IDENTIFIERS = {
    "Zabrze": "zabrze",
    "Piotrków Trybunalski": "piotrkowTrybunalski",
    "Grudziądz": "grudziadz",
    "Tczew": "tczew",
    "Radom": "radom",
    "Chelmno": "chelmno",
    "Żarnowiec": "zarnowiec"
}

def update_coordinates_from_api(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pobiera prawdziwe współrzędne z API i aktualizuje podany słownik.
    """
    power_plants = data.get("power_plants", {})

    for city_name, attrib in power_plants.items():
        api_id = API_IDENTIFIERS.get(city_name)

        if not api_id:
            print(f"Pomijam {city_name} - brak zdefiniowanego identyfikatora API.")
            continue

        # Zbudowanie docelowego URL
        url = f"http://www.gps-coordinates.net/api/{api_id}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status() # Rzuci błąd dla HTTP 4xx/5xx
            api_data = response.json()

            # Aktualizacja tylko, jeśli API potwierdzi znalezienie miejsca
            if api_data.get("responseCode") == "200":
                # API zwraca współrzędne jako stringi, float() zabezpiecza typ
                attrib["latitude"] = float(api_data.get("latitude"))
                attrib["longitude"] = float(api_data.get("longitude"))
                print(f"Zaktualizowano współrzędne dla {city_name}")
            else:
                print(f"Błąd z API dla {city_name}: responseCode {api_data.get('responseCode')}")

        except requests.RequestException as e:
            print(f"Błąd połączenia podczas pobierania danych dla {city_name}: {e}")

    return data

# --- Użycie ---
from pydantic import BaseModel, field_validator

    # Przenosimy logikę czyszczenia prosto do modelu (fabryki)

# 1. Aktualizujemy surowe dane
updated_pp_data = update_coordinates_from_api(pp_data)

# 2. Generujemy czyste i bezpieczne obiekty (przy użyciu Twojego wcześniejszego kodu)
pp_list: list[PowerPlant] = [
    PowerPlant(
        nazwa=key,
        is_active=attrib["is_active"],
        location=GeoPoint(nazwa=key, latitude=attrib["latitude"], longitude=attrib["longitude"]),
        power_level=10,
        code=attrib["code"]
    )
    for key, attrib in updated_pp_data["power_plants"].items()
]

with open("complete_pp_data.json", "w", encoding="utf-8") as f:
    json.dump(updated_pp_data, f)
    # 1. Przechodzimy przez listę i każdy obiekt zamieniamy z powrotem na słownik
    dane_do_zapisu = [plant.model_dump() for plant in pp_list]

    # 2. Standardowy zapis do pliku tekstowego
with open("complete_pp_data.json", "w", encoding="utf-8") as f:
    # indent=4 sprawi, że JSON będzie miał czytelne wcięcia
    # ensure_ascii=False gwarantuje, że "Żarnowiec" czy "Piotrków" zapiszą się z polskimi znakami, a nie jako krzaczki Unicode
    json.dump(dane_do_zapisu, f, indent=4, ensure_ascii=False)
