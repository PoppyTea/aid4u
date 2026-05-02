"""
Dekoratory i helpery obserwabilności.

⚠️  PRZED MODYFIKACJĄ: użyj langfuse-docs MCP. API Langfuse v4 różni się od v3.

─── Kiedy używać czego ──────────────────────────────────────────────────────

@langfuse_observe()   → Tworzenie trace w Langfuse. Używaj na metodach solve()
                        i innych funkcjach biznesowych (zadania kursu).
                        Automatycznie tworzy trace i obserwację.

@logfire_span()       → Ręczny span w Logfire dla złożonej logiki wewnętrznej.
                        Logfire auto-instrumentuje Anthropic i HTTPX — tu tylko
                        gdy potrzebujesz dodatkowego spanu dla własnego kodu.

propagate_attrs()     → Shorthand do ustawiania user_id/session_id/metadata
                        na bieżącej i wszystkich potomnych obserwacjach (Langfuse v4).

─── Czego NIE musisz robić ──────────────────────────────────────────────────
- NIE owijaj wywołań self.llm.chat() — Logfire instrument_anthropic() robi to auto.
- NIE owijaj HTTP requestów do hubu — Logfire instrument_httpx() robi to auto.
- NIE używaj update_current_trace() — to API v3, w v4 użyj propagate_attributes().
"""
from __future__ import annotations

import asyncio
import functools
from contextlib import contextmanager
from typing import Any, Callable, Generator, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


# ─── Langfuse v4 ──────────────────────────────────────────────────────────────

def langfuse_observe(name: str | None = None) -> Callable[[F], F]:
    """
    Owija funkcję dekoratorem @observe z Langfuse v4.

    Tworzy trace + obserwację w Langfuse dla każdego wywołania.
    Bezpieczne gdy Langfuse nie jest skonfigurowany — no-op.

    Użycie:
        @langfuse_observe("solve_people_task")
        def solve(self, data): ...

        @langfuse_observe()  # użyje nazwy funkcji
        async def fetch_all_pages(): ...
    """
    def decorator(fn: F) -> F:
        try:
            from langfuse import observe as _lf_observe
            decorated = _lf_observe(name=name or fn.__name__)(fn)
        except ImportError:
            decorated = fn  # Langfuse niezainstalowany — no-op

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return decorated(*args, **kwargs)

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await decorated(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(fn) else wrapper  # type: ignore

    return decorator


@contextmanager
def propagate_attrs(
    *,
    trace_name: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, str] | None = None,
    tags: list[str] | None = None,
    version: str | None = None,
) -> Generator[None, None, None]:
    """
    Langfuse v4: propaguje atrybuty do bieżącej i wszystkich potomnych obserwacji.

    Zastępuje update_current_trace() z v3.
    metadata musi być dict[str, str] z wartościami do 200 znaków (wymóg v4).

    Użycie:
        with propagate_attrs(user_id="u1", session_id="sess-abc"):
            result = self.llm.chat(messages)
    """
    try:
        from langfuse import propagate_attributes

        kwargs: dict[str, Any] = {}
        if trace_name is not None:
            kwargs["trace_name"] = trace_name
        if user_id is not None:
            kwargs["user_id"] = user_id
        if session_id is not None:
            kwargs["session_id"] = session_id
        if metadata is not None:
            kwargs["metadata"] = metadata
        if tags is not None:
            kwargs["tags"] = tags
        if version is not None:
            kwargs["version"] = version

        with propagate_attributes(**kwargs):
            yield
    except ImportError:
        yield  # Langfuse niezainstalowany — no-op


# ─── Logfire ──────────────────────────────────────────────────────────────────

def logfire_span(name: str | None = None) -> Callable[[F], F]:
    """
    Owija funkcję ręcznym spanem Logfire.

    Używaj tylko gdy potrzebujesz spanu dla własnej logiki —
    Logfire auto-instrumentuje Anthropic i HTTPX po setup_observability().

    Użycie:
        @logfire_span("parse_and_filter")
        def heavy_processing(data: bytes) -> list[dict]: ...

        @logfire_span()  # użyje nazwy funkcji
        async def fetch_all_pages() -> list: ...
    """
    def decorator(fn: F) -> F:
        span_name = name or fn.__qualname__

        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                import logfire
                with logfire.span(span_name):
                    return await fn(*args, **kwargs)
            return async_wrapper  # type: ignore
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                import logfire
                with logfire.span(span_name):
                    return fn(*args, **kwargs)
            return sync_wrapper  # type: ignore

    return decorator


# ─── Backwards compat alias (stara nazwa z projektu) ─────────────────────────
# Stara nazwa @observe działała tylko z Logfire.
# Nowa preferowana ścieżka: @langfuse_observe() dla trace LLM, @logfire_span() dla spanów infrastruktury.
observe = logfire_span
