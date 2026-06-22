#!/usr/bin/env python3
"""Upload a test plan Excel/TSV to a Jira issue (Option C setup)."""

from __future__ import annotations

import argparse
import json
import sys

from jira_env import credentials_hint, load_dotenv, upload_attachment


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload test plan file to Jira issue")
    parser.add_argument("issue_key", help="Jira issue key, e.g. MSC-205625")
    parser.add_argument("--file", required=True, help="Local test plan .xlsx or .tsv")
    parser.add_argument("--site", default="wbdstreaming.atlassian.net")
    args = parser.parse_args()

    load_dotenv()
    try:
        attachments = upload_attachment(args.issue_key.upper(), args.file, args.site)
    except (RuntimeError, FileNotFoundError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "hint": credentials_hint()}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "issueKey": args.issue_key.upper(),
                "uploaded": [{"id": a.get("id"), "filename": a.get("filename"), "size": a.get("size")} for a in attachments],
                "next": f"python scripts/fetch_jira_testplan.py {args.issue_key.upper()} --sheet \"Inc as full\"",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
