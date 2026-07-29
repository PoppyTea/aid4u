from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from core.server.factory import ServerFactory, run_server


def test_server_factory_create_health_check() -> None:
    """Test if ServerFactory creates a valid FastAPI app with health check."""
    app = ServerFactory.create("test-service")
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "test-service"}
    assert app.title == "test-service"
    assert app.docs_url == "/docs"


def test_server_factory_create_middleware_logs_request() -> None:
    """Test if the HTTP middleware correctly logs the request using logfire."""
    app = ServerFactory.create("test-logging-service")
    client = TestClient(app)

    with patch("logfire.info") as mock_info:
        response = client.get("/health")
        assert response.status_code == 200
        mock_info.assert_called_once()
        args, kwargs = mock_info.call_args
        assert args[0] == "GET /health"
        assert kwargs["status"] == 200
        assert "elapsed_ms" in kwargs


def test_server_factory_logfire_missing_on_create(monkeypatch: Any) -> None:
    """Test ServerFactory.create does not crash when logfire is not installed."""
    import sys

    # Simulate missing logfire
    monkeypatch.setitem(sys.modules, "logfire", None)

    # Should not raise exception
    app = ServerFactory.create("test-no-logfire")
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200


def test_run_server() -> None:
    """Test if run_server calls uvicorn.run with correct parameters."""
    app = ServerFactory.create("test-run-server")
    with patch("uvicorn.run") as mock_run:
        run_server(app, port=9000, host="127.0.0.1")
        mock_run.assert_called_once_with(app, host="127.0.0.1", port=9000, log_level="warning")
