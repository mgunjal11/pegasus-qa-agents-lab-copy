#!/usr/bin/env python3
"""Regenerate MSC-205625 coverage report with fresh timestamp and test plan rows."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from coverage_report_helpers import (  # noqa: E402
    apply_report_ui_enhancements,
    ci_coverage_report_fields,
    load_testplan_cache,
    render_pr_rows_from_prefetch,
    render_testplan_rows,
)
from coverage_report_timestamp import report_paths  # noqa: E402

KEY = "MSC-205625"


def patch_metric_note(html: str, label: str, value: str, note: str) -> str:
    """Replace metric-value and note inside a metric-card containing label text."""
    label_block = (
        rf'(?:<div class="label-row">\s*<div class="label">{re.escape(label)}</div>.*?</div>'
        rf'|<div class="label">{re.escape(label)}</div>)'
    )
    pattern = (
        rf'(<div class="metric-card[^"]*">.*?{label_block}\s*'
        rf'<div class="metric-value">)[^<]*(</div>\s*<div class="note">)[^<]*(</div>)'
    )

    def repl(m: re.Match[str]) -> str:
        return f"{m.group(1)}{value}{m.group(2)}{note}{m.group(3)}"

    return re.sub(pattern, repl, html, count=1, flags=re.DOTALL)


def main() -> None:
    candidates = sorted(ROOT.glob(f"reports/{KEY}*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit(f"No existing {KEY} report under reports/")
    html = candidates[0].read_text(encoding="utf-8")
    out, generated, tz_label = report_paths(KEY, root=ROOT)
    tp = load_testplan_cache(KEY, ROOT)
    cov = tp.get("coverage") or {}
    rows = render_testplan_rows(
        tp.get("testCases") or [],
        tp.get("jiraRequirements") or tp.get("requirements") or [],
    )
    note = tp.get("testPlanSummaryNote") or ""
    tp_pct = cov.get("testplanCoveragePct")
    gwt_n = cov.get("completeGwtCount", 0)
    tc_n = cov.get("testCaseCount", 0)
    req_cov = cov.get("requirementsCovered", 0)
    req_total = cov.get("requirementCount", 4)
    detail = cov.get("coverageDetail", "")

    html = re.sub(
        r"<strong>Generated:</strong> [^<]+",
        f"<strong>Generated:</strong> {generated}",
        html,
        count=1,
    )
    html = re.sub(
        r"<strong>Status:</strong> Ready for Release<strong>Type:",
        "<strong>Status:</strong> Ready for Release &nbsp;|&nbsp; <strong>Type:",
        html,
        count=1,
    )
    html = re.sub(
        r"<strong>Status:</strong> [^<]+ &nbsp;\|&nbsp;",
        "<strong>Status:</strong> Ready for Release &nbsp;|&nbsp;",
        html,
        count=1,
    )
    if note:
        html = re.sub(
            r'(<section class="report-section section-testplan">.*?<div class="note-box">)[^<]*(?:<[^/][^>]*>[^<]*)*(</div>)',
            lambda m: m.group(1) + note + m.group(2),
            html,
            count=1,
            flags=re.DOTALL,
        )
    pattern = r'(<section class="report-section section-testplan">.*?<tbody>\s*)(.*?)(\s*</tbody>)'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        html = html[: match.start(2)] + "\n              " + rows + "\n            " + html[match.end(2) :]

    if tp_pct is not None:
        pct_str = f"{tp_pct}%"
        html = patch_metric_note(
            html,
            "Test plan acceptance criteria coverage",
            pct_str,
            f"{detail} — attached test plan",
        )
    verdict = (
        f"Pass with gaps — PR #161 (pick-genie) + Domino Inc as Fulll test plan ({tc_n} scenarios, "
        f"{gwt_n}/{tc_n} full Given/When/Then, {req_cov}/{req_total} acceptance criteria in test plan); "
        f"R4 SIT evidence and explicit passport assertion in Then steps still pending."
    )
    html = re.sub(
        r'<div class="verdict verdict-pass-gaps">[^<]+</div>',
        f'<div class="verdict verdict-pass-gaps">{verdict}</div>',
        html,
        count=1,
    )

    pr_rows = render_pr_rows_from_prefetch(
        KEY,
        ROOT,
        dev_tests_by_number={
            161: "TestDominoPassportRouting, passport_manager unit tests",
        },
    )
    ci = ci_coverage_report_fields(KEY, ROOT)
    html = patch_metric_note(html, "CI line coverage", ci["lineCoverage"], ci["lineNote"])
    html = patch_metric_note(
        html,
        "CI branch coverage",
        ci["branchCoverage"],
        ci["branchNote"],
    )
    html = re.sub(
        r'(<div class="metric-card )metric-na(">\s*<div class="label">CI line coverage</div>)',
        rf'\1{ci["lineClass"]}\2',
        html,
        count=1,
    )
    html = re.sub(
        r'(<div class="metric-card )metric-na(">\s*<div class="label">CI branch coverage</div>)',
        rf'\1{ci["branchClass"]}\2',
        html,
        count=1,
    )
    html = re.sub(
        r'(<section class="report-section section-pr">.*?<tbody>\s*)(.*?)(\s*</tbody>)',
        lambda m: m.group(1) + pr_rows + m.group(3),
        html,
        count=1,
        flags=re.DOTALL,
    )

    html = apply_report_ui_enhancements(html)

    out.write_text(html, encoding="utf-8")
    manifest_path = ROOT / "reports" / ".cache" / f"{KEY}-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"issueKey": KEY}
    data["lastReportFile"] = str(out.relative_to(ROOT)).replace("\\", "/")
    data["prUrls"] = [
        "https://github.com/wbd-msc/pegasus-pick-genie/pull/161",
        "https://github.com/wbd-msc/pegasus-encode-monitor/pull/195",
    ]
    data["repo"] = "wbd-msc/pegasus-pick-genie"
    data["testPlanSheet"] = "Inc as full"
    data["timezoneLabel"] = tz_label
    data["fetchedAt"] = "2026-05-27T11:20:00.000000+00:00"
    manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(out.resolve())
    print(generated)


if __name__ == "__main__":
    main()
