"""Pobiera materiały drona dla s02e05: dokumentację API i mapę terenu.

Oba zasoby są statyczne (w odróżnieniu od `s02e02_electricity`'s mutowalnego
`electricity.png`) — bezpieczne do cache'owania w `data/input/`. Waliduje treść
przez `core.net` przed zapisem, bo `/data/{apikey}/{path}` potrafi zwrócić HTTP 200
z treścią błędu zamiast prawdziwego 404 dla złego URL-a (potwierdzone empirycznie
przy `mapa_dron.png` — zły URL do tego samego pliku).

Użycie:
    uv run python data/input/s02e05_drone/fetch_drone_assets.py
"""

from __future__ import annotations

from core.observability.setup import setup_observability

setup_observability()

from pathlib import Path

from core.hub.client import HubClient
from core.net import expect_binary

ASSETS_DIR = Path(__file__).parent
DRONE_HTML_PATH = ASSETS_DIR / "drone.html"
DRONE_PNG_PATH = ASSETS_DIR / "drone.png"


def fetch_all() -> list[Path]:
    """Pobiera brakujące zasoby (pomija te już obecne na dysku) i zwraca listę pobranych."""
    hub = HubClient()
    downloaded: list[Path] = []

    if not DRONE_HTML_PATH.exists():
        content = hub.get_public("dane/drone.html")
        DRONE_HTML_PATH.write_bytes(content)
        downloaded.append(DRONE_HTML_PATH)

    if not DRONE_PNG_PATH.exists():
        content = hub.get_data("drone.png", tolerate_503=True)
        expect_binary(content, "png", source="drone.png")
        DRONE_PNG_PATH.write_bytes(content)
        downloaded.append(DRONE_PNG_PATH)

    return downloaded


if __name__ == "__main__":
    result = fetch_all()
    if result:
        print(f"Pobrano {len(result)} nowych plików:")
        for path in result:
            print(f"  {path}")
    else:
        print("Wszystkie zasoby już obecne na dysku.")
