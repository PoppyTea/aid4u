"""
Natywne narzędzie Anthropic: bash (client-executed).

W przeciwieństwie do web_search/code_execution, bash jest wykonywany PO STRONIE
KLIENTA: model prosi o polecenie shell w bloku `tool_use`, aplikacja je uruchamia
i odsyła wynik jako `tool_result` w kolejnej turze — stąd pętla, nie pojedyncze
wywołanie. Świadomie POZA LLMProvider/LLMClient, patrz native_tool_web_search.py
po uzasadnienie architektury.

⚠️  BEZPIECZEŃSTWO: to narzędzie daje modelowi wykonanie DOWOLNYCH poleceń shell
na maszynie, na której działa `BashToolExecutor`. Używaj tylko w zaufanym/
piaskownicowym środowisku (kontener, jednorazowa VM) i zawsze ustaw `cwd` na
katalog roboczy zadania — nigdy nie zostawiaj domyślnego cwd na maszynie
z realnymi danymi/sekretami bez przemyślanego ograniczenia.

Ten executor NIE utrzymuje stanu powłoki między wywołaniami (brak prawdziwej
persystentnej sesji bash) — jeśli model poprosi o `restart` zamiast `command`,
zwracamy no-op zamiast próby symulacji restartu sesji.

Użycie:
    from core.llm.native_tool_bash import run_bash_tool_loop, BashToolExecutor

    response = run_bash_tool_loop(
        config.anthropic_key,
        "Sprawdź która wersja Pythona jest zainstalowana.",
        executor=BashToolExecutor(cwd="/tmp/sandbox", timeout=10.0),
    )
    print(response.content)
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from core.llm.types import LLMResponse

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_TOOL_TYPE = "bash_20250124"


@dataclass
class BashToolExecutor:
    """
    Domyślny executor — uruchamia polecenia lokalnie przez `subprocess`.

    cwd: katalog roboczy poleceń. Ustaw jawnie — domyślny `None` dziedziczy cwd
        procesu Pythona, co zwykle NIE jest tym, czego chcesz w produkcji.
    timeout: limit czasu pojedynczego polecenia w sekundach.
    """

    cwd: str | None = None
    timeout: float = 30.0

    def __call__(self, command: str) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                timeout=self.timeout,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired:
            return f"ERROR: command timed out after {self.timeout}s"

        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[exit code {result.returncode}]"
        return output


def run_bash_tool_loop(
    api_key: str,
    prompt: str,
    *,
    executor: Callable[[str], str] | None = None,
    model: str = _DEFAULT_MODEL,
    system: str | None = None,
    max_tokens: int = 4096,
    max_iterations: int = 10,
) -> LLMResponse:
    """
    Pętla agentowa z natywnym narzędziem bash.

    executor: (command: str) -> output tekstowy. Domyślnie `BashToolExecutor()`
        — patrz ostrzeżenie bezpieczeństwa w docstringu modułu przed użyciem
        domyślnego executora bez jawnego `cwd`.
    max_iterations: zabezpieczenie przed nieskończoną pętlą wywołań narzędzia.
    """
    import anthropic

    exec_fn = executor or BashToolExecutor()
    client = anthropic.Anthropic(api_key=api_key)
    tool = {"type": _TOOL_TYPE, "name": "bash"}
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

    response = None
    for _ in range(max_iterations):
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "tools": [tool],
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)

        tool_use_blocks = [
            block
            for block in response.content
            if getattr(block, "type", None) == "tool_use" and block.name == "bash"
        ]
        if not tool_use_blocks:
            return _final_response(response)

        messages.append(
            {"role": "assistant", "content": [block.model_dump() for block in response.content]}
        )
        messages.append({"role": "user", "content": _run_tools(tool_use_blocks, exec_fn)})

    return _final_response(response) if response is not None else LLMResponse(
        content="", model=model, input_tokens=0, output_tokens=0
    )


def _run_tools(tool_use_blocks: list[Any], exec_fn: Callable[[str], str]) -> list[dict[str, Any]]:
    tool_results = []
    for block in tool_use_blocks:
        command = block.input.get("command")
        try:
            output = (
                exec_fn(command)
                if command is not None
                else "OK (no persistent shell session to restart in this executor)"
            )
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        except Exception as exc:  # executor failures shouldn't kill the agent loop
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"ERROR: {exc}",
                    "is_error": True,
                }
            )
    return tool_results


def _final_response(response: Any) -> LLMResponse:
    text = " ".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    return LLMResponse(
        content=text,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
