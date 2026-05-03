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

    # Real request — implemented in Task 3
    print("error: real requests not implemented yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
