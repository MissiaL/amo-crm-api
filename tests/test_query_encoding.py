"""Verify amoCRM-style query strings (filter[..], arrays, with=..) encode right."""
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "api_call.py"


def run_script(args, env_overrides):
    env = {**os.environ, **env_overrides}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_bracket_filter_is_passed_through(mock_server):
    base_url, server = mock_server
    server.response_queue.append((200, {"_embedded": {"leads": []}}, {}))

    rc, out, err = run_script(
        [
            "--method", "GET",
            "--url", f"{base_url}/api/v4/leads",
            "--params", json.dumps({
                "filter[query]": "Иванов",
                "filter[statuses][0][pipeline_id]": "123",
                "filter[statuses][0][status_id]": "456",
            }),
        ],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 0, err
    q = parse_qs(server.requests[0]["query"])
    assert q["filter[query]"] == ["Иванов"]
    assert q["filter[statuses][0][pipeline_id]"] == ["123"]
    assert q["filter[statuses][0][status_id]"] == ["456"]


def test_array_value_with_doseq(mock_server):
    base_url, server = mock_server
    server.response_queue.append((200, {"_embedded": {"leads": []}}, {}))

    rc, out, err = run_script(
        [
            "--method", "GET",
            "--url", f"{base_url}/api/v4/leads",
            "--params", json.dumps({"filter[id][]": ["1", "2", "3"]}),
        ],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 0, err
    q = parse_qs(server.requests[0]["query"])
    assert sorted(q["filter[id][]"]) == ["1", "2", "3"]


def test_with_csv_passthrough(mock_server):
    base_url, server = mock_server
    server.response_queue.append((200, {"_embedded": {"leads": []}}, {}))

    rc, out, err = run_script(
        [
            "--method", "GET",
            "--url", f"{base_url}/api/v4/leads",
            "--params", json.dumps({"with": "contacts,companies", "limit": "10"}),
        ],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 0, err
    q = parse_qs(server.requests[0]["query"])
    assert q["with"] == ["contacts,companies"]
    assert q["limit"] == ["10"]


def test_unicode_in_filter_query(mock_server):
    """Cyrillic must round-trip cleanly through URL encoding."""
    base_url, server = mock_server
    server.response_queue.append((200, {"_embedded": {"leads": []}}, {}))

    rc, out, err = run_script(
        [
            "--method", "GET",
            "--url", f"{base_url}/api/v4/leads",
            "--params", json.dumps({"filter[query]": "Тест Иванов"}),
        ],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )

    assert rc == 0, err
    q = parse_qs(server.requests[0]["query"])
    assert q["filter[query]"] == ["Тест Иванов"]
