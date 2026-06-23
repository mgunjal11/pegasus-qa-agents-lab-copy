#!/usr/bin/env python3
"""
Prefetch GitHub PR data for Req2Release.

Run once in terminal to avoid repeated gh tool approvals during agent analysis:

  python scripts/prefetch_coverage_inputs.py MSC-209376 \\
    --pr https://github.com/wbd-msc/my-repo/pull/42

  python scripts/prefetch_coverage_inputs.py MSC-209376 \\
    --repo wbd-msc/my-repo --search-pr

Writes: reports/.cache/{ISSUE-KEY}-prefetch.json
Optional manifest: reports/.cache/{ISSUE-KEY}-manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ci_coverage import (  # noqa: E402
    extract_ci_coverage,
    fetch_check_run_sonar_summary,
    fetch_sonarqube_comment,
)

PR_URL_RE = re.compile(
    r"https://github\.com/(?P<org>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
)


_GH_SUBPROCESS = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace"}


def gh_json(args: list[str]) -> Any:
    result = subprocess.run(
        ["gh", *args],
        check=False,
        **_GH_SUBPROCESS,
    )
    if result.returncode != 0:
        err = result.stderr.strip() or f"gh failed: {' '.join(args)}"
        if "auth" in err.lower() or "not logged" in err.lower():
            err += (
                "\nRun: python scripts/preflight_coverage_validator.py  "
                "and gh auth login (https://cli.github.com)"
            )
        raise RuntimeError(err)
    return json.loads(result.stdout)


def gh_text(args: list[str], *, accept_stdout_on_error: bool = False) -> str:
    result = subprocess.run(
        ["gh", *args],
        check=False,
        **_GH_SUBPROCESS,
    )
    if result.returncode != 0:
        # gh pr checks exits non-zero when any check is pending/failing but still prints rows.
        if accept_stdout_on_error and result.stdout.strip():
            return result.stdout
        raise RuntimeError(result.stderr.strip() or f"gh failed: {' '.join(args)}")
    return result.stdout


def parse_pr_url(url: str) -> tuple[str, str, int]:
    match = PR_URL_RE.match(url.strip())
    if not match:
        raise ValueError(f"Invalid GitHub PR URL: {url}")
    org = match.group("org")
    repo = match.group("repo")
    number = int(match.group("number"))
    return org, repo, number


def search_prs(issue_key: str, repo: str, limit: int = 10) -> list[str]:
    out = gh_text(
        [
            "search",
            "prs",
            issue_key,
            "--repo",
            repo,
            "--state",
            "open,closed",
            "--limit",
            str(limit),
            "--json",
            "url",
        ]
    )
    rows = json.loads(out)
    return [row["url"] for row in rows if row.get("url")]


def fetch_codecov_comment(org: str, repo: str, number: int) -> str | None:
    try:
        comments = gh_json(
            [
                "api",
                f"repos/{org}/{repo}/issues/{number}/comments",
                "--jq",
                '.[] | select(.user.login | test("codecov"; "i")) | .body',
            ]
        )
    except (RuntimeError, json.JSONDecodeError):
        return None
    if isinstance(comments, list) and comments:
        return comments[0]
    if isinstance(comments, str) and comments.strip():
        return comments
    return None


def fetch_pr(org: str, repo: str, number: int, url: str) -> dict[str, Any]:
    full_repo = f"{org}/{repo}"
    view = gh_json(
        [
            "pr",
            "view",
            str(number),
            "--repo",
            full_repo,
            "--json",
            "title,state,author,body,headRefName,baseRefName,files,commits,headRefOid,url",
        ]
    )
    diff = gh_text(["pr", "diff", str(number), "--repo", full_repo])
    diff_names = gh_text(
        ["pr", "diff", str(number), "--repo", full_repo, "--name-only"]
    ).strip()
    checks = gh_text(
        ["pr", "checks", str(number), "--repo", full_repo],
        accept_stdout_on_error=True,
    )
    codecov = fetch_codecov_comment(org, repo, number)
    sonar = fetch_sonarqube_comment(org, repo, number)
    head_sha = (view.get("headRefOid") or "") if isinstance(view, dict) else ""
    sonar_check = None
    if head_sha:
        sonar_check = fetch_check_run_sonar_summary(org, repo, head_sha)
    ci_coverage = extract_ci_coverage(
        codecov_comment=codecov,
        sonar_comment=sonar,
        sonar_check_summary=sonar_check,
        checks_text=checks,
        repo=full_repo,
    )
    return {
        "url": url,
        "org": org,
        "repo": repo,
        "number": number,
        "view": view,
        "diff": diff,
        "diffNames": diff_names.splitlines() if diff_names else [],
        "checks": checks,
        "codecovComment": codecov,
        "sonarComment": sonar,
        "ciCoverage": ci_coverage,
    }


def write_manifest(
    cache_dir: Path,
    issue_key: str,
    pr_urls: list[str],
    repo: str | None,
    mode: str,
) -> Path:
    manifest = {
        "issueKey": issue_key,
        "prUrls": pr_urls,
        "repo": repo,
        "mode": mode,
        "skipPrSearch": bool(pr_urls),
        "writeReport": True,
        "useCache": True,
        "cacheMaxAgeHours": 24,
    }
    path = cache_dir / f"{issue_key}-manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prefetch GitHub PR data for coverage validation"
    )
    parser.add_argument("issue_key", help="Jira issue key, e.g. MSC-209376")
    parser.add_argument(
        "--pr",
        action="append",
        dest="pr_urls",
        default=[],
        help="GitHub PR URL (repeatable)",
    )
    parser.add_argument(
        "--repo",
        help="org/repo for PR search when --pr not given",
    )
    parser.add_argument(
        "--search-pr",
        action="store_true",
        help="Search PRs by issue key when --pr not given (requires --repo)",
    )
    parser.add_argument(
        "--mode",
        default="from-cache",
        choices=("auto", "from-cache", "fetch-only", "interactive"),
        help="Suggested agent mode for next run (written to manifest)",
    )
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        default=True,
        help="Write reports/.cache/{KEY}-manifest.json (default: on)",
    )
    parser.add_argument(
        "--no-write-manifest",
        action="store_false",
        dest="write_manifest",
        help="Skip manifest file",
    )
    parser.add_argument(
        "--skip-if-fresh",
        action="store_true",
        help="Skip gh fetch when prefetch cache matches --pr URLs and is within cacheMaxAgeHours",
    )
    parser.add_argument(
        "--cache-max-age",
        type=int,
        default=None,
        help="Max prefetch age in hours (default: manifest or 24)",
    )
    args = parser.parse_args()

    issue_key = args.issue_key.strip().upper()
    pr_urls = list(args.pr_urls or [])

    if not pr_urls:
        if args.search_pr and args.repo:
            found = search_prs(issue_key, args.repo)
            if not found:
                print(
                    f"No PRs found for {issue_key} in {args.repo}",
                    file=sys.stderr,
                )
                return 1
            pr_urls = found
            print(f"Found PR(s): {', '.join(pr_urls)}", file=sys.stderr)
        else:
            print(
                "Provide --pr URL or --repo with --search-pr",
                file=sys.stderr,
            )
            return 1

    from cache_freshness import is_prefetch_fresh, load_manifest_max_age

    cache_dir = Path("reports/.cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    max_age = args.cache_max_age if args.cache_max_age is not None else load_manifest_max_age(issue_key)

    if args.skip_if_fresh and pr_urls:
        fresh, reason = is_prefetch_fresh(issue_key, pr_urls, max_age_hours=max_age)
        if fresh:
            out_path = cache_dir / f"{issue_key}-prefetch.json"
            print(out_path.resolve())
            print(f"Skipped prefetch ({reason})", file=sys.stderr)
            return 0

    prs: list[dict[str, Any]] = []
    inferred_repo = args.repo
    for url in pr_urls:
        org, repo_name, number = parse_pr_url(url)
        if not inferred_repo:
            inferred_repo = f"{org}/{repo_name}"
        prs.append(fetch_pr(org, repo_name, number, url))

    payload = {
        "issueKey": issue_key,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "repo": inferred_repo,
        "prUrls": pr_urls,
        "prs": prs,
    }

    out_path = cache_dir / f"{issue_key}-prefetch.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(out_path.resolve())

    if args.write_manifest:
        manifest_path = write_manifest(
            cache_dir, issue_key, pr_urls, inferred_repo, args.mode
        )
        print(f"Manifest: {manifest_path.resolve()}", file=sys.stderr)

    print(
        f"Prefetched {len(prs)} PR(s). Run: @Req2Release {issue_key} --from-cache --auto",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
