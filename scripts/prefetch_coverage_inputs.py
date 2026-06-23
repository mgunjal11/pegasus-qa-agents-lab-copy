#!/usr/bin/env python3
"""
Prefetch GitHub PR data for msc-dev-code-and-qa-test-coverage-validator.

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
    """Search open and closed PRs — gh only accepts one --state value per call."""
    urls: list[str] = []
    seen: set[str] = set()
    for state in ("open", "closed"):
        out = gh_text(
            [
                "search",
                "prs",
                issue_key,
                "--repo",
                repo,
                "--state",
                state,
                "--limit",
                str(limit),
                "--json",
                "url",
            ]
        )
        for row in json.loads(out):
            url = row.get("url")
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
            if len(urls) >= limit:
                return urls[:limit]
    return urls


def compare_branches(repo: str, base: str, head: str) -> dict[str, Any]:
    return gh_json(["api", f"repos/{repo}/compare/{base}...{head}", "--jq", "."])


def branch_compare_payload(
    issue_key: str,
    repo: str,
    head: str,
    base: str = "main",
) -> dict[str, Any]:
    cmp = compare_branches(repo, base, head)
    return {
        "issueKey": issue_key,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "repo": repo,
        "prUrls": [],
        "prs": [],
        "branchCompare": {
            "repo": repo,
            "base": base,
            "head": head,
            "ahead_by": cmp.get("ahead_by"),
            "total_commits": cmp.get("total_commits"),
            "files": [f.get("filename") for f in cmp.get("files", []) if f.get("filename")],
            "commits": [
                {
                    "sha": (c.get("sha") or "")[:7],
                    "message": ((c.get("commit") or {}).get("message") or "").split("\n")[0],
                    "author": ((c.get("commit") or {}).get("author") or {}).get("name"),
                }
                for c in (cmp.get("commits") or [])[:20]
            ],
        },
    }


def load_manifest_compare_branch(issue_key: str, cache_dir: Path) -> str | None:
    path = cache_dir / f"{issue_key.upper()}-manifest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    branch = str(data.get("compareBranch") or "").strip()
    return branch or None


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


def fetch_pr_safe(org: str, repo: str, number: int, url: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (pr_payload, error_dict). Never raises — for multi-org partial prefetch."""
    try:
        return fetch_pr(org, repo, number, url), None
    except (RuntimeError, ValueError) as exc:
        err_text = str(exc)
        hint = ""
        low = err_text.lower()
        if "not found" in low or "could not resolve to a repository" in low:
            hint = (
                f"Authorize {org} on GitHub: gh auth refresh -h github.com -s read:org,repo "
                f"then approve SSO at https://github.com/orgs/{org}"
            )
        return None, {
            "url": url,
            "org": org,
            "repo": f"{org}/{repo}",
            "number": number,
            "error": err_text,
            "hint": hint,
        }


def load_jira_pr_urls(issue_key: str, cache_dir: Path | None = None) -> list[str]:
    base = cache_dir or Path("reports/.cache")
    path = base / f"{issue_key.upper()}-jira.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("prUrls") or [])


def write_manifest(
    cache_dir: Path,
    issue_key: str,
    pr_urls: list[str],
    repo: str | None,
    mode: str,
    *,
    compare_branch: str | None = None,
) -> Path:
    path = cache_dir / f"{issue_key.upper()}-manifest.json"
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    manifest = {
        **existing,
        "issueKey": issue_key,
        "prUrls": pr_urls,
        "repo": repo or existing.get("repo"),
        "mode": mode,
        "skipPrSearch": bool(pr_urls),
        "writeReport": existing.get("writeReport", True),
        "useCache": existing.get("useCache", True),
        "cacheMaxAgeHours": existing.get("cacheMaxAgeHours", 24),
    }
    if compare_branch:
        manifest["compareBranch"] = compare_branch
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
        "--compare",
        metavar="BRANCH",
        help="When PR search finds nothing, compare BRANCH to --base (default main)",
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base branch for --compare (default: main)",
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
        "--from-jira-cache",
        action="store_true",
        help="Merge PR URLs from reports/.cache/{KEY}-jira.json with --pr flags",
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
    cache_dir = Path("reports/.cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    for url in load_jira_pr_urls(issue_key, cache_dir):
        if url not in pr_urls:
            pr_urls.append(url)

    if not pr_urls:
        if args.search_pr and args.repo:
            found = search_prs(issue_key, args.repo)
            if found:
                pr_urls = found
                print(f"Found PR(s): {', '.join(pr_urls)}", file=sys.stderr)
            else:
                compare_head = args.compare or load_manifest_compare_branch(issue_key, cache_dir)
                if compare_head and args.repo:
                    print(
                        f"No PRs for {issue_key} in {args.repo}; "
                        f"using branch compare {compare_head} vs {args.base}",
                        file=sys.stderr,
                    )
                    payload = branch_compare_payload(
                        issue_key, args.repo, compare_head, base=args.base
                    )
                    out_path = cache_dir / f"{issue_key}-prefetch.json"
                    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                    print(out_path.resolve())
                    if args.write_manifest:
                        manifest_path = write_manifest(
                            cache_dir,
                            issue_key,
                            [],
                            args.repo,
                            args.mode,
                            compare_branch=compare_head,
                        )
                        print(f"Manifest: {manifest_path.resolve()}", file=sys.stderr)
                    return 0
                print(
                    f"No PRs found for {issue_key} in {args.repo}",
                    file=sys.stderr,
                )
                return 1
        else:
            print(
                "Provide --pr URL or --repo with --search-pr",
                file=sys.stderr,
            )
            return 1

    from cache_freshness import is_prefetch_fresh, load_manifest_max_age

    max_age = args.cache_max_age if args.cache_max_age is not None else load_manifest_max_age(issue_key)

    if args.skip_if_fresh and pr_urls:
        fresh, reason = is_prefetch_fresh(issue_key, pr_urls, max_age_hours=max_age)
        if fresh:
            out_path = cache_dir / f"{issue_key}-prefetch.json"
            print(out_path.resolve())
            print(f"Skipped prefetch ({reason})", file=sys.stderr)
            return 0

    prs: list[dict[str, Any]] = []
    prefetch_errors: list[dict[str, Any]] = []
    inferred_repo = args.repo
    requested_urls = list(pr_urls)
    for url in pr_urls:
        org, repo_name, number = parse_pr_url(url)
        if not inferred_repo:
            inferred_repo = f"{org}/{repo_name}"
        pr_data, err = fetch_pr_safe(org, repo_name, number, url)
        if pr_data:
            prs.append(pr_data)
        elif err:
            prefetch_errors.append(err)

    if not prs:
        detail = "; ".join(e.get("error", "")[:120] for e in prefetch_errors[:3])
        print(f"No PRs prefetched for {issue_key}. {detail}", file=sys.stderr)
        return 1

    if prefetch_errors:
        for err in prefetch_errors:
            msg = f"Skipped {err.get('url')}: {err.get('error', '')[:200]}"
            if err.get("hint"):
                msg += f" — {err['hint']}"
            print(msg, file=sys.stderr)

    payload = {
        "issueKey": issue_key,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "repo": inferred_repo,
        "requestedPrUrls": requested_urls,
        "prUrls": [p.get("url") for p in prs if p.get("url")],
        "prs": prs,
        "prefetchErrors": prefetch_errors,
    }

    out_path = cache_dir / f"{issue_key}-prefetch.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(out_path.resolve())

    if args.write_manifest:
        manifest_path = write_manifest(
            cache_dir, issue_key, requested_urls, inferred_repo, args.mode
        )
        print(f"Manifest: {manifest_path.resolve()}", file=sys.stderr)

    ok_n = len(prs)
    req_n = len(requested_urls)
    if prefetch_errors:
        print(
            f"Prefetched {ok_n}/{req_n} PR(s) ({len(prefetch_errors)} inaccessible — see prefetchErrors in cache). "
            f"Run: @msc-dev-code-and-qa-test-coverage-validator {issue_key} --from-cache --auto",
            file=sys.stderr,
        )
    else:
        print(
            f"Prefetched {ok_n} PR(s). Run: @msc-dev-code-and-qa-test-coverage-validator {issue_key} --from-cache --auto",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
