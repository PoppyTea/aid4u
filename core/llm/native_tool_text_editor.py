"""
Natywne narzędzie Anthropic: text_editor (client-executed).

Jak bash — wykonywane PO STRONIE KLIENTA: model wysyła polecenie edycji pliku
(`view` / `create` / `str_replace` / `insert`) w bloku `tool_use`, aplikacja je
wykonuje lokalnie i odsyła wynik jako `tool_result`. Świadomie POZA
LLMProvider/LLMClient, patrz native_tool_web_search.py po uzasadnienie
architektury.

⚠️  BEZPIECZEŃSTWO: w przeciwieństwie do `BashToolExecutor` (gdzie sandboxing to
tylko zalecenie), `TextEditorToolExecutor` WYMAGA `root` w konstruktorze —
każda ścieżka jest rozwiązywana względem niego i walidowana, żeby nie wyszła
poza `root` (blokada path traversal, np. `../../etc/passwd`). Dowolny zapis do
pliku poza świadomie wybranym katalogiem jest bardziej niebezpieczny niż
pojedyncze polecenie shell, więc tu nie ma "domyślnie bez ograniczeń".

Użycie:
    from core.llm.native_tool_text_editor import (
        run_text_editor_tool_loop,
        TextEditorToolExecutor,
    )

    response = run_text_editor_tool_loop(
        config.anthropic_key,
        "Popraw literówkę 'recieve' na 'receive' w notes.txt.",
        executor=TextEditorToolExecutor(root="/tmp/sandbox"),
    )
    print(response.content)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from core.llm.types import LLMResponse

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_TOOL_TYPE = "text_editor_20250728"
_TOOL_NAME = "str_replace_based_edit_tool"


@dataclass
class TextEditorToolExecutor:
    """
    Domyślny executor — czyta/pisze pliki lokalnie, ograniczony do `root`.

    root: katalog, poza który żadna operacja nie może wyjść. Wymagany —
        celowo brak wartości domyślnej.
    """

    root: str

    def __post_init__(self) -> None:
        self._root = Path(self.root).resolve()

    def __call__(self, tool_input: dict[str, Any]) -> str:
        command = tool_input.get("command")
        path = self._resolve(tool_input.get("path", ""))

        if command == "view":
            return self._view(path, tool_input.get("view_range"))
        if command == "create":
            return self._create(path, tool_input.get("file_text", ""))
        if command == "str_replace":
            return self._str_replace(path, tool_input["old_str"], tool_input["new_str"])
        if command == "insert":
            return self._insert(path, tool_input["insert_line"], tool_input["new_str"])
        raise ValueError(f"Nieznane polecenie text_editor: {command!r}")

    def _resolve(self, raw_path: str) -> Path:
        candidate = (self._root / raw_path.lstrip("/")).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise ValueError(f"Ścieżka poza dozwolonym katalogiem: {raw_path!r}")
        return candidate

    def _view(self, path: Path, view_range: list[int] | None) -> str:
        if path.is_dir():
            names = sorted(p.name for p in path.iterdir())
            return "\n".join(names)
        lines = path.read_text().splitlines()
        start, end = (view_range[0], view_range[1]) if view_range else (1, len(lines))
        numbered = [f"{i}: {lines[i - 1]}" for i in range(start, min(end, len(lines)) + 1)]
        return "\n".join(numbered)

    def _create(self, path: Path, file_text: str) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file_text)
        return f"Utworzono {path.name} ({len(file_text)} znaków)."

    def _str_replace(self, path: Path, old_str: str, new_str: str) -> str:
        content = path.read_text()
        occurrences = content.count(old_str)
        if occurrences == 0:
            raise ValueError("old_str nie znaleziony w pliku.")
        if occurrences > 1:
            raise ValueError(f"old_str występuje {occurrences} razy — musi być unikalny.")
        path.write_text(content.replace(old_str, new_str, 1))
        return f"Zastąpiono fragment w {path.name}."

    def _insert(self, path: Path, insert_line: int, new_str: str) -> str:
        lines = path.read_text().splitlines()
        lines.insert(insert_line, new_str)
        path.write_text("\n".join(lines) + "\n")
        return f"Wstawiono tekst po linii {insert_line} w {path.name}."


def run_text_editor_tool_loop(
    api_key: str,
    prompt: str,
    *,
    executor: Callable[[dict[str, Any]], str],
    model: str = _DEFAULT_MODEL,
    system: str | None = None,
    max_tokens: int = 4096,
    max_iterations: int = 10,
) -> LLMResponse:
    """
    Pętla agentowa z natywnym narzędziem text_editor.

    executor: (tool_input: dict) -> output tekstowy. Brak wartości domyślnej —
        podaj jawnie `TextEditorToolExecutor(root=...)`, patrz ostrzeżenie
        bezpieczeństwa w docstringu modułu.
    max_iterations: zabezpieczenie przed nieskończoną pętlą wywołań narzędzia.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    tool = {"type": _TOOL_TYPE, "name": _TOOL_NAME}
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
            if getattr(block, "type", None) == "tool_use" and block.name == _TOOL_NAME
        ]
        if not tool_use_blocks:
            return _final_response(response)

        messages.append(
            {"role": "assistant", "content": [block.model_dump() for block in response.content]}
        )
        messages.append({"role": "user", "content": _run_tools(tool_use_blocks, executor)})

    return _final_response(response) if response is not None else LLMResponse(
        content="", model=model, input_tokens=0, output_tokens=0
    )


def _run_tools(
    tool_use_blocks: list[Any], executor: Callable[[dict[str, Any]], str]
) -> list[dict[str, Any]]:
    tool_results = []
    for block in tool_use_blocks:
        try:
            output = executor(block.input)
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
