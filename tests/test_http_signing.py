"""Verify api_call.py makes real HTTP requests with proper Bearer auth."""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "api_call.py"


def run_script(args, env_overrides):
    env = {**os.environ, **env_overrides}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_get_sends_bearer_token(mock_server):
    base_url, server = mock_server
    server.response_queue.append((200, {"account_id": 42}, {}))

    rc, out, err = run_script(
        ["--method", "GET", "--url", f"{base_url}/api/v4/account"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok-abc"},
    )

    assert rc == 0, err
    assert json.loads(out) == {"account_id": 42}
    assert len(server.requests) == 1
    assert server.requests[0]["headers"]["Authorization"] == "Bearer tok-abc"


def test_post_sends_json_body_and_content_type(mock_server):
    base_url, server = mock_server
    server.response_queue.append((201, {"_embedded": {"leads": [{"id": 1}]}}, {}))

    rc, out, err = run_script(
        [
            "--method", "POST",
            "--url", f"{base_url}/api/v4/leads",
            "--body", json.dumps([{"name": "Test", "price": 100}]),
        ],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 0, err
    assert server.requests[0]["headers"]["Content-Type"] == "application/json"
    assert json.loads(server.requests[0]["body"]) == [{"name": "Test", "price": 100}]


def test_query_params_are_encoded(mock_server):
    base_url, server = mock_server
    server.response_queue.append((200, {"_embedded": {"leads": []}}, {}))

    rc, out, err = run_script(
        [
            "--method", "GET",
            "--url", f"{base_url}/api/v4/leads",
            "--params", json.dumps({"limit": "50", "page": "1"}),
        ],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 0, err
    q = server.requests[0]["query_parsed"]
    assert q["limit"] == ["50"]
    assert q["page"] == ["1"]


def test_extra_headers_are_merged(mock_server):
    base_url, server = mock_server
    server.response_queue.append((200, {"ok": True}, {}))

    rc, out, err = run_script(
        [
            "--method", "GET",
            "--url", f"{base_url}/api/v4/account",
            "--headers", json.dumps({"X-Custom": "foo"}),
        ],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 0, err
    assert server.requests[0]["headers"]["X-Custom"] == "foo"
    assert server.requests[0]["headers"]["Authorization"] == "Bearer tok"


def test_204_no_content_returns_empty_string(mock_server):
    base_url, server = mock_server
    server.response_queue.append((204, b"", {}))

    rc, out, err = run_script(
        ["--method", "DELETE", "--url", f"{base_url}/api/v4/leads/1"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 0, err
    assert out.strip() == ""


def test_extra_headers_cannot_override_authorization(mock_server):
    base_url, server = mock_server
    server.response_queue.append((200, {"ok": True}, {}))

    rc, out, err = run_script(
        [
            "--method", "GET",
            "--url", f"{base_url}/api/v4/account",
            "--headers", json.dumps({"Authorization": "Bearer evil"}),
        ],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "real"},
    )

    assert rc == 0, err
    assert server.requests[0]["headers"]["Authorization"] == "Bearer real"
