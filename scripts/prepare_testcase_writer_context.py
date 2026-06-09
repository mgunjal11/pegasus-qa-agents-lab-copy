#!/usr/bin/env python3
"""Load Jira + LADR requirements for msc-testcase-writer drafting."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from confluence_requirements import dedupe_ladr_requirements


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def extract_jira_requirements(jira: dict[str, Any]) -> list[dict[str, str]]:
    reqs: list[dict[str, str]] = []
    for item in jira.get("requirements") or []:
        if isinstance(item, dict) and item.get("id"):
            reqs.append({"id": str(item["id"]), "text": str(item.get("text") or "")})
        elif isinstance(item, str) and item.strip():
            reqs.append({"id": f"R{len(reqs) + 1}", "text": item.strip()})
    return reqs


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Jira + LADR context for testcase writer")
    parser.add_argument("issue_key")
    parser.add_argument("--from-jira-cache", action="store_true")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Run fetch_confluence_requirements.py before reading cache",
    )
    args = parser.parse_args()
    key = args.issue_key.upper()
    root = repo_root()
    cache = root / "reports" / ".cache"

    if args.fetch or args.from_jira_cache:
        cmd = [sys.executable, str(root / "scripts" / "fetch_confluence_requirements.py"), key]
        if args.from_jira_cache:
            cmd.append("--from-jira-cache")
        subprocess.run(cmd, cwd=root, check=False)

    jira = load_json(cache / f"{key}-jira.json")
    conf = load_json(cache / f"{key}-confluence.json")
    jira_reqs = extract_jira_requirements(jira)
    ladr_reqs = dedupe_ladr_requirements(conf.get("ladrRequirements") or [])
    has_ladr = bool(ladr_reqs)

    payload = {
        "issueKey": key,
        "mode": "jira_and_ladr" if has_ladr else "jira_only",
        "hasLadr": has_ladr,
        "summary": jira.get("summary"),
        "jiraRequirements": jira_reqs,
        "ladrRequirements": ladr_reqs,
        "confluence": {
            "status": conf.get("status"),
            "pages": [
                {
                    "title": p.get("title"),
                    "webUrl": p.get("webUrl"),
                    "pageId": p.get("id") or p.get("pageId"),
                }
                for p in (conf.get("pages") or [])
            ],
        },
        "draftGuidance": (
            "Cover every R1…Rn and every L1…Ln; put ESS task+status in Then steps for LADR mapping."
            if has_ladr
            else "Cover every Jira acceptance criterion; no LADR linked."
        ),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
