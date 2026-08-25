"""
Rejestr promptów — jednostronna synchronizacja kod → Langfuse.

Kontrakt (pełne uzasadnienie: `strategy/observability.md`): treść promptu w kodzie
zadania jest JEDYNYM źródłem prawdy. Ten moduł nigdy nie pobiera treści promptu z
Langfuse do decydowania o zachowaniu — tylko wypycha aktualną wersję i pobiera
lekką referencję do podpięcia pod generację (`start_observation(prompt=...)`),
żeby w panelu dało się porównać wersje/koszt/wyniki.

Wzorzec przepisany z `4th-devs/03_01_observability/src/core/tracing/prompts.ts`
(reguła "4th-devs najpierw" z `aid4u/AGENTS.md`) — SHA-256 diff, push tylko gdy
treść się zmieniła, stan trzymany lokalnie żeby nie pytać Langfuse o niezmieniony
prompt przy każdym uruchomieniu.

Użycie w zadaniu:
    from core.observability.prompts import sync_prompt

    _PROMPT_REF = sync_prompt("s03e01-phrase-classifier", SYSTEM_CLASSIFY)
    ...
    llm.structured(messages, Schema, system=SYSTEM_CLASSIFY, prompt_name=_PROMPT_REF.name)

Błąd sieci / brak kluczy Langfuse → `PromptRef.is_fallback=True`, zadanie leci
dalej. Observability nigdy nie blokuje zdobycia flagi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

_STATE_FILE = Path(".langfuse-prompt-state.json")

# Referencje dostępne w bieżącym procesie — wypełniane przez sync_prompt(),
# czytane przez get_prompt_ref() (np. z CostTrackMiddleware, patrz middleware.py).
_prompt_refs: dict[str, PromptRef] = {}


@dataclass(frozen=True)
class PromptRef:
    """
    Lekka referencja do wersji promptu w Langfuse.

    `client` to obiekt SDK (`TextPromptClient`/`ChatPromptClient`) gotowy do
    podania jako `start_observation(prompt=...)` — `None` gdy synchronizacja
    się nie powiodła (`is_fallback=True`).
    """

    name: str
    version: int | None
    client: Any | None
    is_fallback: bool


def get_prompt_ref(name: str) -> PromptRef | None:
    """Zwraca referencję zsynchronizowaną wcześniej w tym procesie przez `sync_prompt()`, albo None."""
    return _prompt_refs.get(name)


def sync_prompt(name: str, content: str, *, tags: list[str] | None = None) -> PromptRef:
    """
    Synchronizuje `content` pod `name` w rejestrze promptów Langfuse.

    Push tylko jeśli SHA-256 treści zmienił się od ostatniego zapisanego stanu
    (`.langfuse-prompt-state.json`, gitignored — lokalny cache, nie źródło
    prawdy). Zawsze próbuje dociągnąć obiekt promptu do podpięcia pod
    generację; przy jakimkolwiek błędzie (brak kluczy, sieć, API) zwraca
    fallback zamiast rzucać — to narzędzie pomiarowe, nie bramka blokująca.
    """
    try:
        from core.config import get_config

        cfg = get_config()
        if not (cfg.langfuse_public_key and cfg.langfuse_secret_key):
            return PromptRef(name=name, version=None, client=None, is_fallback=True)

        from langfuse import get_client

        client = get_client()
        content_hash = sha256(content.encode("utf-8")).hexdigest()
        state = _load_state()
        cached = state.get(name)

        if cached is not None and cached.get("content_hash") == content_hash:
            version = cached["version"]
        else:
            created = client.create_prompt(
                name=name,
                prompt=content,
                labels=["production"],
                tags=tags or [],
                type="text",
            )
            version = created.version
            state[name] = {"content_hash": content_hash, "version": version}
            _save_state(state)

        prompt_client = client.get_prompt(name=name, version=version, type="text")
        ref = PromptRef(name=name, version=version, client=prompt_client, is_fallback=False)
    except Exception:
        import logfire

        logfire.warning(f"Prompt sync failed for '{name}' — falling back", exc_info=True)
        ref = PromptRef(name=name, version=None, client=None, is_fallback=True)

    _prompt_refs[name] = ref
    return ref


def _load_state() -> dict[str, dict[str, Any]]:
    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(state: dict[str, dict[str, Any]]) -> None:
    try:
        _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        import logfire

        logfire.warning("Failed to save prompt sync state", exc_info=True)
