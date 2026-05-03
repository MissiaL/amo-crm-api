"""Verify api_call.py classifies HTTP errors with actionable messages."""
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


def test_401_says_token_invalid_or_expired(mock_server):
    base_url, server = mock_server
    server.response_queue.append((401, {"detail": "Unauthorized"}, {}))

    rc, out, err = run_script(
        ["--method", "GET", "--url", f"{base_url}/api/v4/account"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 1
    assert "AMOCRM_TOKEN" in err
    assert "expired" in err.lower() or "invalid" in err.lower()


def test_403_says_no_permission(mock_server):
    base_url, server = mock_server
    server.response_queue.append((403, {"detail": "Forbidden"}, {}))

    rc, out, err = run_script(
        ["--method", "GET", "--url", f"{base_url}/api/v4/leads"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 1
    assert "permission" in err.lower() or "rights" in err.lower()


def test_404_includes_body(mock_server):
    base_url, server = mock_server
    server.response_queue.append((404, {"detail": "Not Found"}, {}))

    rc, out, err = run_script(
        ["--method", "GET", "--url", f"{base_url}/api/v4/leads/999"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 1
    assert "404" in err or "not found" in err.lower()


def test_429_reads_retry_after(mock_server):
    base_url, server = mock_server
    server.response_queue.append((429, {"detail": "rate limit"}, {"Retry-After": "30"}))

    rc, out, err = run_script(
        ["--method", "GET", "--url", f"{base_url}/api/v4/leads"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 1
    assert "30" in err
    assert "wait" in err.lower() or "retry" in err.lower()


def test_500_says_server_side(mock_server):
    base_url, server = mock_server
    server.response_queue.append((503, {"error": "boom"}, {}))

    rc, out, err = run_script(
        ["--method", "GET", "--url", f"{base_url}/api/v4/leads"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 1
    assert "503" in err
    assert "server" in err.lower()


def test_400_includes_validation_errors(mock_server):
    base_url, server = mock_server
    body = {"validation-errors": [{"errors": [{"path": "name", "detail": "required"}]}]}
    server.response_queue.append((400, body, {}))

    rc, out, err = run_script(
        [
            "--method", "POST",
            "--url", f"{base_url}/api/v4/leads",
            "--body", json.dumps([{}]),
        ],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 1
    assert "400" in err
    assert "name" in err  # validation detail surfaces in stderr


def test_token_never_appears_in_error_output(mock_server):
    base_url, server = mock_server
    server.response_queue.append((401, {"detail": "bad"}, {}))

    rc, out, err = run_script(
        ["--method", "GET", "--url", f"{base_url}/api/v4/account"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "secret-must-not-leak"},
    )

    assert rc == 1
    assert "secret-must-not-leak" not in err
    assert "secret-must-not-leak" not in out


def test_huge_error_body_is_truncated(mock_server):
    """A multi-MB error body must not flood stderr — should truncate around 4 KB."""
    base_url, server = mock_server
    huge_body = ("X" * 50_000)
    server.response_queue.append((500, huge_body.encode("utf-8"), {}))

    rc, out, err = run_script(
        ["--method", "GET", "--url", f"{base_url}/api/v4/account"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 1
    # stderr is at most a few KB after truncation, never 50_000+
    assert len(err) < 10_000
    assert "truncated" in err
    assert "50000" in err  # original size mentioned
