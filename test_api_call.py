"""Offline checks: python3 -m unittest -v test_api_call."""
import contextlib
import io
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import unittest
import urllib.parse
from unittest.mock import patch

from scripts import api_call


class ApiCallTests(unittest.TestCase):
    def run_dry(self, *args):
        output = io.StringIO()
        errors = io.StringIO()
        with patch.dict(os.environ, {"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "test-token"}), \
                patch.object(sys, "argv", ["api_call.py", "--method", "GET", "--dry-run", *args]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = api_call.main()
        return status, output.getvalue(), errors.getvalue()

    def test_query_and_filters_preserved(self):
        status, output, _ = self.run_dry(
            "--url", "/api/v4/contacts?with=leads",
            "--params", '{"filter[id][]": [123,456], "query": "Иванов"}',
        )
        self.assertEqual(status, 0)
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(output.strip()).query), {
            "with": ["leads"], "filter[id][]": ["123", "456"], "query": ["Иванов"],
        })
        self.assertNotIn("test-token", output)

    def test_dry_run_validates_json(self):
        for argument, value in [("--params", "[]"), ("--body", "invalid"), ("--headers", "[]")]:
            with self.subTest(argument=argument):
                status, output, errors = self.run_dry("--url", "/api/v4/account", argument, value)
                self.assertEqual(status, 1)
                self.assertEqual(output, "")
                self.assertIn("error:", errors)

    def test_account_host_enforced(self):
        for url in ["https://other.amocrm.ru/api/v4/account", "https://evil.example/", "http://demo.amocrm.ru/", "https://demo.amocrm.ru:444/"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                api_call.build_url(url, "demo")

    def test_redirect_rejected(self):
        requests = []

        class Receiver(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(302 if self.path == "/account" else 200)
                self.send_header("Location", "/token-target")
                self.end_headers()

            def log_message(self, *args):
                pass

        with HTTPServer(("127.0.0.1", 0), Receiver) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/account"
                with patch.dict(os.environ, {
                    "AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "test-token", "AMOCRM_ALLOW_TEST_URL": "1",
                }), patch.object(sys, "argv", ["api_call.py", "--method", "GET", "--url", url]), \
                        contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(api_call.main(), 1)
                self.assertEqual(requests, ["/account"])
            finally:
                server.shutdown()
                worker.join()

    def test_error_redacts_token(self):
        self.assertNotIn("test-token", api_call._classify_error(400, "echo test-token", {}, ("test-token",)))

    def test_uncertain_write_failure(self):
        errors = io.StringIO()
        with patch.dict(os.environ, {"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "test-token"}), \
                patch.object(sys, "argv", ["api_call.py", "--method", "POST", "--url", "/api/v4/leads", "--body", "[]"]), \
                patch.object(api_call.urllib.request, "build_opener") as opener, \
                contextlib.redirect_stderr(errors):
            opener.return_value.open.side_effect = TimeoutError("timed out")
            self.assertEqual(api_call.main(), 1)
        self.assertIn("outcome is unknown", errors.getvalue())
        self.assertIn("verify the outcome of writes", api_call._classify_error(504, "timeout", {}))


if __name__ == "__main__":
    unittest.main()
