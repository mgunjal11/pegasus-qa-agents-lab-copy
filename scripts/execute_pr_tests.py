#!/usr/bin/env python3
"""
Optional local pytest execution for PR test files in prefetch cache.

Requires a local clone of the service repo — set testRepoRoot in
.coverage-validator.defaults.json or COVERAGE_TEST_REPO_ROOT env var.

  python scripts/execute_pr_tests.py MSC-205625
  python scripts/build_coverage_report.py MSC-205625 --execute-tests
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent


def repo_root() -> Path:
    return ROOT


def execution_cache_path(issue_key: str) -> Path:
    return repo_root() / "reports" / ".cache" / f"{issue_key.upper()}-test-execution.json"


def load_defaults(root: Path | None = None) -> dict[str, Any]:
    base = root or repo_root()
    path = base / ".coverage-validator.defaults.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_test_repo_root(issue_key: str, root: Path | None = None) -> Path | None:
    base = root or repo_root()
    env = os.environ.get("COVERAGE_TEST_REPO_ROOT", "").strip()
    if env:
        p = Path(env)
        return p if p.is_dir() else None
    defaults = load_defaults(base)
    raw = str(defaults.get("testRepoRoot") or defaults.get("testRepoPath") or "").strip()
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = base / raw
        return p if p.is_dir() else None
    manifest_path = base / "reports" / ".cache" / f"{issue_key.upper()}-manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            raw = str(manifest.get("testRepoRoot") or "").strip()
            if raw:
                p = Path(raw)
                if not p.is_absolute():
                    p = base / raw
                return p if p.is_dir() else None
        except (OSError, json.JSONDecodeError):
            pass
    return None


def collect_pr_test_paths(prefetch: dict[str, Any]) -> list[str]:
    from coverage_report_helpers import is_dev_test_module_path

    paths: list[str] = []
    seen: set[str] = set()
    for pr in prefetch.get("prs") or []:
        for name in pr.get("diffNames") or []:
            if is_dev_test_module_path(name) and name not in seen:
                seen.add(name)
                paths.append(name)
    bc = prefetch.get("branchCompare") or {}
    for name in bc.get("files") or []:
        if is_dev_test_module_path(name) and name not in seen:
            seen.add(name)
            paths.append(name)
    return paths


def run_local_pytest(
    issue_key: str,
    *,
    root: Path | None = None,
    max_files: int = 12,
) -> dict[str, Any]:
    base = root or repo_root()
    key = issue_key.upper()
    prefetch_path = base / "reports" / ".cache" / f"{key}-prefetch.json"
    if not prefetch_path.exists():
        return {
            "issueKey": key,
            "status": "skipped",
            "reason": "prefetch cache missing",
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        }

    prefetch = json.loads(prefetch_path.read_text(encoding="utf-8"))
    repo = resolve_test_repo_root(key, base)
    if not repo:
        return {
            "issueKey": key,
            "status": "skipped",
            "reason": "set testRepoRoot in .coverage-validator.defaults.json or COVERAGE_TEST_REPO_ROOT",
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        }

    rel_paths = collect_pr_test_paths(prefetch)[:max_files]
    existing = [repo / p for p in rel_paths if (repo / p).is_file()]
    if not existing:
        return {
            "issueKey": key,
            "status": "skipped",
            "reason": f"no PR test files found under {repo}",
            "requestedPaths": rel_paths,
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        }

    cmd = [sys.executable, "-m", "pytest", *[str(p) for p in existing], "-q", "--tb=no"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "issueKey": key,
            "status": "error",
            "reason": "pytest timed out after 600s",
            "repoRoot": str(repo),
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        }

    out = (proc.stdout or "") + (proc.stderr or "")
    passed = failed = 0
    for line in out.splitlines():
        m = __import__("re").search(r"(\d+) passed", line)
        if m:
            passed = int(m.group(1))
        m = __import__("re").search(r"(\d+) failed", line)
        if m:
            failed = int(m.group(1))

    return {
        "issueKey": key,
        "status": "ok" if proc.returncode == 0 else "fail",
        "returnCode": proc.returncode,
        "passed": passed,
        "failed": failed,
        "repoRoot": str(repo),
        "testFiles": [str(p.relative_to(repo)).replace("\\", "/") for p in existing],
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
    }


def write_execution_cache(payload: dict[str, Any], issue_key: str) -> Path:
    out = execution_cache_path(issue_key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local pytest on PR test files from prefetch cache")
    parser.add_argument("issue_key")
    args = parser.parse_args()
    payload = run_local_pytest(args.issue_key.upper())
    out = write_execution_cache(payload, args.issue_key)
    print(json.dumps({"output": str(out.resolve()), "status": payload.get("status")}))
    return 0 if payload.get("status") in ("ok", "skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
