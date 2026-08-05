"""
Weryfikacja s01e02 (findhim) BEZ agenta / bez Function Calling.

Cel: sprawdzić, czy sama logika (haversine + dopasowanie najbliższej elektrowni)
i dane (lista elektrowni z huba, suspects.json) dają poprawną odpowiedź —
niezależnie od tego, co się dzieje w warstwie promptu/agenta (debugowanej
osobno). Deterministyczne: żadnego wywołania LLM. Wywołania sieciowe: prawdziwe
HTTP do hub.ag3nts.org (/data, /api/location, /api/accesslevel, /verify) oraz
do Nominatim (geokodowanie elektrowni — patrz resolve_all_power_plants()).

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
    parse_power_plants,
    resolve_all_power_plants,
    search_suspect_history_for_nearest_power_plant,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_plants(hub: HubClient) -> list[PowerPlant]:
    """Ten sam pobór + geokodowanie co FindhimTask.fetch_data()/solve() —
    żadnego statycznego pliku, więc żadnego ryzyka stałej/nieaktualnej listy."""
    raw = hub.get_data("findhim_locations.json")
    plants = parse_power_plants(json.loads(raw))
    return resolve_all_power_plants(plants)


def load_suspects() -> list[dict]:
    return json.loads((DATA_DIR / "suspects.json").read_text(encoding="utf-8"))


def main(*, submit: bool) -> None:
    hub = HubClient()
    plants = load_plants(hub)
    suspects = load_suspects()

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
