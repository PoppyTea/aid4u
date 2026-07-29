"""
Weryfikacja s01e02 (findhim) BEZ agenta / bez Function Calling.

Cel: sprawdzić, czy sama logika (haversine + dopasowanie najbliższej elektrowni)
i dane (FULL-power-plants-data.json, suspects.json) dają poprawną odpowiedź —
niezależnie od tego, co się dzieje w warstwie promptu/agenta (debugowanej
osobno). Deterministyczne: żadnego wywołania LLM. Jedyne wywołania sieciowe to
prawdziwe HTTP do hub.ag3nts.org (/api/location, /api/accesslevel, /verify).

Uruchom:
    uv run python tasks/s01e02_findhim/scripts/verify_without_agent.py --dry-run
    uv run python tasks/s01e02_findhim/scripts/verify_without_agent.py          # wysyła realnie
"""
from __future__ import annotations

from core.observability.setup import setup_observability

setup_observability()

import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

from core.hub import HubClient  # noqa: E402
from tasks.s01e02_findhim.solution import (  # noqa: E402
    PowerPlant,
    get_access_level,
    search_suspect_history_for_nearest_power_plant,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Prawdziwe koordynaty (Wikipedia: https://en.wikipedia.org/wiki/%C5%BBarnowiec_Nuclear_Power_Plant).
# FULL-power-plants-data.json ma błąd geokodowania — trafiło w INNĄ miejscowość
# o nazwie Żarnowiec (jest ich kilka w Polsce), nie w tę nad Bałtykiem, gdzie
# faktycznie stoi (nieukończona) elektrownia jądrowa.
REAL_ZARNOWIEC_LAT = 54.7392
REAL_ZARNOWIEC_LON = 18.0870


def load_plants() -> list[PowerPlant]:
    raw = json.loads((DATA_DIR / "FULL-power-plants-data.json").read_text(encoding="utf-8"))
    plants = []
    for entry in raw["power_plants"]:
        location = dict(entry["location"])
        if not isinstance(location.get("name"), str):
            location["name"] = entry["location_name"]
        if entry["location_name"] == "Żarnowiec":
            location["latitude"] = REAL_ZARNOWIEC_LAT
            location["longitude"] = REAL_ZARNOWIEC_LON
        plants.append(PowerPlant.model_validate({**entry, "location": location}))
    return plants


def load_suspects() -> list[dict]:
    return json.loads((DATA_DIR / "suspects.json").read_text(encoding="utf-8"))


def main(*, submit: bool) -> None:
    plants = load_plants()
    suspects = load_suspects()
    hub = HubClient()

    print("=== Dystanse per podejrzany (wszystkie elektrownie brane pod uwagę) ===")
    results = []
    for s in suspects:
        result = search_suspect_history_for_nearest_power_plant(
            hub, plants, s["name"], s["surname"], s["birthYear"]
        )
        results.append({**s, **result})
        print(f"  {s['name']:<10} {s['surname']:<12} -> {result['plant_code']}  ({result['distance_km']} km)")

    winner = min(results, key=lambda r: r["distance_km"])
    print(f"\nZwycięzca: {winner['name']} {winner['surname']} -> {winner['plant_code']} ({winner['distance_km']} km)")

    access_level = get_access_level(hub, winner["name"], winner["surname"], winner["birthYear"])
    answer = {
        "name": winner["name"],
        "surname": winner["surname"],
        "accessLevel": access_level,
        "powerPlant": winner["plant_code"],
    }
    print(f"\nOdpowiedź do wysłania: {answer}")

    if not submit:
        print("\n--dry-run — nie wysyłam do /verify.")
        return

    response = hub.submit("findhim", answer)
    flag = hub.get_flag(response)
    print(f"\nOdpowiedź huba: {response}")
    if flag:
        print(f"\n*** FLAGA: {flag} ***")
    else:
        print("\nBrak flagi w odpowiedzi — sprawdź response powyżej.")


if __name__ == "__main__":
    main(submit="--dry-run" not in sys.argv)
