#!/usr/bin/env python3
"""
Orchestrate coverage-validator shell pipeline with automatic preflight.

Runs preflight first, then confluence → test plan → prefetch → map → semantic boost → build.
Jira MCP fetch remains optional (--from-mcp-json); default uses fetch_jira_story.py (REST).

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


def _parse_subprocess_json(stdout: str) -> dict[str, Any]:
    """Parse JSON from subprocess stdout (single-line, pretty-printed, or trailing line)."""
    text = stdout.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return {"stdout": text}


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
    return _parse_subprocess_json(result.stdout)


def _load_manifest(key: str) -> dict[str, Any]:
    path = _cache_dir(key) / f"{key.upper()}-manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _load_jira_pr_urls(key: str) -> list[str]:
    path = _cache_dir(key) / f"{key.upper()}-jira.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("prUrls") or [])


def _load_testplan_cache(key: str) -> dict[str, Any]:
    path = _cache_dir(key) / f"{key.upper()}-testplan.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _testcase_xlsx_path(key: str) -> Path:
    return ROOT / "testcases" / f"{key.upper()}-testcases.xlsx"


def _gap_supplement_xlsx_path(key: str) -> Path:
    return ROOT / "testcases" / f"{key.upper()}-gap-supplement.xlsx"


def _generated_case_count(result: dict[str, Any]) -> int:
    """Cases written this run (`generatedCases` or legacy `generated` key)."""
    for field in ("generatedCases", "generated"):
        value = result.get(field)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    return 0


def _should_refetch_after_generate(key: str, gen_result: dict[str, Any], *, gap_only: bool) -> bool:
    if _generated_case_count(gen_result) > 0:
        return True
    if gap_only:
        return _gap_supplement_xlsx_path(key).exists()
    return _testcase_xlsx_path(key).exists()


def _auto_generate_enabled(
    defaults: dict[str, Any],
    manifest: dict[str, Any],
    args: argparse.Namespace,
) -> bool:
    if args.skip_testplan:
        return False
    if manifest.get("skipTestcaseGeneration") or defaults.get("skipTestcaseGeneration"):
        return False
    if getattr(args, "no_auto_generate_testplan", False):
        return False
    gen = manifest.get("generateTestPlanIfMissing")
    if gen is None:
        gen = defaults.get("generateTestPlanIfMissing", False)
    return bool(gen)


def _fill_gaps_enabled(
    defaults: dict[str, Any],
    manifest: dict[str, Any],
    args: argparse.Namespace,
) -> bool:
    if args.skip_testplan:
        return False
    if getattr(args, "no_fill_testplan_gaps", False):
        return False
    fill = manifest.get("fillTestPlanGaps")
    if fill is None:
        fill = defaults.get("fillTestPlanGaps", True)
    return bool(fill)


def _attached_testcase_count(testplan_result: dict[str, Any]) -> int:
    cov = testplan_result.get("coverage") if isinstance(testplan_result.get("coverage"), dict) else {}
    try:
        return int(cov.get("attachedTestCaseCount") or 0)
    except (TypeError, ValueError):
        return 0


def _should_fill_testplan_gaps(
    key: str,
    testplan_result: dict[str, Any],
    defaults: dict[str, Any],
    manifest: dict[str, Any],
    args: argparse.Namespace,
) -> bool:
    """Gap fill only after a Jira/local attached plan was parsed (not gap-supplement alone)."""
    if testplan_result.get("status") != "ok":
        return False
    if not _fill_gaps_enabled(defaults, manifest, args):
        return False
    if _attached_testcase_count(testplan_result) <= 0:
        return False
    return bool(_uncovered_requirement_ids(key))


def _uncovered_requirement_ids(key: str) -> list[str]:
    tp = _load_testplan_cache(key)
    cov = tp.get("coverage") if isinstance(tp.get("coverage"), dict) else {}
    ids: list[str] = []
    for field in ("uncoveredRequirements", "uncoveredJiraRequirements", "uncoveredLadrRequirements"):
        for item in cov.get(field) or []:
            rid = str(item).strip().upper()
            if rid and rid not in ids:
                ids.append(rid)
    return ids


def _run_generate_testcases(
    key: str,
    *,
    gap_only: str | None = None,
    write_excel: bool = True,
) -> dict[str, Any]:
    cmd = [sys.executable, str(SCRIPTS / "generate_testcases_from_requirements.py"), key]
    if gap_only:
        cmd.extend(["--gap-only", gap_only])
    if write_excel:
        cmd.append("--write-excel")
    return _run(cmd, label="generate-testcases")


def _refetch_testplan(key: str, label: str = "testplan-refetch") -> dict[str, Any]:
    return _run(
        [sys.executable, str(SCRIPTS / "fetch_jira_testplan.py"), key, "--from-jira-cache"],
        label=label,
    )


def _should_invoke_testcase_writer(
    key: str,
    defaults: dict[str, Any],
    manifest: dict[str, Any],
    args: argparse.Namespace,
) -> bool:
    """Step 5a — agent must run @Spec2Test when no Jira plan and no local xlsx."""
    if args.skip_testplan:
        return False
    if manifest.get("skipTestcaseGeneration") or defaults.get("skipTestcaseGeneration"):
        return False
    tp = _load_testplan_cache(key)
    if tp.get("status") != "no_testplan":
        return False
    return not _testcase_xlsx_path(key).exists()


def _prefetch_args(key: str, args: argparse.Namespace, defaults: dict[str, Any]) -> list[str]:
    cmd = [sys.executable, str(SCRIPTS / "prefetch_coverage_inputs.py"), key]
    manifest = _load_manifest(key)
    pr_urls = list(args.pr_urls or []) if hasattr(args, "pr_urls") else []
    if not pr_urls and args.pr:
        pr_urls = [args.pr]
    if not pr_urls:
        pr_urls = list(manifest.get("prUrls") or [])
    if not pr_urls:
        pr_urls = _load_jira_pr_urls(key)
    for url in pr_urls:
        cmd.extend(["--pr", str(url)])
    repo = args.repo or defaults.get("repo") or manifest.get("repo")
    if not pr_urls and repo:
        cmd.extend(["--repo", str(repo)])
        if defaults.get("searchPrIfMissing", True) and not args.no_search_pr:
            cmd.append("--search-pr")
        compare = manifest.get("compareBranch") or defaults.get("compareBranch")
        if compare:
            cmd.extend(["--compare", str(compare)])
    if args.skip_if_fresh:
        cmd.append("--skip-if-fresh")
    return cmd


def run_pipeline(key: str, args: argparse.Namespace) -> dict[str, Any]:
    key = key.upper()
    defaults = load_coverage_defaults(ROOT)
    semantic = args.semantic_boost
    if semantic is None:
        semantic = bool(defaults.get("semanticMappingBoost", False))

    preflight = run_preflight(key, verify_jira=args.verify_jira)
    if not preflight["ok"]:
        fail_ids = ", ".join(preflight.get("requiredFailures") or [])
        raise RuntimeError(
            f"Preflight failed ({fail_ids}). "
            f"Fix setup then re-run: python scripts/preflight_coverage_validator.py {key} --verify-jira"
        )
    if args.preflight_only:
        return {"preflight": preflight, "skipped": True}

    steps: list[dict[str, Any]] = [{"preflight": preflight}]

    if args.fetch_jira:
        jira_cmd = [sys.executable, str(SCRIPTS / "fetch_jira_story.py"), key]
        if args.skip_if_fresh:
            jira_cmd.append("--skip-if-fresh")
        steps.append(_run(jira_cmd, label="jira"))

    if not args.skip_jira_check and not _jira_cache_exists(key):
        raise RuntimeError(
            f"Missing reports/.cache/{key}-jira.json after fetch — "
            f"check .env credentials or pass --from-mcp-json to fetch_jira_story.py"
        )

    if not args.skip_testplan:
        steps.append(
            _run(
                [sys.executable, str(SCRIPTS / "fetch_confluence_requirements.py"), key, "--from-jira-cache"],
                label="confluence",
            )
        )
        testplan_result = _run(
            [sys.executable, str(SCRIPTS / "fetch_jira_testplan.py"), key, "--from-jira-cache"],
            label="testplan",
        )
        steps.append(testplan_result)

        manifest = _load_manifest(key)
        # Local xlsx may exist from a prior testcase-writer run — re-fetch before halting.
        if (
            testplan_result.get("status") == "no_testplan"
            and _testcase_xlsx_path(key).exists()
        ):
            testplan_result = _run(
                [sys.executable, str(SCRIPTS / "fetch_jira_testplan.py"), key, "--from-jira-cache"],
                label="testplan-refetch",
            )
            steps.append(testplan_result)

        if _should_invoke_testcase_writer(key, defaults, manifest, args):
            if _auto_generate_enabled(defaults, manifest, args):
                gen_result = _run_generate_testcases(key, gap_only=None)
                steps.append(gen_result)
                if _should_refetch_after_generate(key, gen_result, gap_only=False):
                    testplan_result = _refetch_testplan(key)
                    steps.append(testplan_result)
                else:
                    return {
                        "issueKey": key,
                        "status": "needs_testcase_writer",
                        "testplanStatus": "no_testplan",
                        "steps": len(steps),
                        "message": (
                            f"Auto-generate produced no cases for {key}. "
                            f"Invoke @Spec2Test {key}, then re-run."
                        ),
                        "preflight": preflight,
                    }
            else:
                return {
                    "issueKey": key,
                    "status": "needs_testcase_writer",
                    "testplanStatus": "no_testplan",
                    "steps": len(steps),
                    "message": (
                        f"No Jira test plan for {key}. Invoke @Spec2Test {key} "
                        f"(see testplan-missing-fallback.md), then re-run this script."
                    ),
                    "preflight": preflight,
                }
        elif _should_fill_testplan_gaps(key, testplan_result, defaults, manifest, args):
            gap_result = _run_generate_testcases(
                key,
                gap_only="from-testplan",
            )
            steps.append(gap_result)
            if _should_refetch_after_generate(key, gap_result, gap_only=True):
                testplan_result = _refetch_testplan(key, label="testplan-gap-refetch")
                steps.append(testplan_result)

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
    parser.add_argument(
        "--fetch-jira",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch Jira story via fetch_jira_story.py before pipeline (default: on)",
    )
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
    parser.add_argument(
        "--no-auto-generate-testplan",
        action="store_true",
        help="Do not auto-generate QMetry cases when Jira test plan is missing",
    )
    parser.add_argument(
        "--no-fill-testplan-gaps",
        action="store_true",
        help="Do not auto-generate supplement cases for uncovered R/L in attached plan",
    )
    args = parser.parse_args()

    try:
        result = run_pipeline(args.issue_key, args)
        print(json.dumps(result, indent=2))
        if result.get("status") == "needs_testcase_writer":
            return 2
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
