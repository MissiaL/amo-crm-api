"""Shared pytest fixtures — mock HTTP server for api_call.py tests."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import pytest


class RecordingHandler(BaseHTTPRequestHandler):
    """Records every request and replies with whatever the test queue says."""
    def log_message(self, *args, **kwargs):
        pass  # silence stderr access log

    def _handle(self, method):
        parsed = urlparse(self.path)
        body = b""
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length:
            body = self.rfile.read(length)
        self.server.requests.append({
            "method": method,
            "path": parsed.path,
            "query": parsed.query,
            "query_parsed": parse_qs(parsed.query, keep_blank_values=True),
            "headers": dict(self.headers),
            "body": body.decode("utf-8") if body else "",
        })
        if self.server.response_queue:
            status, payload, headers = self.server.response_queue.pop(0)
        else:
            status, payload, headers = 200, b'{"ok": true}', {}
        self.send_response(status)
        for k, v in {"Content-Type": "application/json", **headers}.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload if isinstance(payload, bytes) else json.dumps(payload).encode())

    def do_GET(self):    self._handle("GET")
    def do_POST(self):   self._handle("POST")
    def do_PATCH(self):  self._handle("PATCH")
    def do_DELETE(self): self._handle("DELETE")


@pytest.fixture
def mock_server():
    """Start a local HTTP server on a random port. Yields (base_url, server)."""
    server = HTTPServer(("127.0.0.1", 0), RecordingHandler)
    server.requests = []
    server.response_queue = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    yield f"http://127.0.0.1:{port}", server
    server.shutdown()
    server.server_close()
