#!/usr/bin/env python3
"""
Fetch Confluence LADR pages linked from a Jira issue and extract ESS requirements.

Uses the same ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN as Jira attachment download.
Agent may also use Atlassian MCP getConfluencePage and write this cache manually.

  python scripts/fetch_confluence_requirements.py MSC-204417
  python scripts/fetch_confluence_requirements.py MSC-204417 --from-jira-cache
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from confluence_requirements import (  # noqa: E402
    confluence_cache_path,
    fetch_and_cache_confluence_for_issue,
    repo_root,
)
from jira_env import load_dotenv  # noqa: E402


def jira_cache_path(issue_key: str) -> Path:
    return repo_root() / "reports" / ".cache" / f"{issue_key.upper()}-jira.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Confluence LADR requirements for coverage validator")
    parser.add_argument("issue_key", help="Jira issue key, e.g. MSC-204417")
    parser.add_argument("--from-jira-cache", action="store_true", help="Read reports/.cache/{KEY}-jira.json")
    parser.add_argument("--site", default="wbdstreaming.atlassian.net")
    args = parser.parse_args()

    load_dotenv()
    issue_key = args.issue_key.upper()
    jira_data: dict | None = None
    if args.from_jira_cache:
        path = jira_cache_path(issue_key)
        if path.exists():
            jira_data = json.loads(path.read_text(encoding="utf-8"))

    payload = fetch_and_cache_confluence_for_issue(issue_key, jira_data, site=args.site)
    print(
        json.dumps(
            {
                "output": str(confluence_cache_path(issue_key).resolve()),
                "status": payload.get("status"),
                "pages": len(payload.get("pages") or []),
                "ladrRequirements": len(payload.get("ladrRequirements") or []),
            }
        )
    )
    # status "ok" covers linked pages with no LADR/ESS (e.g. deployment notes) — still a valid cache
    status = payload.get("status")
    return 0 if payload.get("ladrRequirements") or status in ("ok", "no_links") else 1


if __name__ == "__main__":
    raise SystemExit(main())
