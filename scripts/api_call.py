#!/usr/bin/env python3
"""Thin HTTP client for amoCRM REST API v4.

Reads AMOCRM_SUBDOMAIN and AMOCRM_TOKEN from env. Signs every request with
Bearer auth. Designed to be called by an agent — JSON in, JSON out, exit code
0 on success, 1 on any error.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def build_url(url_arg: str, subdomain: str) -> str:
    if url_arg.startswith(("http://", "https://")):
        return url_arg
    if not url_arg.startswith("/"):
        url_arg = "/" + url_arg
    return f"https://{subdomain}.amocrm.ru{url_arg}"


def main() -> int:
    parser = argparse.ArgumentParser(description="amoCRM HTTP client")
    parser.add_argument("--method", required=True, choices=["GET", "POST", "PATCH", "DELETE"])
    parser.add_argument("--url", required=True, help="Path like /api/v4/leads, or full https URL")
    parser.add_argument("--params", default=None, help="JSON object for query params")
    parser.add_argument("--body", default=None, help="JSON for request body")
    parser.add_argument("--headers", default=None, help="JSON object for extra headers")
    parser.add_argument("--dry-run", action="store_true", help="Print full URL and exit (for tests)")
    args = parser.parse_args()

    subdomain = os.environ.get("AMOCRM_SUBDOMAIN")
    token = os.environ.get("AMOCRM_TOKEN")
    if not subdomain:
        print("error: AMOCRM_SUBDOMAIN env var is not set", file=sys.stderr)
        return 1
    if not token:
        print("error: AMOCRM_TOKEN env var is not set", file=sys.stderr)
        return 1

    url = build_url(args.url, subdomain)

    if args.dry_run:
        print(url)
        return 0

    # Build query string with doseq=True so arrays/filter[..]= keys serialize right
    query = ""
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"error: --params is not valid JSON: {e}", file=sys.stderr)
            return 1
        query = urllib.parse.urlencode(params, doseq=True)
    full_url = url + ("?" + query if query else "")

    headers = {"Authorization": f"Bearer {token}"}
    body_bytes = None
    if args.body is not None:
        # Body is JSON text — send it through as-is, but verify it parses
        try:
            json.loads(args.body)
        except json.JSONDecodeError as e:
            print(f"error: --body is not valid JSON: {e}", file=sys.stderr)
            return 1
        body_bytes = args.body.encode("utf-8")
        headers["Content-Type"] = "application/json"
    if args.headers:
        try:
            extra = json.loads(args.headers)
        except json.JSONDecodeError as e:
            print(f"error: --headers is not valid JSON: {e}", file=sys.stderr)
            return 1
        headers.update(extra)

    req = urllib.request.Request(full_url, data=body_bytes, headers=headers, method=args.method)
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            if data:
                sys.stdout.write(data.decode("utf-8"))
                sys.stdout.write("\n")
            return 0
    except urllib.error.HTTPError as e:
        # Error classification — implemented in Task 4
        body = e.read().decode("utf-8", errors="replace")
        print(f"error: HTTP {e.code}", file=sys.stderr)
        if body:
            print(body, file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"error: network failure: {e.reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
