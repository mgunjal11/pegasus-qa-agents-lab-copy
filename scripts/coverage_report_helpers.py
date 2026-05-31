#!/usr/bin/env python3
"""HTML helpers for msc-dev-code-and-qa-test-coverage-validator reports."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from testplan_gwt import steps_for_display
from testplan_evidence import extract_testcase_evidence_ids, has_mascot_links

REPORT_AGENT_NAME = "msc-dev-code-and-qa-test-coverage-validator"
REPORT_DEVELOPER = "Mayur Gunjal"


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def render_mascot_links(links: list[dict[str, str]]) -> str:
    if not links:
        return ""
    parts = []
    for link in links:
        label = esc(link.get("label") or "Mascot")
        url = esc(link.get("url") or "")
        if not url:
            continue
        parts.append(f'<a href="{url}" target="_blank">{label}</a>')
    return "<br>".join(parts) if parts else ""


def render_evidence_ids(evidence_ids: list[dict[str, str]]) -> str:
    if not evidence_ids:
        return ""
    parts = []
    for item in evidence_ids:
        label = item.get("label") or "ID"
        value = item.get("value") or ""
        if not value:
            continue
        parts.append(f"<code>{esc(label)}: {esc(value)}</code>")
    return "<br>".join(parts) if parts else ""


def render_testplan_evidence(
    tc: dict[str, Any],
    jira_requirements: list[dict[str, str]] | None = None,
) -> str:
    """Evidence column: Mascot links when present; else Edit/Job/Request UUIDs from plan or Jira AC."""
    mascot_html = render_mascot_links(tc.get("mascot_links") or [])
    if mascot_html:
        return mascot_html
    evidence_ids = tc.get("evidence_ids") or extract_testcase_evidence_ids(tc, jira_requirements)
    id_html = render_evidence_ids(evidence_ids)
    if id_html:
        return id_html
    return '<span class="badge badge-not-verified">No Mascot links or IDs in test plan</span>'


def render_gwt_steps(steps: dict[str, str]) -> str:
    normalized = steps_for_display(steps)
    chunks = []
    for key in ("given", "when", "then"):
        val = normalized.get(key, "")
        if val:
            chunks.append(esc(val))
    if chunks:
        return "<br>".join(chunks)
    # Fallback: show combined step text when GWT is present but not split
    combined = "\n".join(str(v) for v in steps.values() if v)
    return esc(combined) if combined.strip() else "—"


def pr_alignment_for_tc(mapped: list[str]) -> str:
    if not mapped:
        return '<span class="badge badge-not-verified">Unmapped</span>'
    reqs = ", ".join(mapped)
    return f'<span class="badge badge-implemented">Aligns</span> {esc(reqs)}'


def ladr_coverage_badge(mapped: bool) -> str:
    if mapped:
        return '<span class="badge badge-covered">Covered</span>'
    return '<span class="badge badge-missing">Gap</span>'


def render_ladr_traceability_rows(traceability: list[dict[str, Any]]) -> str:
    if not traceability:
        return '<tr><td colspan="4">—</td></tr>'
    rows = []
    for row in traceability:
        tc_ids = row.get("testCaseIds") or []
        tc_cell = esc(", ".join(tc_ids)) if tc_ids else "—"
        rows.append(
            f"<tr>"
            f"<td>{esc(row.get('id', ''))}</td>"
            f"<td>{esc(row.get('text', ''))}</td>"
            f"<td>{tc_cell}</td>"
            f"<td>{ladr_coverage_badge(bool(row.get('mapped')))}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def render_ladr_traceability_block(testplan_cache: dict[str, Any]) -> str:
    """HTML subsection tying Confluence LADR requirements to Excel test cases."""
    traceability = testplan_cache.get("ladrTraceability") or []
    ladr_reqs = testplan_cache.get("ladrRequirements") or []
    if not traceability and ladr_reqs:
        from confluence_requirements import build_ladr_traceability

        traceability = build_ladr_traceability(
            testplan_cache.get("testCases") or [],
            ladr_reqs,
        )
    if not traceability:
        return ""

    cov = testplan_cache.get("coverage") or {}
    ladr_total = cov.get("ladrRequirementCount") or len(traceability)
    ladr_covered = cov.get("ladrRequirementsCovered") or sum(1 for r in traceability if r.get("mapped"))
    confluence = testplan_cache.get("confluence") or {}
    pages = confluence.get("pages") or []
    page_links = []
    for page in pages:
        url = page.get("webUrl") or ""
        title = page.get("title") or page.get("pageId") or "Confluence"
        if url:
            page_links.append(f'<a href="{esc(url)}" target="_blank">{esc(title)}</a>')
    source_line = " · ".join(page_links) if page_links else "Confluence LADR (linked from Jira)"
    lead = (
        f"{ladr_covered}/{ladr_total} LADR requirements mapped to test cases in the attached Excel plan. "
        f"Source: {source_line}."
    )
    return (
        '<div class="review-panel review-info ladr-trace-block" style="margin-bottom:1rem;">'
        "<h3>LADR ↔ test plan traceability</h3>"
        f'<p class="section-lead">{lead}</p>'
        '<div class="table-wrap">'
        '<table class="ladr-trace-table">'
        "<thead>"
        "<tr><th>LADR ID</th><th>Requirement</th><th>Test case(s)</th><th>Status</th></tr>"
        "</thead>"
        "<tbody>"
        f"{render_ladr_traceability_rows(traceability)}"
        "</tbody>"
        "</table>"
        "</div>"
        "</div>"
    )


def build_testplan_gaps_html(
    coverage: dict[str, Any],
    *,
    extra_gaps: list[str] | None = None,
) -> str:
    """Build {{TESTPLAN_GAPS_LIST}} HTML from coverage cache."""
    uncovered_ladr = coverage.get("uncoveredLadrRequirements") or []
    uncovered_jira = coverage.get("uncoveredJiraRequirements") or coverage.get("uncoveredRequirements") or []
    gaps: list[str] = list(extra_gaps or [])
    for r in uncovered_jira:
        if r.startswith("L"):
            continue
        gaps.append(
            f'<li class="medium"><strong>{esc(r)}</strong> — no mapped test case for Jira acceptance criterion</li>'
        )
    for r in uncovered_ladr:
        gaps.append(
            f'<li class="medium"><strong>{esc(r)}</strong> — no mapped test case for Confluence LADR requirement</li>'
        )
    tc_count = coverage.get("testCaseCount") or 0
    gwt_complete = coverage.get("completeGwtCount") or 0
    incomplete_gwt = tc_count - gwt_complete
    if incomplete_gwt:
        gaps.append(
            f'<li class="medium">{incomplete_gwt} test case(s) missing full Given/When/Then in step text</li>'
        )
    return "".join(gaps)


def testplan_coverage_class(pct: Any) -> str:
    if pct is None or pct == "NA" or pct == "Pending":
        return "metric-na"
    try:
        val = float(pct)
    except (TypeError, ValueError):
        return "metric-na"
    if val >= 85:
        return "metric-good"
    if val >= 70:
        return "metric-warn"
    return "metric-fail"


def build_testplan_report_fields(issue_key: str, root: Path | None = None) -> dict[str, str]:
    """Build TESTPLAN_* and LADR traceability placeholders from test plan cache."""
    tp = load_testplan_cache(issue_key, root)
    cov = tp.get("coverage") or {}
    jira_reqs = tp.get("jiraRequirements") or tp.get("requirements") or []
    tp_pct = cov.get("testplanCoveragePct")
    fields: dict[str, str] = {
        "{{TESTPLAN_COVERAGE_PCT}}": "NA" if tp_pct is None else f"{tp_pct}%",
        "{{TESTPLAN_COVERAGE_CLASS}}": testplan_coverage_class(tp_pct),
        "{{TESTPLAN_COVERAGE_DETAIL}}": cov.get("coverageDetail") or "No test plan",
        "{{TESTPLAN_ROWS}}": render_testplan_rows(tp.get("testCases") or [], jira_reqs),
        "{{LADR_TRACEABILITY_BLOCK}}": render_ladr_traceability_block(tp),
        "{{TESTPLAN_GAPS_LIST}}": build_testplan_gaps_html(cov),
    }
    note = tp.get("testPlanSummaryNote") or ""
    fields["{{TESTPLAN_NOTE}}"] = f'<div class="note-box">{esc(note)}</div>' if note else ""
    return fields


def render_testplan_rows(
    test_cases: list[dict[str, Any]],
    jira_requirements: list[dict[str, str]] | None = None,
) -> str:
    rows = []
    for tc in test_cases:
        steps = tc.get("steps") or {}
        section = tc.get("section") or ""
        summary = tc.get("summary") or ""
        scenario = f"{section} · {summary}" if section and summary else (section or summary or tc.get("id", ""))
        rows.append(
            f"<tr>"
            f"<td>{esc(tc.get('id', ''))}</td>"
            f"<td>{esc(scenario)}</td>"
            f"<td>{esc(', '.join(tc.get('mapped_requirements') or []) or '—')}</td>"
            f"<td>{render_gwt_steps(steps)}</td>"
            f"<td>{pr_alignment_for_tc(tc.get('mapped_requirements') or [])}</td>"
            f"<td>{render_testplan_evidence(tc, jira_requirements)}</td>"
            f"</tr>"
        )
    return "\n".join(rows) if rows else '<tr><td colspan="6">—</td></tr>'


def load_testplan_cache(issue_key: str, root: Path | None = None) -> dict[str, Any]:
    base = root or Path(__file__).resolve().parents[1]
    path = base / "reports" / ".cache" / f"{issue_key.upper()}-testplan.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_prefetch_cache(issue_key: str, root: Path | None = None) -> dict[str, Any]:
    base = root or Path(__file__).resolve().parents[1]
    path = base / "reports" / ".cache" / f"{issue_key.upper()}-prefetch.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def ci_coverage_report_fields(issue_key: str, root: Path | None = None) -> dict[str, str]:
    """Build CI line/branch card placeholders from prefetch cache."""
    from ci_coverage import coverage_to_report_fields, merge_coverage

    cache = load_prefetch_cache(issue_key, root)
    merged: dict[str, Any] = {}
    for pr in cache.get("prs") or []:
        merged = merge_coverage(merged, pr.get("ciCoverage") or {})
    if not merged:
        return coverage_to_report_fields({})
    return coverage_to_report_fields(merged)


def ci_status_html(checks_text: str | None) -> str:
    """Map gh pr checks output to CI status cell HTML; N/A when unavailable."""
    if not checks_text or not str(checks_text).strip():
        return '<span class="badge badge-na">N/A</span>'
    text = str(checks_text).strip()
    low = text.lower()
    unavailable_markers = (
        "unavailable",
        "failed to run",
        "could not",
        "error fetching",
        "no checks",
        "not found",
        "command failed",
        "gh:",
    )
    if any(m in low for m in unavailable_markers):
        return '<span class="badge badge-na">N/A</span>'
    has_fail = bool(
        re.search(r"\b(?:fail(?:ed|ing|ure)?|failing)\b", low)
        or "\tfail" in low
    )
    if has_fail:
        if "pass" in low or "successful" in low:
            summary = text.split("\n")[0][:80]
            return (
                f'<span class="badge badge-partial">Mixed</span> '
                f'<span class="ci-detail">{esc(summary)}</span>'
            )
        return '<span class="badge badge-missing">Failed</span>'
    if "pass" in low or "successful" in low or "succeeded" in low:
        return '<span class="badge badge-covered">Passed</span>'
    summary = text.split("\n")[0][:100]
    return f'<span class="badge badge-not-verified">{esc(summary)}</span>'


def _pr_link_cell(url: str, number: int | str, repo: str) -> str:
    label = f"#{number}"
    if url:
        return f'<a href="{esc(url)}" target="_blank">{esc(label)}</a>'
    short = repo.split("/")[-1] if "/" in repo else repo
    return esc(f"{short}#{number}")


def render_pr_row(
    *,
    url: str = "",
    number: int | str = "",
    repo: str = "",
    state: str = "",
    title: str = "",
    dev_tests: str = "",
    checks: str | None = None,
    author: str | None = None,
) -> str:
    """One §2 Linked PR(s) row: PR | Repo | State | Title | Dev tests | CI status."""
    repo_display = repo or "—"
    if author and not repo:
        repo_display = author
    state_display = (state or "—").strip()
    title_display = (title or "—").strip()
    dev_display = (dev_tests or "—").strip()
    if dev_display != "—":
        dev_display = f"<code>{esc(dev_display)}</code>"
    ci_cell = ci_status_html(checks)
    return (
        "<tr>"
        f"<td>{_pr_link_cell(url, number, repo_display)}</td>"
        f"<td><code>{esc(repo_display)}</code></td>"
        f"<td>{esc(state_display)}</td>"
        f"<td>{esc(title_display)}</td>"
        f"<td>{dev_display}</td>"
        f"<td>{ci_cell}</td>"
        "</tr>"
    )


def render_pr_rows(prs: list[dict[str, Any]]) -> str:
    if not prs:
        return '<tr><td colspan="6">—</td></tr>'
    return "\n".join(
        render_pr_row(
            url=str(p.get("url") or ""),
            number=p.get("number", ""),
            repo=str(p.get("repo") or ""),
            state=str(p.get("state") or ""),
            title=str(p.get("title") or ""),
            dev_tests=str(p.get("dev_tests") or p.get("devTests") or ""),
            checks=p.get("checks"),
            author=p.get("author"),
        )
        for p in prs
    )


def prefetch_pr_to_row(
    pr_entry: dict[str, Any],
    *,
    dev_tests: str = "",
) -> dict[str, Any]:
    """Normalize prefetch_coverage_inputs.py PR object to render_pr_rows dict."""
    org = pr_entry.get("org") or ""
    repo_name = pr_entry.get("repo") or ""
    full_repo = f"{org}/{repo_name}" if org and repo_name else ""
    view = pr_entry.get("view") or {}
    author = view.get("author") or {}
    login = ""
    if isinstance(author, dict):
        login = author.get("login") or ""
    return {
        "url": pr_entry.get("url") or "",
        "number": pr_entry.get("number", ""),
        "repo": full_repo,
        "state": view.get("state") or "",
        "title": view.get("title") or "",
        "dev_tests": dev_tests,
        "checks": pr_entry.get("checks"),
        "author": login,
    }


def render_pr_rows_from_prefetch(
    issue_key: str,
    root: Path | None = None,
    dev_tests_by_number: dict[int | str, str] | None = None,
) -> str:
    cache = load_prefetch_cache(issue_key, root)
    prs = cache.get("prs") or []
    rows = []
    for pr in prs:
        num = pr.get("number")
        dev = (dev_tests_by_number or {}).get(num, "") if dev_tests_by_number else ""
        rows.append(prefetch_pr_to_row(pr, dev_tests=dev))
    return render_pr_rows(rows)


SUMMARY_METRIC_INFO: dict[str, str] = {
    "Dev code coverage": (
        "Share of Jira acceptance criteria that have matching production code "
        "changes in the linked PR. Green ≥85%, amber 70–84.9%, red below 70%."
    ),
    "Dev unit / integration test coverage": (
        "Share of dev-owned acceptance criteria covered by unit or integration "
        "tests added or updated in the PR (not E2E or manual QA)."
    ),
    "Requirements mapped": (
        "How many Jira acceptance criteria were extracted from the story and "
        "scored in this report (e.g. R1–R4)."
    ),
    "Test plan acceptance criteria coverage": (
        "Share of Jira acceptance criteria and linked LADR/Confluence ESS scenarios "
        "that have at least one mapped test case in the attached test plan with Given/When/Then steps."
    ),
    "QA scope remaining": (
        "Count of requirements still needing QA verification—E2E, manual, "
        "regression, or spot-check—because dev tests do not fully cover them."
    ),
    "Open gaps": (
        "Implementation or test-plan concerns from the review, summarized by "
        "severity (e.g. High, Medium)."
    ),
    "CI line coverage": (
        "Percentage of code lines executed by automated tests in CI, from "
        "Codecov, SonarQube, or pytest-cov on the linked PR."
    ),
    "CI branch coverage": (
        "Percentage of code branches (if/else paths) covered by automated tests "
        "in CI, from Codecov, SonarQube, or pytest-cov on the linked PR."
    ),
}

METRIC_INFO_CSS = """
    .label-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.35rem; margin-bottom: 0.3rem; }
    .label-row .label { margin-bottom: 0; flex: 1; min-width: 0; }
    .metric-info-tip { position: relative; display: inline-flex; flex-shrink: 0; margin-top: 0.05rem; margin-left: 0.2rem; z-index: 1; }
    .metric-info-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 1rem; height: 1rem; border-radius: 50%;
      font-size: 0.62rem; font-weight: 700; font-style: italic; font-family: Georgia, serif;
      color: #475569; background: #e2e8f0; border: 1px solid #cbd5e1;
      cursor: pointer; line-height: 1;
    }
    .metric-info-tip:hover .metric-info-icon,
    .metric-info-tip:focus .metric-info-icon,
    .metric-info-tip:focus-within .metric-info-icon { background: #2563eb; color: #fff; border-color: #2563eb; outline: none; }
    .metric-info-tooltip {
      visibility: hidden; opacity: 0;
      position: absolute; z-index: 200;
      left: 0; right: auto; top: calc(100% + 8px);
      width: min(280px, calc(100vw - 2.5rem));
      max-width: 280px;
      padding: 0.55rem 0.65rem;
      background: #0f172a; color: #f8fafc;
      font-size: 0.72rem; font-weight: 400; line-height: 1.45;
      text-transform: none; letter-spacing: normal;
      border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.18);
      transition: opacity 0.15s ease;
      pointer-events: none;
      white-space: normal;
    }
    .label-row .metric-info-tooltip,
    .group-title-row .metric-info-tooltip {
      left: auto;
      right: 0;
    }
    .section-head .heading-label-row .metric-info-tooltip,
    .review-panel h3 .heading-label-row .metric-info-tooltip {
      left: auto;
      right: 0;
      transform: none;
    }
    th:last-child .metric-info-tooltip {
      left: auto;
      right: 0;
      transform: none;
    }
    th:nth-last-child(2) {
      position: relative;
    }
    th:nth-last-child(2) .th-label-row {
      position: static;
    }
    th:nth-last-child(2) .metric-info-tip {
      position: static;
    }
    th:nth-last-child(2) .metric-info-tooltip {
      left: auto;
      right: 0;
      transform: none;
    }
    .metric-info-tip:hover .metric-info-tooltip,
    .metric-info-tip:focus .metric-info-tooltip,
    .metric-info-tip:focus-within .metric-info-tooltip { visibility: visible; opacity: 1; }
"""

TOOLTIP_LAYOUT_FIX_MARKER = "/* tooltip layout fix v5 — prevent clipping in panels and sections */"

TOOLTIP_LAYOUT_FIX_CSS = """
    """ + TOOLTIP_LAYOUT_FIX_MARKER + """
    .container,
    .report-section,
    .report-section .section-head,
    .report-section .section-body,
    .review-panel,
    .metric-card,
    .metric-grid,
    .summary-grid,
    header,
    table,
    thead,
    tbody,
    tr,
    th {
      overflow: visible !important;
    }
    .table-wrap { overflow-x: auto; overflow-y: visible !important; }
    .review-panel h3,
    .heading-label-row,
    .label-row,
    .group-title-row,
    th .th-label-row {
      position: relative;
      z-index: 1;
    }
    th:nth-last-child(-n+2) {
      position: relative !important;
    }
    th:nth-last-child(-n+2) .th-label-row {
      position: static !important;
    }
    th:nth-last-child(-n+2) .metric-info-tip {
      position: static !important;
    }
    th:nth-last-child(-n+2):has(.metric-info-tip:hover),
    th:nth-last-child(-n+2):has(.metric-info-tip:focus-within),
    .metric-info-tip:hover,
    .metric-info-tip:focus-within {
      z-index: 250;
    }
    .metric-info-icon,
    .metric-info-tip {
      cursor: pointer !important;
    }
    .metric-info-tooltip {
      z-index: 300 !important;
      left: 0 !important;
      right: auto !important;
      transform: none !important;
      top: calc(100% + 8px) !important;
      width: min(280px, calc(100vw - 2.5rem)) !important;
      max-width: 280px !important;
      white-space: normal !important;
    }
    .label-row .metric-info-tooltip,
    .group-title-row .metric-info-tooltip,
    .section-head .heading-label-row .metric-info-tooltip,
    .review-panel h3 .heading-label-row .metric-info-tooltip {
      left: auto !important;
      right: 0 !important;
      transform: none !important;
    }
    th .metric-info-tooltip {
      left: 0 !important;
      right: auto !important;
      transform: none !important;
    }
    th:last-child .metric-info-tooltip {
      left: auto !important;
      right: 0 !important;
      transform: none !important;
    }
    th:nth-last-child(2) .metric-info-tooltip {
      left: auto !important;
      right: 0 !important;
      transform: none !important;
    }
"""

TOOLTIP_LAYOUT_FIX_BLOCK_RE = re.compile(
    r"\s*/\* tooltip layout fix(?: v\d+)? — prevent clipping in panels and sections \*/[\s\S]*?"
    r"(?=\n\s*</style>)",
    re.MULTILINE,
)

PR_TABLE_INFO_CSS = """
    .section-pr th .th-label-row,
    .section-testplan th .th-label-row,
    .section-trace th .th-label-row {
      display: inline-flex; align-items: center; gap: 0.25rem; vertical-align: middle; white-space: nowrap;
    }
    .section-pr th .metric-info-icon,
    .section-testplan th .metric-info-icon,
    .section-trace th .metric-info-icon { width: 0.9rem; height: 0.9rem; font-size: 0.58rem; }
    .section-pr th .metric-info-tooltip,
    .section-testplan th .metric-info-tooltip,
    .section-trace th .metric-info-tooltip { text-transform: none; font-weight: 400; letter-spacing: normal; }
    .section-head .heading-label-row { display: inline-flex; align-items: center; gap: 0.35rem; }
    .section-head .metric-info-icon {
      color: #fff; background: rgba(255,255,255,0.22); border-color: rgba(255,255,255,0.4);
    }
    .section-head .metric-info-tip:hover .metric-info-icon,
    .section-head .metric-info-tip:focus-within .metric-info-icon { background: #fff; color: #1e3a8a; }
    .summary-group-title .group-title-row {
      display: flex; align-items: center; justify-content: space-between; gap: 0.35rem;
    }
    .summary-group-title .group-title-text { flex: 1; }
    .review-panel h3 .heading-label-row { display: inline-flex; align-items: center; gap: 0.35rem; }
    header .verdict { display: flex; align-items: flex-start; gap: 0.45rem; }
    header .verdict .metric-info-tip { margin-top: 0.15rem; flex-shrink: 0; }
"""

PR_TABLE_COLUMN_INFO: dict[str, str] = {
    "PR": "GitHub pull request number with a link to the PR page.",
    "Repo": "GitHub organization and repository (org/repo) that contains the pull request.",
    "State": "Pull request lifecycle state from GitHub (open, merged, or closed).",
    "Title": "Pull request title as shown on GitHub.",
    "Dev tests": (
        "Key unit or integration test classes or files added or changed in the PR "
        "that cover dev-owned acceptance criteria."
    ),
    "CI status": (
        "Overall CI check result from gh pr checks — passed, failed, mixed, "
        "or N/A when checks could not be fetched."
    ),
}

SECTION_HEADER_INFO: dict[str, str] = {
    "Coverage summary": (
        "High-level readiness metrics from Jira acceptance criteria, linked PR code "
        "and tests, attached test plan, and CI pipeline coverage."
    ),
    "Linked PR(s)": (
        "GitHub pull requests linked to the Jira story, with CI status and dev test "
        "evidence from the PR diff."
    ),
    "Attached test plan validation": (
        "QMetry test plan from Jira mapped to Jira acceptance criteria and Confluence LADR "
        "requirements (when linked), with LADR ↔ test case traceability and PR alignment checks."
    ),
    "Dev vs QA test ownership": (
        "Which requirements are proven by dev unit/integration tests in the PR versus "
        "handed off to QA for E2E, manual, or regression verification."
    ),
    "Requirements traceability": (
        "Per-requirement view of implementation status, dev test coverage, ownership, "
        "and evidence citations."
    ),
    "Implementation review": (
        "Summary of what is correctly implemented in the PR and remaining gaps or "
        "concerns from the code and test-plan review."
    ),
    "Assumptions and open questions": (
        "Scoring assumptions, mapping rules, and unresolved questions used when "
        "generating this report."
    ),
    "Recommended actions": (
        "Suggested next steps for dev or QA before release based on open gaps."
    ),
}

SUMMARY_GROUP_INFO: dict[str, str] = {
    "Implementation & tests": (
        "Production code and automated test evidence from the linked PR against "
        "Jira acceptance criteria."
    ),
    "QA & release risk": (
        "Test plan coverage, remaining QA verification scope, and open review gaps."
    ),
    "CI pipeline coverage": (
        "Line and branch coverage percentages reported by CI tools on the linked PR."
    ),
}

TESTPLAN_TABLE_COLUMN_INFO: dict[str, str] = {
    "TC": "Test case ID from the attached QMetry test plan.",
    "Scenario": "Section and summary describing the test scenario.",
    "Mapped req": "Jira acceptance criteria (R1, R2, …) and Confluence LADR items (L1, L2, …) mapped to this test case.",
    "Given When Then": "Test steps from the QMetry plan in Given/When/Then form.",
    "PR alignment": "Whether the linked PR implementation aligns with this test case.",
    "Evidence": "Mascot fulfillment links when present; otherwise Edit ID, Job ID, Media Request, or other UUIDs from the test plan or mapped Jira acceptance criteria.",
}

LADR_TRACE_TABLE_COLUMN_INFO: dict[str, str] = {
    "LADR ID": "Confluence LADR requirement identifier (L1, L2, …) parsed from the linked design doc.",
    "Requirement": "LADR ESS milestone or status-code text from Confluence.",
    "Test case(s)": "Excel test plan case IDs that semantically cover this LADR requirement.",
    "Status": "Covered when at least one test case maps to this LADR item; Gap when none.",
}

TRACE_TABLE_COLUMN_INFO: dict[str, str] = {
    "ID": "Requirement identifier extracted from the Jira story (R1, R2, …).",
    "Requirement": "Acceptance criteria or requirement text from Jira.",
    "Code": "Whether production code in the PR implements this requirement.",
    "Dev tests": "Whether unit or integration tests in the PR cover this requirement.",
    "Owner": "Who owns verification: Dev, Shared (dev + QA), or QA.",
    "QA scope": "Type of QA verification still needed, if any (E2E, Manual, Regression, etc.).",
    "Evidence": "File paths, test names, or test plan references supporting the assessment.",
}

OWNERSHIP_LABEL_INFO: dict[str, str] = {
    "Covered by dev tests (unit / integration)": (
        "Requirements already proven by unit or integration tests in the linked PR."
    ),
    "QA handoff": (
        "Requirements QA must still verify in functional, E2E, or manual testing."
    ),
}

REVIEW_PANEL_INFO: dict[str, str] = {
    "Test plan gaps": (
        "Uncovered Jira acceptance criteria or Confluence LADR requirements with no mapped "
        "test case, plus Given/When/Then or PR alignment issues."
    ),
    "LADR ↔ test plan traceability": (
        "Each Confluence LADR requirement (L1…Ln) tied to test case IDs from the Excel "
        "attachment — shows which design scenarios QA validates."
    ),
    "✓ Correctly implemented": (
        "Requirements and behaviors that match the Jira story and are supported by PR evidence."
    ),
    "⚠ Gaps and concerns": (
        "Missing implementation, weak test coverage, or contradictions flagged in the review."
    ),
}

VERDICT_INFO = (
    "Overall readiness: Pass when requirements are met; Pass with gaps when minor items "
    "remain; Fail when critical gaps or contradictions exist."
)


def metric_info_icon_html(label: str, tip: str | None = None) -> str:
    text = tip if tip is not None else SUMMARY_METRIC_INFO.get(label, "")
    if not text:
        return ""
    return (
        f'<span class="metric-info-tip" tabindex="0" role="button" '
        f'aria-label="About {esc(label)}">'
        f'<span class="metric-info-icon" aria-hidden="true">i</span>'
        f'<span class="metric-info-tooltip">{esc(text)}</span></span>'
    )


def render_table_header_row(columns: dict[str, str]) -> str:
    """Table thead row with info-icon tooltips on each column."""
    cells = []
    for col, tip in columns.items():
        icon = metric_info_icon_html(col, tip)
        cells.append(f'<th><span class="th-label-row">{esc(col)}{icon}</span></th>')
    return "<tr>" + "".join(cells) + "</tr>"


def render_pr_table_header_row() -> str:
    """§2 Linked PR(s) thead row with info-icon tooltips on each column."""
    return render_table_header_row(PR_TABLE_COLUMN_INFO)


def _inject_heading_tooltip(html: str, tag: str, title: str, tip: str) -> str:
    if f'<span class="heading-label-row">{esc(title)}' in html:
        return html
    if f'<span class="heading-label-row">{title}' in html:
        return html
    plain = f"<{tag}>{title}</{tag}>"
    wrapped = (
        f"<{tag}><span class=\"heading-label-row\">{title}"
        f"{metric_info_icon_html(title, tip)}</span></{tag}>"
    )
    if plain in html:
        return html.replace(plain, wrapped, 1)
    plain_esc = f"<{tag}>{esc(title)}</{tag}>"
    if plain_esc in html:
        return html.replace(plain_esc, wrapped, 1)
    return html


def _inject_label_row(html: str, label: str, tip: str) -> str:
    if f'<div class="label-row"><div class="label">{label}</div>' in html:
        return html
    plain = f'<div class="label">{label}</div>'
    wrapped = (
        f'<div class="label-row"><div class="label">{label}</div>'
        f"{metric_info_icon_html(label, tip)}</div>"
    )
    if plain in html:
        return html.replace(plain, wrapped, 1)
    return html


def _replace_section_thead(html: str, section_class: str, header_row: str) -> str:
    pattern = (
        rf'(<section class="report-section {section_class}">.*?<thead>\s*)'
        r"<tr>.*?</tr>"
        r"(\s*</thead>)"
    )
    return re.sub(pattern, rf"\1{header_row}\2", html, count=1, flags=re.DOTALL)


def _ensure_info_icon_styles(html: str) -> str:
    bundle = METRIC_INFO_CSS + PR_TABLE_INFO_CSS
    if "metric-info-tip" not in html:
        html = html.replace("</style>", bundle + "\n  </style>", 1)
    elif ".section-head .heading-label-row" not in html:
        html = html.replace("</style>", PR_TABLE_INFO_CSS + "\n  </style>", 1)
    return html


def inject_section_header_tooltips(html: str) -> str:
    for title, tip in SECTION_HEADER_INFO.items():
        html = _inject_heading_tooltip(html, "h2", title, tip)
    return html


def inject_summary_group_tooltips(html: str) -> str:
    for title, tip in SUMMARY_GROUP_INFO.items():
        if f'group-title-text">{esc(title)}' in html:
            continue
        plain = f'<div class="summary-group-title">{esc(title)}</div>'
        wrapped = (
            f'<div class="summary-group-title"><span class="group-title-row">'
            f'<span class="group-title-text">{esc(title)}</span>'
            f"{metric_info_icon_html(title, tip)}</span></div>"
        )
        if plain in html:
            html = html.replace(plain, wrapped, 1)
    return html


def inject_verdict_tooltip(html: str) -> str:
    if "verdict" not in html or 'aria-label="About verdict"' in html:
        return html
    icon = metric_info_icon_html("Verdict", VERDICT_INFO).replace(
        'aria-label="About Verdict"', 'aria-label="About verdict"'
    )
    return re.sub(
        r'(<div class="verdict verdict-[^"]+">)',
        rf"\1{icon}",
        html,
        count=1,
    )


def inject_pr_table_header_tooltips(html: str) -> str:
    if "section-pr" not in html:
        return html
    return _replace_section_thead(html, "section-pr", render_pr_table_header_row())


def inject_testplan_table_header_tooltips(html: str) -> str:
    if "section-testplan" not in html:
        return html
    html = _replace_section_thead(
        html, "section-testplan", render_table_header_row(TESTPLAN_TABLE_COLUMN_INFO)
    )
    if "ladr-trace-table" not in html:
        return html
    pattern = (
        r'(<table class="ladr-trace-table">\s*<thead>\s*)'
        r"<tr>.*?</tr>"
        r"(\s*</thead>)"
    )
    return re.sub(
        pattern,
        rf"\1{render_table_header_row(LADR_TRACE_TABLE_COLUMN_INFO)}\2",
        html,
        count=1,
        flags=re.DOTALL,
    )


def inject_trace_table_header_tooltips(html: str) -> str:
    if "section-trace" not in html:
        return html
    return _replace_section_thead(
        html, "section-trace", render_table_header_row(TRACE_TABLE_COLUMN_INFO)
    )


def inject_ownership_card_tooltips(html: str) -> str:
    if "section-ownership" not in html:
        return html
    for label, tip in OWNERSHIP_LABEL_INFO.items():
        html = _inject_label_row(html, label, tip)
    return html


def inject_review_panel_tooltips(html: str) -> str:
    for title, tip in REVIEW_PANEL_INFO.items():
        html = _inject_heading_tooltip(html, "h3", title, tip)
    return html


def _strip_legacy_tooltip_layout_fix(html: str) -> str:
    """Remove v1 tooltip-layout CSS (comment optional; body ends at th:last-child rule)."""
    return re.sub(
        r"\s*(?:/\* tooltip layout fix(?: v\d+)? — prevent clipping[^*]*\*/\s*)?"
        r"\.report-section,\s*\n\s*\.report-section \.section-body,.*?"
        r"th:last-child \.metric-info-tooltip \{[^}]+\}\s*",
        "\n",
        html,
        count=1,
        flags=re.DOTALL,
    )


def inject_tooltip_layout_fix(html: str) -> str:
    """Ensure tooltip CSS avoids overflow clipping (idempotent; upgrades v1–v3 → v4)."""
    html = html.replace("cursor: help;", "cursor: pointer;")
    html = _strip_legacy_tooltip_layout_fix(html)
    html = TOOLTIP_LAYOUT_FIX_BLOCK_RE.sub("", html)
    if TOOLTIP_LAYOUT_FIX_MARKER in html:
        return html
    return html.replace("</style>", TOOLTIP_LAYOUT_FIX_CSS + "\n  </style>", 1)


def render_report_footer() -> str:
    """Report footer with agent name and developer credit."""
    return (
        f"<footer>Generated by {REPORT_AGENT_NAME} · "
        f"Developed by {esc(REPORT_DEVELOPER)}</footer>"
    )


def inject_report_footer(html: str) -> str:
    """Ensure report footer includes agent and developer attribution (idempotent)."""
    footer = render_report_footer()
    if footer in html:
        return html
    if re.search(r"<footer>\s*Generated by msc-dev-code-and-qa-test-coverage-validator\s*</footer>", html):
        return re.sub(
            r"<footer>\s*Generated by msc-dev-code-and-qa-test-coverage-validator\s*</footer>",
            footer,
            html,
            count=1,
        )
    if "<footer>" in html:
        return re.sub(r"<footer>.*?</footer>", footer, html, count=1, flags=re.DOTALL)
    if "</body>" in html:
        return html.replace("</body>", f"    {footer}\n  </body>", 1)
    return html


def apply_report_ui_enhancements(html: str) -> str:
    """Add info-icon tooltips and footer attribution across the coverage validation report."""
    html = _ensure_info_icon_styles(html)
    html = inject_tooltip_layout_fix(html)
    html = inject_verdict_tooltip(html)
    html = inject_section_header_tooltips(html)
    html = wrap_summary_metric_labels(html)
    html = inject_summary_group_tooltips(html)
    html = inject_pr_table_header_tooltips(html)
    html = inject_testplan_table_header_tooltips(html)
    html = inject_ownership_card_tooltips(html)
    html = inject_trace_table_header_tooltips(html)
    html = inject_review_panel_tooltips(html)
    html = inject_report_footer(html)
    return html


def wrap_summary_metric_labels(html: str) -> str:
    """Add info-icon tooltips to §1 coverage summary metric labels."""
    html = _ensure_info_icon_styles(html)
    for label in SUMMARY_METRIC_INFO:
        if f'<div class="label-row"><div class="label">{label}</div>' in html:
            continue
        plain = f'<div class="label">{label}</div>'
        wrapped = (
            f'<div class="label-row"><div class="label">{label}</div>'
            f"{metric_info_icon_html(label)}</div>"
        )
        if plain in html:
            html = html.replace(plain, wrapped, 1)
    return html
