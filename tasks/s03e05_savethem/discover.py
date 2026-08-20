"""
S03E05 — faza odkrywania: zrzut wszystkiego, co wiedzą narzędzia Centrali.

To zadanie nie daje statycznej listy narzędzi — jest tylko `/api/toolsearch`, które
na każde zapytanie zwraca **3 najlepiej dopasowane** wpisy, nigdy wszystkich. Stąd
strategia: zadać wiele zapytań pod różne słowa kluczowe i zebrać sumę wyników.

Dopasowanie jest SŁOWOKLUCZOWE (odpowiedź niesie `score` i `matched_keywords`), więc
zapytania są układane pod słowa z opisów narzędzi, nie pod ładne zdania. Wszystkie
narzędzia rozmawiają **wyłącznie po angielsku** — stąd angielskie zapytania mimo
polskiego repo.

Uruchomienie (raz, wynik commitowany):
    uv run python -m tasks.s03e05_savethem.discover

Zrzuty lądują w `data/input/s03e05_savethem/` i to one — nie żywe API — są wejściem
dla solvera. Dzięki temu `terrain.py` i testy działają offline.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import json
from pathlib import Path
from typing import Any

from rich.console import Console

from core.hub import HubClient

OUT_DIR = Path("data/input/s03e05_savethem")
_console = Console()

# Zapytania dobrane pod słowa, które faktycznie padają w opisach narzędzi
# ("notes", "terrain", "map", "vehicle"), a nie pod naturalność zdania —
# toolsearch punktuje pokrycie słów kluczowych.
TOOL_QUERIES = (
    "I need notes about movement rules and terrain",
    "map of the area and locations",
    "vehicles and their fuel consumption",
    "how much food and fuel does each vehicle use",
    "rules for crossing water rivers and rocks",
    "how to get off the vehicle and walk on foot",
)

# Zapytania zadawane KAŻDEMU odkrytemu narzędziu. Skoro zwraca tylko 3 wyniki na
# zapytanie, jedno pytanie nie wystarcza — pytamy o każdy aspekt osobno.
CONTENT_QUERIES = (
    "Skolwin",
    "map",
    "terrain legend symbols",
    "movement rules",
    "vehicles",
    "fuel consumption",
    "food consumption",
    "walking on foot",
    "dismount get off vehicle",
    "water river crossing",
    "rocks trees obstacles",
    "start position",
)


def search_tools(hub: HubClient) -> dict[str, dict[str, Any]]:
    """
    Odpytuje `toolsearch` wieloma zapytaniami i scala wyniki w jeden słownik.

    Zwraca mapę `nazwa narzędzia -> deskryptor`. Scalanie jest konieczne, bo każde
    pojedyncze zapytanie widzi najwyżej 3 narzędzia.
    """
    found: dict[str, dict[str, Any]] = {}
    for query in TOOL_QUERIES:
        response = hub.post_api("/api/toolsearch", {"query": query})
        tools = response.get("tools") or []
        for tool in tools:
            name = tool.get("name")
            if name and name not in found:
                found[name] = tool
                _console.print(f"  [green]+[/] {name} → {tool.get('url')} — {tool.get('description')}")
        _console.print(f"[dim]  ({query!r}: {len(tools)} wyników)[/]")
    return found


def query_tool(hub: HubClient, url: str, queries: tuple[str, ...]) -> dict[str, Any]:
    """
    Zadaje narzędziu serię zapytań i zwraca surowe odpowiedzi pod kluczem zapytania.

    Błąd pojedynczego zapytania nie przerywa zrzutu — część endpointów bywa 404
    (społeczność zgłasza to dla `/api/wehicles` i wariantów pisowni), a resztę i tak
    chcemy zebrać.
    """
    out: dict[str, Any] = {}
    for query in queries:
        try:
            out[query] = hub.post_api(url, {"query": query})
        except Exception as exc:  # noqa: BLE001 — zrzut ma przetrwać częściowe błędy
            out[query] = {"_error": f"{type(exc).__name__}: {exc}"}
            _console.print(f"    [yellow]![/] {url} {query!r}: {type(exc).__name__}")
    return out


def main() -> None:
    """Odkrywa narzędzia, odpytuje każde i zapisuje surowe odpowiedzi do `data/input/`."""
    hub = HubClient()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    _console.print("[bold]1. Szukam narzędzi[/]")
    tools = search_tools(hub)
    (OUT_DIR / "tools.json").write_text(
        json.dumps(tools, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _console.print(f"[bold]Znalezione narzędzia:[/] {', '.join(sorted(tools)) or 'BRAK'}")

    _console.print("\n[bold]2. Odpytuję każde narzędzie[/]")
    for name, tool in sorted(tools.items()):
        url = tool.get("url")
        if not url:
            continue
        _console.print(f"  [cyan]{name}[/] ({url})")
        dump = query_tool(hub, url, CONTENT_QUERIES)
        (OUT_DIR / f"{name}.json").write_text(
            json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    _console.print(f"\n[green]Zrzut w {OUT_DIR}[/]")


if __name__ == "__main__":
    main()
