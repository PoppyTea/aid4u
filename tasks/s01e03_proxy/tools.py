"""
Definicje narzędzi (function calling) i executor dla agenta s01e03.

Zwykłe funkcje wywoływane przez LLMClient.run_agent_loop — MCP nie jest
wymagane w tym zadaniu (patrz karta lekcji: bezpośrednie wywołania funkcji
z kodu Pythona są szybsze i wystarczające, efficiency mode).
"""

from __future__ import annotations

from typing import Any, Callable

from core.llm.types import Tool
from tasks.s01e03_proxy.packages_data import PackageStore

CHECK_PACKAGE_TOOL = Tool(
    name="check_package",
    description="Sprawdza status, zawartość i aktualny cel paczki po jej numerze.",
    parameters={
        "type": "object",
        "properties": {
            "package_id": {"type": "string", "description": "Numer paczki, np. PKG10172494"},
        },
        "required": ["package_id"],
    },
)

REDIRECT_PACKAGE_TOOL = Tool(
    name="redirect_package",
    description="Przekierowuje paczkę pod nowy adres/cel docelowy.",
    parameters={
        "type": "object",
        "properties": {
            "package_id": {"type": "string", "description": "Numer paczki"},
            "destination": {"type": "string", "description": "Nowe miasto/kod celu docelowego"},
        },
        "required": ["package_id", "destination"],
    },
)

TOOLS = [CHECK_PACKAGE_TOOL, REDIRECT_PACKAGE_TOOL]


def make_tool_executor(store: PackageStore) -> Callable[[str, dict[str, Any]], str]:
    """Buduje tool_executor związany z konkretnym PackageStore (per-sesja/per-serwer)."""

    def executor(name: str, args: dict[str, Any]) -> str:
        if name == "check_package":
            package = store.get(args["package_id"])
            if package is None:
                return f"Nie znaleziono paczki {args['package_id']}."
            return (
                f"Paczka {package.package_id}: zawartość={package.contents}, "
                f"lokalizacja={package.current_location}, cel={package.destination}."
            )
        if name == "redirect_package":
            return store.redirect(args["package_id"], args["destination"])
        raise ValueError(f"Nieznane narzędzie: {name}")

    return executor
