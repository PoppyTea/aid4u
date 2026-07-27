"""
Inicjalizacja warstwy obserwabilności.

⚠️  ZAWSZE wywołaj setup_observability() jako PIERWSZĄ rzecz w run.py,
przed importem jakichkolwiek modułów LLM czy HTTP.
Inaczej auto-instrumentacja nie przechwyci wszystkich wywołań.

─── Logfire ─────────────────────────────────────────────────────────────────
Potrzebny: tylko LOGFIRE_TOKEN (write token).
Read token NIE jest potrzebny — używamy tylko do wysyłania telemetrii.

Logfire auto-instrumentuje po setup():
- instrument_anthropic() → każde wywołanie Anthropic SDK = span
- instrument_httpx()     → każdy HTTP request (hub, zewnętrzne API) = span
- instrument_fastapi()   → wywoływane osobno w ServerFactory

Dev sessions (LOGFIRE_TOKEN tymczasowy, 7 dni):
- Przydatne do jednorazowego lokalnego testowania bez stałego projektu.
- Nie używamy — mamy stały projekt z własnym write token.
- Jeśli chcesz wypróbować: użyj local_dev_session przez Logfire MCP.

─── Langfuse v4 ─────────────────────────────────────────────────────────────
SDK v4 — breaking changes względem v3:
- Inicjalizacja: Langfuse() nadal działa, ale get_client() to preferowany wzorzec
  do pobierania klienta w dowolnym miejscu kodu po inicjalizacji.
- update_current_trace() → propagate_attributes() (context manager)
- start_span() → start_observation()
- start_generation() → start_observation(as_type="generation")
- Smart span filtering: v4 domyślnie eksportuje tylko spany LLM.
  Jeśli potrzebujesz wszystkich spanów: Langfuse(should_export_span=lambda s: True)

⚠️  PRZED MODYFIKACJĄ TEGO PLIKU: użyj langfuse-docs MCP serwera.
    API Langfuse zmieniło się między v3 i v4. Wiedza treningowa może być nieaktualna.
"""

from __future__ import annotations

_initialized = False


def setup_observability() -> None:
    """Idempotentna inicjalizacja. Bezpieczne do wielokrotnego wywołania."""
    global _initialized
    if _initialized:
        return

    _setup_logfire()
    _setup_langfuse()

    _initialized = True


def _setup_logfire() -> None:
    import logfire
    from core.config import get_config

    cfg = get_config()
    token = cfg.logfire_token

    if token:
        logfire.configure(token=token, service_name="aid4u")
    else:
        # Tryb lokalny — spany widoczne w konsoli, nie wysyłane do chmury.
        # Przydatne przy pierwszym uruchomieniu bez konfiguracji Logfire.
        logfire.configure(send_to_logfire=False, service_name="aid4u")

    # Auto-instrumentacja — zero kodu w zadaniach
    logfire.instrument_anthropic()
    logfire.instrument_httpx()
    # instrument_fastapi() wywoływane osobno w ServerFactory


def _setup_langfuse() -> None:
    """
    Inicjalizacja Langfuse v4.

    Po wywołaniu Langfuse(), singleton jest dostępny globalnie przez get_client():
        from langfuse import get_client
        langfuse = get_client()

    Dekorator @observe (z langfuse) automatycznie tworzy trace dla każdej funkcji:
        from langfuse import observe
        @observe()
        def my_task(): ...

    Atrybuty trace (user_id, session_id, metadata) ustawiamy przez propagate_attributes():
        from langfuse import propagate_attributes
        with propagate_attributes(user_id="u1", session_id="s1", metadata={"k": "v"}):
            result = call_llm(...)
    """
    from core.config import get_config

    cfg = get_config()
    if not (cfg.langfuse_public_key and cfg.langfuse_secret_key):
        return

    try:
        from langfuse import Langfuse

        Langfuse(
            public_key=cfg.langfuse_public_key,
            secret_key=cfg.langfuse_secret_key,
            host=cfg.langfuse_host,
            # v4 domyślnie eksportuje tylko spany LLM (gen_ai.*, langfuse-sdk).
            # Odkomentuj poniższe jeśli chcesz eksportować WSZYSTKIE spany (zachowanie v3):
            # should_export_span=lambda span: True,
        )
    except Exception as e:
        import logfire

        logfire.warning(f"Langfuse init failed (non-fatal): {e}")
