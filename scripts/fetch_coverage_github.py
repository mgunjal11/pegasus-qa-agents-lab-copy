#!/usr/bin/env python3
"""
Single-shot GitHub fetch for msc-code-coverage-validator.

Use ONE agent Shell call instead of many gh approvals:

  python scripts/fetch_coverage_github.py MSC-204417 --repo wbd-msc/pegasus-ess --search-pr
  python scripts/fetch_coverage_github.py MSC-204417 --pr https://github.com/org/repo/pull/1
  python scripts/fetch_coverage_github.py MSC-204417 --repo wbd-msc/pegasus-ess --compare develop

Delegates to prefetch_coverage_inputs.py when PR URLs are known; adds branch compare for direct-commit stories.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def gh_json(args: list[str]):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "gh failed")
    return json.loads(r.stdout)


def compare_branches(repo: str, base: str, head: str) -> dict:
    return gh_json(
        ["api", f"repos/{repo}/compare/{base}...{head}", "--jq", "."]
    )


def main() -> int:
    p = argparse.ArgumentParser(description="One-shot GitHub fetch for coverage validator")
    p.add_argument("issue_key")
    p.add_argument("--pr", action="append", dest="pr_urls", default=[])
    p.add_argument("--repo")
    p.add_argument("--search-pr", action="store_true")
    p.add_argument("--compare", metavar="BRANCH", help="Compare branch to main (e.g. develop)")
    p.add_argument("--base", default="main")
    args = p.parse_args()

    issue_key = args.issue_key.strip().upper()
    cache_dir = Path("reports/.cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    prefetch_cmd = [
        sys.executable,
        str(SCRIPTS / "prefetch_coverage_inputs.py"),
        issue_key,
        "--mode",
        "from-cache",
    ]
    if args.pr_urls:
        for url in args.pr_urls:
            prefetch_cmd.extend(["--pr", url])
    elif args.search_pr and args.repo:
        prefetch_cmd.extend(["--repo", args.repo, "--search-pr"])
    elif args.pr_urls or (args.search_pr and args.repo):
        pass
    else:
        if not args.compare and not args.repo:
            print("Need --pr, --search-pr with --repo, or --compare", file=sys.stderr)
            return 1

    out_path = cache_dir / f"{issue_key}-prefetch.json"
    payload: dict = {}

    if args.pr_urls or (args.search_pr and args.repo):
        r = subprocess.run(prefetch_cmd, capture_output=True, text=True, check=False)
        if r.returncode != 0:
            print(r.stderr or r.stdout, file=sys.stderr)
            return r.returncode
        print(r.stdout.strip())
        if out_path.exists():
            payload = json.loads(out_path.read_text(encoding="utf-8"))

    if args.compare and args.repo:
        cmp = compare_branches(args.repo, args.base, args.compare)
        branch_data = {
            "repo": args.repo,
            "base": args.base,
            "head": args.compare,
            "ahead_by": cmp.get("ahead_by"),
            "total_commits": cmp.get("total_commits"),
            "files": [f.get("filename") for f in cmp.get("files", [])],
            "commits": [
                {
                    "sha": c.get("sha", "")[:7],
                    "message": (c.get("commit") or {}).get("message", "").split("\n")[0],
                    "author": ((c.get("commit") or {}).get("author") or {}).get("name"),
                }
                for c in cmp.get("commits", [])[:20]
            ],
        }
        if payload:
            payload["branchCompare"] = branch_data
        else:
            payload = {
                "issueKey": issue_key,
                "fetchedAt": datetime.now(timezone.utc).isoformat(),
                "repo": args.repo,
                "prUrls": [],
                "prs": [],
                "branchCompare": branch_data,
            }
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(out_path.resolve())

    return 0


if __name__ == "__main__":
    sys.exit(main())
