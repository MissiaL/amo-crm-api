"""Tests for URL building in api_call.py — env loading, prefix, abs URL passthrough."""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "api_call.py"


def run_script(args, env_overrides=None):
    """Run api_call.py as subprocess, return (returncode, stdout, stderr)."""
    env = {**os.environ, **(env_overrides or {})}
    # Strip the env we want to test the absence of
    for key in ("AMOCRM_SUBDOMAIN", "AMOCRM_TOKEN"):
        if env_overrides and key in env_overrides and env_overrides[key] is None:
            env.pop(key, None)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env={k: v for k, v in env.items() if v is not None},
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_missing_subdomain_exits_with_error():
    rc, out, err = run_script(
        ["--method", "GET", "--url", "/api/v4/account", "--dry-run"],
        env_overrides={"AMOCRM_SUBDOMAIN": None, "AMOCRM_TOKEN": "tok"},
    )
    assert rc == 1
    assert "AMOCRM_SUBDOMAIN" in err


def test_missing_token_exits_with_error():
    rc, out, err = run_script(
        ["--method", "GET", "--url", "/api/v4/account", "--dry-run"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": None},
    )
    assert rc == 1
    assert "AMOCRM_TOKEN" in err


def test_relative_url_gets_subdomain_prefix():
    rc, out, err = run_script(
        ["--method", "GET", "--url", "/api/v4/account", "--dry-run"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )
    assert rc == 0, err
    assert "https://demo.amocrm.ru/api/v4/account" in out


def test_absolute_url_stays_as_is():
    rc, out, err = run_script(
        ["--method", "GET", "--url", "https://other.example.com/foo", "--dry-run"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "tok"},
    )
    assert rc == 0, err
    assert "https://other.example.com/foo" in out
    assert "amocrm.ru" not in out


def test_token_never_appears_in_dry_run_output():
    rc, out, err = run_script(
        ["--method", "GET", "--url", "/api/v4/account", "--dry-run"],
        env_overrides={"AMOCRM_SUBDOMAIN": "demo", "AMOCRM_TOKEN": "secret123"},
    )
    assert rc == 0, err
    assert "secret123" not in out
    assert "secret123" not in err
