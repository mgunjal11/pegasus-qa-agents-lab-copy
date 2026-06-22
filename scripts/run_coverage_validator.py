#!/usr/bin/env python3
"""
Orchestrate coverage-validator shell pipeline with automatic preflight.

Runs preflight first, then confluence → test plan → prefetch → map → semantic boost → build.
Jira MCP fetch remains an agent step; this script requires a warm jira cache unless --skip-jira-check.

  python scripts/run_coverage_validator.py MSC-205625 --auto --write
  python scripts/run_coverage_validator.py MSC-205625 --preflight-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from coverage_validator_config import load_coverage_defaults  # noqa: E402
from preflight_coverage_validator import run_preflight  # noqa: E402


def _cache_dir(key: str) -> Path:
    return ROOT / "reports" / ".cache"


def _jira_cache_exists(key: str) -> bool:
    return (_cache_dir(key) / f"{key.upper()}-jira.json").exists()


def _run(cmd: list[str], *, label: str) -> dict[str, Any]:
    print(f"\n>> {label}: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, encoding="utf-8")
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        hint = ""
        low = err.lower()
        if "gh failed" in low or "auth" in low:
            hint = "\nHint: run `python scripts/preflight_coverage_validator.py` and `gh auth login`."
        elif "jira" in low or "401" in low or "403" in low:
            hint = (
                "\nHint: check `.env` ATLASSIAN_EMAIL / ATLASSIAN_API_TOKEN — "
                "`python scripts/preflight_coverage_validator.py {key} --verify-jira`."
            )
        raise RuntimeError(f"{label} failed (exit {result.returncode}): {err}{hint}")
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"stdout": result.stdout.strip()}


def _prefetch_args(key: str, args: argparse.Namespace, defaults: dict[str, Any]) -> list[str]:
    cmd = [sys.executable, str(SCRIPTS / "prefetch_coverage_inputs.py"), key]
    pr = args.pr or defaults.get("prUrl") or defaults.get("pr")
    repo = args.repo or defaults.get("repo")
    if pr:
        cmd.extend(["--pr", str(pr)])
    elif repo:
        cmd.extend(["--repo", str(repo)])
        if defaults.get("searchPrIfMissing", True) and not args.no_search_pr:
            cmd.append("--search-pr")
    if args.skip_if_fresh:
        cmd.append("--skip-if-fresh")
    return cmd


def run_pipeline(key: str, args: argparse.Namespace) -> dict[str, Any]:
    key = key.upper()
    defaults = load_coverage_defaults(ROOT)
    semantic = args.semantic_boost
    if semantic is None:
        semantic = bool(defaults.get("semanticMappingBoost", True))

    preflight = run_preflight(key, verify_jira=args.verify_jira)
    if not preflight["ok"]:
        fail_ids = ", ".join(preflight.get("requiredFailures") or [])
        raise RuntimeError(
            f"Preflight failed ({fail_ids}). "
            f"Fix setup then re-run: python scripts/preflight_coverage_validator.py {key} --verify-jira"
        )
    if args.preflight_only:
        return {"preflight": preflight, "skipped": True}

    if not args.skip_jira_check and not _jira_cache_exists(key):
        raise RuntimeError(
            f"Missing reports/.cache/{key}-jira.json — fetch Jira via Atlassian MCP first, "
            f"then re-run run_coverage_validator.py {key}"
        )

    steps: list[dict[str, Any]] = [{"preflight": preflight}]

    if not args.skip_testplan:
        steps.append(
            _run(
                [sys.executable, str(SCRIPTS / "fetch_confluence_requirements.py"), key, "--from-jira-cache"],
                label="confluence",
            )
        )
        steps.append(
            _run(
                [sys.executable, str(SCRIPTS / "fetch_jira_testplan.py"), key, "--from-jira-cache"],
                label="testplan",
            )
        )

    steps.append(_run(_prefetch_args(key, args, defaults), label="prefetch"))

    map_cmd = [sys.executable, str(SCRIPTS / "map_requirements_to_diff.py"), key]
    if args.skip_if_fresh:
        map_cmd.append("--skip-if-fresh")
    if semantic:
        map_cmd.append("--semantic-boost")
    steps.append(_run(map_cmd, label="map"))

    build_cmd = [sys.executable, str(SCRIPTS / "build_coverage_report.py"), key]
    build_result = _run(build_cmd, label="build")
    steps.append(build_result)

    report_path = build_result.get("report") or build_result.get("output")
    if not report_path and build_result.get("stdout"):
        first = build_result["stdout"].strip().splitlines()[0]
        if first.endswith(".html"):
            report_path = first

    return {"issueKey": key, "steps": len(steps), "report": report_path, "preflight": preflight}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run coverage validator pipeline with auto-preflight")
    parser.add_argument("issue_key")
    parser.add_argument("--auto", action="store_true", help="Non-interactive (default)")
    parser.add_argument("--write", action="store_true", help="Write HTML report")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--skip-jira-check", action="store_true")
    parser.add_argument("--skip-testplan", action="store_true")
    parser.add_argument("--skip-if-fresh", action="store_true", default=True)
    parser.add_argument("--no-search-pr", action="store_true")
    parser.add_argument("--pr", help="GitHub PR URL")
    parser.add_argument("--repo", help="org/repo for PR search")
    parser.add_argument(
        "--semantic-boost",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Second-pass semantic mapping (default: from defaults or on)",
    )
    parser.add_argument(
        "--verify-jira",
        action="store_true",
        help="Smoke-test Jira REST during preflight",
    )
    args = parser.parse_args()

    try:
        result = run_pipeline(args.issue_key, args)
        print(json.dumps(result, indent=2))
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
