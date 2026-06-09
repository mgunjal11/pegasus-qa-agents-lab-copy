#!/usr/bin/env python3
"""Extract CI line/branch coverage from Codecov, SonarQube, and pytest-cov artifacts."""

from __future__ import annotations

import io
import json
import re
import subprocess
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

_GH_SUBPROCESS = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace"}


def metric_class(pct: float | str | None) -> str:
    if pct is None or pct == "NA":
        return "metric-na"
    try:
        value = float(str(pct).rstrip("%"))
    except ValueError:
        return "metric-na"
    if value >= 85:
        return "metric-good"
    if value >= 70:
        return "metric-warn"
    return "metric-fail"


def _pct(value: float) -> str:
    return f"{round(value, 1)}%"


def parse_codecov_comment(body: str | None) -> dict[str, Any]:
    if not body or not str(body).strip():
        return {}
    text = str(body)
    out: dict[str, Any] = {}
    line = re.search(
        r"(?:All files|Coverage|Line coverage)[^\d]*(\d+\.?\d*)\s*%",
        text,
        re.I,
    )
    if line:
        out["linePct"] = float(line.group(1))
        out["lineSource"] = "Codecov PR comment"
    branch = re.search(r"Branch coverage[^\d]*(\d+\.?\d*)\s*%", text, re.I)
    if branch:
        out["branchPct"] = float(branch.group(1))
        out["branchSource"] = "Codecov PR comment"
    patch = re.search(r"Patch coverage[^\d]*(\d+\.?\d*)\s*%", text, re.I)
    if patch and "linePct" not in out:
        out["linePct"] = float(patch.group(1))
        out["lineSource"] = "Codecov patch coverage"
    return out


def parse_sonar_text(body: str | None) -> dict[str, Any]:
    if not body or not str(body).strip():
        return {}
    text = str(body)
    out: dict[str, Any] = {}
    new_line = re.search(
        r"(\d+\.?\d*)\s*%\s*Coverage\s*\((\d+\.?\d*)\s*%\s*Estimated after merge\)",
        text,
        re.I,
    )
    if new_line:
        out["linePct"] = float(new_line.group(1))
        out["lineSource"] = "SonarQube new code line coverage (PR)"
        out["branchPct"] = float(new_line.group(2))
        out["branchSource"] = "SonarQube overall line coverage"
        return out
    # Sonar bot PR comment (MSC-195138 pegasus-reps#22): markdown bullet with backticks
    estimated_pr_merge = re.search(
        r"Code Coverage\s*\(Estimated after PR merge\)\s*[-–—]\s*`?(\d+\.?\d*)\s*%`?",
        text,
        re.I,
    )
    if estimated_pr_merge:
        out["linePct"] = float(estimated_pr_merge.group(1))
        out["lineSource"] = "SonarQube Code Coverage (estimated after PR merge)"
    line = re.search(r"(\d+\.?\d*)\s*%\s*Coverage", text, re.I)
    if line:
        out["linePct"] = float(line.group(1))
        out["lineSource"] = "SonarQube line coverage (PR)"
    branch = re.search(
        r"(\d+\.?\d*)\s*%\s*(?:Branch coverage|Branches covered)",
        text,
        re.I,
    )
    if branch:
        out["branchPct"] = float(branch.group(1))
        out["branchSource"] = "SonarQube branch coverage (PR)"
    return out


def _apply_sonar_condition_metrics(out: dict[str, Any], conditions: list[dict[str, Any]]) -> None:
    for cond in conditions:
        key = cond.get("metricKey") or ""
        val = cond.get("actualValue")
        if val is None:
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        if key == "new_coverage" and "linePct" not in out:
            out["linePct"] = num
            out["lineSource"] = "SonarQube quality gate (new code line)"
        elif key == "new_branch_coverage":
            out["branchPct"] = num
            out["branchSource"] = "SonarQube quality gate (new code branch)"
        elif key == "branch_coverage" and "branchPct" not in out:
            out["branchPct"] = num
            out["branchSource"] = "SonarQube quality gate (branch)"
        elif key == "coverage" and "branchPct" not in out:
            out.setdefault("_overallLine", num)


def parse_sonar_quality_gate_log(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    out: dict[str, Any] = {}
    for line in text.splitlines():
        if "projectStatus" not in line or "metricKey" not in line:
            continue
        payload = line.split("Z ", 1)[-1] if "Z " in line[:40] else line
        start = payload.find('{"projectStatus"')
        if start < 0:
            continue
        chunk = payload[start:]
        try:
            data = json.loads(chunk)
            conditions = data.get("projectStatus", {}).get("conditions", [])
        except json.JSONDecodeError:
            conditions = [
                {"metricKey": m, "actualValue": v}
                for m, v in re.findall(
                    r'"metricKey":"([^"]+)".*?"actualValue":"([^"]+)"', chunk
                )
            ]
        _apply_sonar_condition_metrics(out, conditions)
    # Scan entire log for any Sonar quality-gate condition pairs (truncated lines miss JSON parse).
    pairs = re.findall(r'"metricKey":"([^"]+)".*?"actualValue":"([^"]+)"', text)
    if pairs:
        _apply_sonar_condition_metrics(
            out,
            [{"metricKey": k, "actualValue": v} for k, v in pairs],
        )
    if "branchPct" not in out and "_overallLine" in out:
        out["branchPct"] = out.pop("_overallLine")
        out["branchSource"] = "SonarQube quality gate (overall line; branch metric not published)"
    else:
        out.pop("_overallLine", None)
    return out


def parse_sonar_measures_json_log(text: str | None) -> dict[str, Any]:
    """Parse Sonar component/measures JSON fragments from CI logs (github-script output)."""
    if not text:
        return {}
    out: dict[str, Any] = {}
    for metric, value in re.findall(
        r'"metric"\s*:\s*"([^"]+)"\s*,\s*"value"\s*:\s*"([^"]+)"',
        text,
    ):
        try:
            num = float(value)
        except ValueError:
            continue
        if metric == "coverage" and "linePct" not in out:
            out["linePct"] = num
            out["lineSource"] = "SonarQube measures (overall line)"
        elif metric in ("branch_coverage", "new_branch_coverage") and "branchPct" not in out:
            out["branchPct"] = num
            out["branchSource"] = f"SonarQube measures ({metric})"
        elif metric == "new_coverage" and "linePct" not in out:
            out["linePct"] = num
            out["lineSource"] = "SonarQube measures (new code line)"
    for metric, value in re.findall(
        r'"(branch_coverage|new_branch_coverage|coverage|new_coverage)"\s*:\s*"?([0-9.]+)"?',
        text,
    ):
        try:
            num = float(value)
        except ValueError:
            continue
        if metric == "coverage" and "linePct" not in out:
            out["linePct"] = num
            out["lineSource"] = "SonarQube metrics JSON (overall line)"
        elif metric in ("branch_coverage", "new_branch_coverage") and "branchPct" not in out:
            out["branchPct"] = num
            out["branchSource"] = f"SonarQube metrics JSON ({metric})"
        elif metric == "new_coverage" and "linePct" not in out:
            out["linePct"] = num
            out["lineSource"] = "SonarQube metrics JSON (new code line)"
    return out


def parse_pytest_cov_table_log(text: str | None) -> dict[str, Any]:
    """Parse pytest-cov terminal report when Branch column is present."""
    if not text:
        return {}
    block = re.search(
        r"^Name\s+Stmts\s+Miss(?:\s+Branch\s+BrPart)?\s+Cover.*?(?=^=+\s*$|\Z)",
        text,
        re.M | re.S,
    )
    if not block:
        return {}
    totals = re.search(
        r"^TOTAL\s+\d+\s+\d+(?:\s+\d+\s+\d+)?\s+(\d+)%",
        block.group(0),
        re.M,
    )
    if not totals:
        return {}
    line_pct = float(totals.group(1))
    out: dict[str, Any] = {
        "linePct": line_pct,
        "lineSource": "pytest-cov TOTAL (CI workflow log)",
    }
    branch_row = re.search(
        r"^TOTAL\s+\d+\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)%",
        block.group(0),
        re.M,
    )
    if branch_row:
        out["branchPct"] = float(branch_row.group(3))
        out["branchSource"] = "pytest-cov Branch column (CI workflow log)"
    return out


def parse_cobertura_xml_snippets_log(text: str | None) -> dict[str, Any]:
    """Extract branch-rate / line-rate from coverage.xml snippets echoed in CI logs."""
    if not text:
        return {}
    out: dict[str, Any] = {}
    for rate in re.findall(r'branch-rate="([0-9.]+)"', text):
        try:
            br = float(rate) * 100
        except ValueError:
            continue
        if br > 0:
            out["branchPct"] = round(br, 1)
            out["branchSource"] = "pytest-cov coverage.xml branch-rate (CI log)"
            break
    if "linePct" not in out:
        for rate in re.findall(r'line-rate="([0-9.]+)"', text):
            try:
                lr = float(rate) * 100
            except ValueError:
                continue
            if lr > 0:
                out["linePct"] = round(lr, 1)
                out["lineSource"] = "pytest-cov coverage.xml line-rate (CI log)"
                break
    return out


def parse_pytest_total_log(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    for line in text.splitlines():
        m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", line)
        if m:
            return {
                "linePct": float(m.group(1)),
                "lineSource": "pytest-cov TOTAL (CI workflow log)",
            }
    return {}


def parse_coverage_xml(content: bytes | str) -> dict[str, Any]:
    if isinstance(content, str):
        content = content.encode("utf-8")
    try:
        root = ET.parse(io.BytesIO(content)).getroot()
    except ET.ParseError:
        return {}
    out: dict[str, Any] = {}
    line_rate = root.attrib.get("line-rate")
    branch_rate = root.attrib.get("branch-rate")
    if line_rate is not None:
        try:
            out["linePct"] = round(float(line_rate) * 100, 1)
            out["lineSource"] = "pytest-cov coverage.xml (CI artifact)"
        except ValueError:
            pass
    if branch_rate is not None:
        try:
            br = float(branch_rate) * 100
            if br > 0:
                out["branchPct"] = round(br, 1)
                out["branchSource"] = "pytest-cov coverage.xml (CI artifact)"
        except ValueError:
            pass
    return out


def merge_coverage(*sources: dict[str, Any]) -> dict[str, Any]:
    """Merge parsed coverage dicts; first non-empty value wins per field."""
    merged: dict[str, Any] = {}
    for src in sources:
        if not src:
            continue
        for key in ("linePct", "lineSource", "branchPct", "branchSource"):
            if key not in merged and src.get(key) is not None:
                merged[key] = src[key]
    return merged


def coverage_to_report_fields(cov: dict[str, Any]) -> dict[str, str]:
    line = cov.get("linePct")
    branch = cov.get("branchPct")
    line_display = _pct(line) if line is not None else "NA"
    branch_display = _pct(branch) if branch is not None else "NA"
    line_note = cov.get("lineSource") or (
        "No Codecov/Sonar/pytest coverage found on PR"
    )
    branch_note = cov.get("branchNote") or cov.get("branchSource") or (
        "Branch coverage not reported by Codecov, Sonar, or pytest-cov on this PR"
    )
    return {
        "lineCoverage": line_display,
        "branchCoverage": branch_display,
        "lineNote": line_note,
        "branchNote": branch_note,
        "lineClass": metric_class(line if line is not None else "NA"),
        "branchClass": metric_class(branch if branch is not None else "NA"),
    }


def fetch_sonarqube_comment(org: str, repo: str, number: int) -> str | None:
    try:
        raw = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{org}/{repo}/issues/{number}/comments",
                "--paginate",
            ],
            check=False,
            **_GH_SUBPROCESS,
        )
        if raw.returncode != 0 or not raw.stdout:
            return None
        comments = json.loads(raw.stdout)
        for comment in comments:
            login = (comment.get("user") or {}).get("login") or ""
            body = comment.get("body") or ""
            if not body.strip():
                continue
            if re.search(r"sonar", login, re.I):
                return body
            if re.search(r"Coverage.*\d+\.?\d*\s*%|SonarQube.*quality gate", body, re.I):
                return body
    except (json.JSONDecodeError, OSError):
        return None
    return None


def fetch_check_run_sonar_summary(org: str, repo: str, head_sha: str) -> str | None:
    try:
        raw = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{org}/{repo}/commits/{head_sha}/check-runs",
            ],
            check=False,
            **_GH_SUBPROCESS,
        )
        if raw.returncode != 0 or not raw.stdout:
            return None
        data = json.loads(raw.stdout)
        for run in data.get("check_runs") or []:
            if "sonar" not in (run.get("name") or "").lower():
                continue
            output = run.get("output") or {}
            summary = output.get("summary") or ""
            if summary.strip():
                return summary
    except (json.JSONDecodeError, OSError):
        return None
    return None


def fetch_ci_job_log(repo: str, job_id: str) -> str | None:
    try:
        raw = subprocess.run(
            ["gh", "api", f"repos/{repo}/actions/jobs/{job_id}/logs"],
            capture_output=True,
            check=False,
        )
        if raw.returncode != 0:
            return None
        return raw.stdout.decode("utf-8", errors="replace")
    except OSError:
        return None


def _job_id_from_checks_line(line: str) -> str | None:
    m = re.search(r"/job/(\d+)", line)
    return m.group(1) if m else None


def fetch_build_log_from_checks(checks_text: str | None, repo: str) -> str | None:
    """Fetch and merge CI job logs likely to contain Sonar gate output or pytest-cov."""
    if not checks_text:
        return None
    priority_markers = (
        ("build-deploy / build", "pass"),
        ("integration-test", "pass"),
        ("cicd-test-unit", "pass"),
        ("analyze (python)", "pass"),
    )
    chunks: list[str] = []
    seen_jobs: set[str] = set()
    for marker, status in priority_markers:
        for line in checks_text.splitlines():
            low = line.lower()
            if marker in low and status in low and "/job/" in line:
                job_id = _job_id_from_checks_line(line)
                if not job_id or job_id in seen_jobs:
                    continue
                seen_jobs.add(job_id)
                log = fetch_ci_job_log(repo, job_id)
                if log:
                    chunks.append(log)
    if chunks:
        return "\n".join(chunks)
    for line in checks_text.splitlines():
        if "/job/" in line:
            job_id = _job_id_from_checks_line(line)
            if job_id and job_id not in seen_jobs:
                log = fetch_ci_job_log(repo, job_id)
                if log:
                    return log
    return None


def fetch_coverage_artifact(repo: str, run_id: str, artifact_name: str = "unit-coverage-report-ci") -> bytes | None:
    """Download unit-coverage-report-ci zip (binary) and return coverage.xml bytes."""
    try:
        raw = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/actions/runs/{run_id}/artifacts",
            ],
            check=False,
            **_GH_SUBPROCESS,
        )
        if raw.returncode != 0 or not raw.stdout:
            return None
        artifacts = json.loads(raw.stdout).get("artifacts") or []
        target = next((a for a in artifacts if a.get("name") == artifact_name), None)
        if not target:
            return None
        if target.get("expired"):
            return None
        artifact_id = target.get("id")
        if not artifact_id:
            return None
        dl = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/actions/artifacts/{artifact_id}/zip",
            ],
            capture_output=True,
            check=False,
        )
        if dl.returncode != 0 or not dl.stdout:
            return None
        with zipfile.ZipFile(io.BytesIO(dl.stdout)) as zf:
            for name in zf.namelist():
                if name.endswith("coverage.xml"):
                    return zf.read(name)
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, KeyError):
        return None
    return None


def _run_id_from_checks_line(line: str) -> str | None:
    m = re.search(r"/actions/runs/(\d+)/", line)
    return m.group(1) if m else None


def fetch_coverage_artifact_from_checks(checks_text: str | None, repo: str) -> bytes | None:
    if not checks_text:
        return None
    for line in checks_text.splitlines():
        if "build" in line.lower() and "/actions/runs/" in line:
            run_id = _run_id_from_checks_line(line)
            if run_id:
                data = fetch_coverage_artifact(repo, run_id)
                if data:
                    return data
    return None


def finalize_ci_coverage(cov: dict[str, Any]) -> dict[str, Any]:
    """
    When CI only publishes Sonar new_coverage (line) and no branch metric exists,
    show line % on the branch card with an explicit note (avoids misleading NA).
    """
    out = dict(cov or {})
    if out.get("branchPct") is not None or out.get("linePct") is None:
        return out
    line_src = str(out.get("lineSource") or "")
    if "SonarQube" in line_src or "pytest-cov" in line_src:
        out["branchPct"] = out["linePct"]
        out["branchSource"] = "Not reported separately (same as CI line coverage)"
        out["branchNote"] = (
            "Branch coverage was not published separately on this PR "
            "(Sonar quality gate reported new_coverage only; Codecov/Sonar comment "
            "and coverage.xml artifact unavailable or expired)"
        )
    return out


def extract_ci_coverage(
    *,
    codecov_comment: str | None = None,
    sonar_comment: str | None = None,
    sonar_check_summary: str | None = None,
    checks_text: str | None = None,
    repo: str | None = None,
    ci_log: str | None = None,
    coverage_xml: bytes | None = None,
) -> dict[str, Any]:
    log = ci_log
    if not log and checks_text and repo:
        log = fetch_build_log_from_checks(checks_text, repo)
    xml = coverage_xml
    if not xml and checks_text and repo:
        xml = fetch_coverage_artifact_from_checks(checks_text, repo)
    merged = merge_coverage(
        parse_codecov_comment(codecov_comment),
        parse_sonar_text(sonar_comment),
        parse_sonar_text(sonar_check_summary),
        parse_coverage_xml(xml) if xml else {},
        parse_cobertura_xml_snippets_log(log),
        parse_pytest_cov_table_log(log),
        parse_pytest_total_log(log),
        parse_sonar_measures_json_log(log),
        parse_sonar_quality_gate_log(log),
    )
    return finalize_ci_coverage(merged)
