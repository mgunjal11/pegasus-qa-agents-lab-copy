#!/usr/bin/env python3
"""
Fetch Jira story and write reports/.cache/{KEY}-jira.json for the coverage validator.

Uses Jira REST (.env credentials). Optional MCP JSON import for offline/MCP-first workflows.

  python scripts/fetch_jira_story.py MSC-205625
  python scripts/fetch_jira_story.py MSC-205625 --skip-if-fresh
  python scripts/fetch_jira_story.py MSC-205625 --from-mcp-json path/to/mcp-issue.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from cache_freshness import cache_timestamp, load_manifest_max_age  # noqa: E402
from jira_story import build_jira_cache, jira_cache_path  # noqa: E402


def is_jira_cache_fresh(
    issue_key: str,
    root: Path | None = None,
    *,
    max_age_hours: int = 24,
) -> tuple[bool, str]:
    path = jira_cache_path(issue_key, root)
    if not path.exists():
        return False, "jira cache missing"
    fetched = cache_timestamp(path)
    if not fetched:
        return False, "jira cache unreadable"
    from datetime import datetime, timezone

    age_h = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
    if age_h > max_age_hours:
        return False, f"jira cache older than {max_age_hours}h"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "jira cache unreadable"
    if not data.get("requirements"):
        return False, "jira cache missing requirements"
    return True, "jira cache fresh"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Jira story into coverage-validator cache")
    parser.add_argument("issue_key")
    parser.add_argument("--site", default="wbdstreaming.atlassian.net")
    parser.add_argument(
        "--from-mcp-json",
        help="Normalize Atlassian MCP getJiraIssue JSON instead of REST fetch",
    )
    parser.add_argument(
        "--skip-if-fresh",
        action="store_true",
        help="Skip when jira cache is within cacheMaxAgeHours and has requirements",
    )
    parser.add_argument(
        "--cache-max-age",
        type=int,
        default=None,
        help="Max jira cache age in hours (default: manifest cacheMaxAgeHours or 24)",
    )
    parser.add_argument(
        "--no-merge-prior",
        action="store_true",
        help="Do not preserve prior requirements when new extraction is thinner",
    )
    args = parser.parse_args()
    key = args.issue_key.upper()
    max_age = args.cache_max_age if args.cache_max_age is not None else load_manifest_max_age(key)

    if args.skip_if_fresh and not args.from_mcp_json:
        fresh, reason = is_jira_cache_fresh(key, ROOT, max_age_hours=max_age)
        if fresh:
            out = jira_cache_path(key, ROOT)
            print(json.dumps({"output": str(out.resolve()), "skipped": True, "reason": reason}))
            return 0

    mcp_path = Path(args.from_mcp_json) if args.from_mcp_json else None
    payload = build_jira_cache(
        key,
        root=ROOT,
        site=args.site,
        mcp_json=mcp_path,
        merge_prior=not args.no_merge_prior,
    )
    out = jira_cache_path(key, ROOT)
    print(
        json.dumps(
            {
                "output": str(out.resolve()),
                "requirementCount": len(payload.get("requirements") or []),
                "prUrls": payload.get("prUrls") or [],
                "attachmentCount": len(payload.get("attachments") or []),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
