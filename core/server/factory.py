"""
Factory pattern — ServerFactory.

Tworzy gotowy serwer FastAPI dla zadań wymagających publicznego endpointu
(proxy, negotiations, domatowo, itp.).

Każdy serwer z pudełka dostaje:
- Auto-instrumentację Logfire (wszystkie requesty jako spany)
- Health check endpoint GET /health
- Logowanie requestów z czasem odpowiedzi
- Obsługę błędów z odpowiednimi kodami HTTP

Użycie w zadaniu:
    from core.server import ServerFactory, run_server

    app = ServerFactory.create("s01e03-proxy")

    @app.post("/")
    async def handle(body: MyRequest) -> MyResponse:
        ...

    # W run.py zadania:
    run_server(app, port=8000)
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, Request, Response


class ServerFactory:
    @staticmethod
    def create(service_name: str) -> FastAPI:
        """
        Tworzy FastAPI z health check i logowaniem.

        Args:
            service_name: Nazwa serwisu widoczna w logach i Logfire (np. 's01e03-proxy')
        """
        app = FastAPI(title=service_name, docs_url="/docs")

        # Auto-instrumentacja Logfire — każdy request = span
        logfire_mod = None
        try:
            import logfire

            logfire.instrument_fastapi(app)
            logfire_mod = logfire
        except Exception:
            pass  # Logfire opcjonalne — serwer działa bez niego

        # Middleware: logowanie czasu odpowiedzi
        @app.middleware("http")
        async def log_requests(request: Request, call_next) -> Response:
            start = time.perf_counter()
            response = await call_next(request)
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            if logfire_mod is not None:
                try:
                    logfire_mod.info(
                        f"{request.method} {request.url.path}",
                        status=response.status_code,
                        elapsed_ms=elapsed,
                    )
                except Exception:
                    pass
            return response

        @app.get("/health")
        async def health() -> dict[str, Any]:
            return {"status": "ok", "service": service_name}

        return app


def run_server(app: FastAPI, *, port: int = 8000, host: str = "0.0.0.0") -> None:
    """
    Uruchamia serwer. Blokujące — wywołuj na końcu skryptu zadania.

    Zatrzymanie: Ctrl+C (sygnał SIGINT obsługiwany przez uvicorn)
    """
    import uvicorn
    from rich.console import Console

    console = Console()
    console.print(f"[bold green]Server starting[/] → http://{host}:{port}")
    console.print(f"[dim]Health check: http://localhost:{port}/health[/]")

    uvicorn.run(app, host=host, port=port, log_level="warning")
