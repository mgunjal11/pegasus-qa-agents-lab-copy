#!/usr/bin/env python3
"""Verify Jira API credentials for test plan attachment download (Option C)."""

from __future__ import annotations

import argparse
import json
import sys

from jira_env import credentials_hint, load_dotenv, verify_credentials


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Jira REST credentials")
    parser.add_argument("issue_key", nargs="?", default="MSC-205625")
    parser.add_argument("--site", default="wbdstreaming.atlassian.net")
    args = parser.parse_args()

    if not load_dotenv():
        print(f"Note: no .env file found. {credentials_hint()}", file=sys.stderr)

    try:
        result = verify_credentials(args.issue_key.upper(), args.site)
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    expiry = result.get("tokenExpiry")
    if expiry and expiry.get("message") and not expiry.get("expired"):
        print(f"Note: {expiry['message']}", file=sys.stderr)

    print(json.dumps(result, indent=2))
    if result.get("tokenExpiry", {}).get("expired"):
        print(f"\n{result['tokenExpiry']['message']}", file=sys.stderr)
        return 1
    if result["attachmentCount"] == 0:
        print(
            f"\nAuth OK, but {result['issueKey']} has no attachments yet.\n"
            "Attach the test plan Excel on the Jira issue, or run:\n"
            f"  python scripts/upload_jira_testplan.py {result['issueKey']} --file path/to/testplan.xlsx",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
