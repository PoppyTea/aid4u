"""
Local proxy + static server for the s02e02_electricity manual clicker.

Browser fetch() calls straight to hub.ag3nts.org would hit CORS (that API is
built for server-side calls, not browser origins) — this stdlib http.server
sits in between, serving index.html and forwarding /api/* to the hub through
HubClient (apikey stays server-side, never touches the page source).

Run:  uv run python -m tasks.s02e02_electricity.webui.server
Then open http://127.0.0.1:8765
"""

from __future__ import annotations

# OS keyring (dbus/SecretService) hangs indefinitely in headless/sandboxed shells
# instead of failing fast — force the no-op backend so Config falls through to
# the .env value immediately. Must run before core.config is imported anywhere.
import keyring
from keyring.backends import fail as _keyring_fail

keyring.set_keyring(_keyring_fail.Keyring())

from core.observability.setup import setup_observability

setup_observability()

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core.hub.client import HubClient

TASK = "electricity"
STATIC_DIR = Path(__file__).parent
PORT = 8765

_log = logging.getLogger(__name__)
_hub = HubClient()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self._serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif self.path.startswith("/api/image"):
            self._proxy_image()
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/rotate":
            self._proxy_rotate()
        else:
            self.send_error(404)

    def _serve_file(self, path: Path, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def _proxy_image(self) -> None:
        reset = "reset=1" in self.path
        remote_path = "electricity.png" + ("?reset=1" if reset else "")
        try:
            data = _hub.get_data(remote_path)
        except Exception as exc:  # noqa: BLE001 — surface any hub error to the page
            self._send_json({"error": str(exc)}, status=502)
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _proxy_rotate(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        cell = body.get("cell", "")
        try:
            result = _hub.submit(TASK, {"rotate": cell})
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": str(exc)}, status=502)
            return
        self._send_json(result)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        _log.info(format, *args)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"electricity webui: http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
