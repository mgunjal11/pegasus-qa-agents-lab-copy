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
        "{{TESTPLAN_SPLIT_METRICS}}": render_testplan_split_metrics(cov),
        "{{UNMAPPED_TC_BLOCK}}": render_unmapped_test_cases(tp.get("testCases") or []),
        "{{SUGGESTED_MAPPING_BLOCK}}": render_suggested_mappings(issue_key, root),
    }
    note = tp.get("testPlanSummaryNote") or ""
    fields["{{TESTPLAN_NOTE}}"] = f'<div class="note-box">{esc(note)}</div>' if note else ""
    return fields


def load_mapping_cache(issue_key: str, root: Path | None = None) -> dict[str, Any]:
    base = root or Path(__file__).resolve().parents[1]
    path = base / "reports" / ".cache" / f"{issue_key.upper()}-mapping.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_jira_cache(issue_key: str, root: Path | None = None) -> dict[str, Any]:
    base = root or Path(__file__).resolve().parents[1]
    path = base / "reports" / ".cache" / f"{issue_key.upper()}-jira.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _readiness_item(label: str, ok: bool, detail: str) -> str:
    cls = "ready-ok" if ok else "ready-warn"
    icon = "✓" if ok else "!"
    return (
        f'<li class="readiness-item {cls}">'
        f'<span class="readiness-icon">{icon}</span>'
        f"<strong>{esc(label)}</strong> — {esc(detail)}</li>"
    )


def build_jira_readiness_block(issue_key: str, root: Path | None = None) -> str:
    """HTML checklist: Jira AC, PR, test plan, Confluence readiness."""
    jira = load_jira_cache(issue_key, root)
    tp = load_testplan_cache(issue_key, root)
    prefetch = load_prefetch_cache(issue_key, root)
    confluence_path = (root or Path(__file__).resolve().parents[1]) / "reports" / ".cache" / f"{issue_key.upper()}-confluence.json"
    conf = json.loads(confluence_path.read_text(encoding="utf-8")) if confluence_path.exists() else {}

    reqs = jira.get("requirements") or []
    pr_urls = jira.get("prUrls") or prefetch.get("prUrls") or []
    tp_status = tp.get("status") or "no_testplan"
    has_conf = bool(conf.get("ladrRequirements")) or bool(conf.get("pages"))

    items = [
        _readiness_item(
            "Acceptance criteria",
            bool(reqs),
            f"{len(reqs)} requirement(s) extracted" if reqs else "Add numbered acceptance criteria in description",
        ),
        _readiness_item(
            "GitHub PR",
            bool(pr_urls or prefetch.get("prs")),
            f"{len(pr_urls or prefetch.get('prs') or [])} PR(s) linked" if pr_urls or prefetch.get("prs") else "Add PR URL in description or comment",
        ),
        _readiness_item(
            "Test plan",
            tp_status == "ok",
            tp.get("testPlanSummaryNote") or tp_status.replace("_", " "),
        ),
        _readiness_item(
            "Confluence / LADR",
            has_conf or not any("ladr" in (r.get("text") or "").lower() for r in reqs),
            "LADR requirements loaded" if has_conf else "Optional — link wiki page if LADR applies",
        ),
    ]
    return (
        '<div class="jira-readiness-block">'
        "<h3>Jira input readiness</h3>"
        f"<ul>{''.join(items)}</ul>"
        "</div>"
    )


def render_testplan_split_metrics(cov: dict[str, Any]) -> str:
    """Sub-metrics: Jira AC % and LADR % separately."""
    jira_total = cov.get("jiraRequirementCount") or 0
    jira_cov = cov.get("jiraRequirementsCovered") or 0
    ladr_total = cov.get("ladrRequirementCount") or 0
    ladr_cov = cov.get("ladrRequirementsCovered") or 0
    parts = []
    if jira_total:
        parts.append(
            f'<span class="split-metric">Jira acceptance criteria: '
            f"<strong>{jira_cov}/{jira_total}</strong></span>"
        )
    if ladr_total:
        parts.append(
            f'<span class="split-metric">LADR scenarios: '
            f"<strong>{ladr_cov}/{ladr_total}</strong></span>"
        )
    if not parts:
        return ""
    return '<div class="testplan-split-metrics">' + " · ".join(parts) + "</div>"


def gwt_quality_badge(steps: dict[str, str]) -> str:
    from testplan_gwt import has_complete_gwt

    if has_complete_gwt(steps):
        return '<span class="badge badge-covered">Full</span>'
    if any((steps or {}).values()):
        return '<span class="badge badge-partial">Partial</span>'
    return '<span class="badge badge-missing">Missing</span>'


def evidence_type_badges(tc: dict[str, Any]) -> str:
    """Compact badges for Evidence column: Mascot / Edit / Job."""
    badges = []
    if tc.get("mascot_links"):
        badges.append('<span class="badge badge-e2e">Mascot</span>')
    ids = tc.get("evidence_ids") or []
    labels = {i.get("label", "").lower() for i in ids}
    if any("edit" in lb for lb in labels):
        badges.append('<span class="badge badge-implemented">Edit</span>')
    if any("job" in lb or "pegasus" in lb for lb in labels):
        badges.append('<span class="badge badge-shared">Job</span>')
    if badges:
        return " ".join(badges) + "<br>"
    return ""


def render_unmapped_test_cases(test_cases: list[dict[str, Any]]) -> str:
    unmapped = [tc for tc in test_cases if not (tc.get("mapped_requirements") or [])]
    if not unmapped:
        return ""
    items = "".join(
        f"<li><strong>{esc(tc.get('id', ''))}</strong> — {esc(tc.get('summary', '')[:120])}</li>"
        for tc in unmapped[:15]
    )
    extra = f"<li>… and {len(unmapped) - 15} more</li>" if len(unmapped) > 15 else ""
    return (
        '<div class="review-panel review-info unmapped-tc-block">'
        "<h3>Unmapped test cases</h3>"
        f"<ul>{items}{extra}</ul>"
        "</div>"
    )


def render_suggested_mappings(issue_key: str, root: Path | None = None) -> str:
    mapping = load_mapping_cache(issue_key, root)
    suggestions: list[str] = []
    for req in mapping.get("requirements") or []:
        for sug in req.get("suggestedTestCases") or []:
            suggestions.append(
                f"<li><strong>{esc(req.get('id', ''))}</strong> ↔ "
                f"<strong>{esc(sug.get('id', ''))}</strong> "
                f"({int(float(sug.get('overlap', 0)) * 100)}% keyword overlap) — "
                f"consider tagging {esc(req.get('id', ''))} in test plan</li>"
            )
    if not suggestions:
        return ""
    return (
        '<div class="review-panel review-info suggested-map-block">'
        "<h3>Suggested test plan ↔ acceptance criteria mappings</h3>"
        f"<ul>{''.join(suggestions[:10])}</ul>"
        "</div>"
    )


def build_cache_meta_line(issue_key: str, root: Path | None = None) -> str:
    """Cache freshness line for report header."""
    base = root or Path(__file__).resolve().parents[1]
    parts = []
    for suffix, label in (
        ("-prefetch.json", "GitHub"),
        ("-testplan.json", "Test plan"),
        ("-jira.json", "Jira"),
    ):
        path = base / "reports" / ".cache" / f"{issue_key.upper()}{suffix}"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                ts = (data.get("fetchedAt") or "")[:19].replace("T", " ")
                parts.append(f"{label} cache {ts} UTC" if ts else label)
            except (json.JSONDecodeError, OSError):
                parts.append(label)
    if not parts:
        return ""
    return " · ".join(parts)


def build_quick_links(issue_key: str, root: Path | None = None) -> str:
    jira = load_jira_cache(issue_key, root)
    prefetch = load_prefetch_cache(issue_key, root)
    links = [
        f'<a href="https://wbdstreaming.atlassian.net/browse/{issue_key.upper()}" target="_blank">Jira</a>',
    ]
    for ref in jira.get("testPlanReferences") or []:
        url = ref.get("url")
        if url:
            links.append(f'<a href="{esc(url)}" target="_blank">Test plan (SharePoint)</a>')
            break
    for pr in prefetch.get("prs") or []:
        u = pr.get("url")
        n = pr.get("number")
        if u:
            links.append(f'<a href="{esc(u)}" target="_blank">PR #{n}</a>')
    conf_path = (root or Path(__file__).resolve().parents[1]) / "reports" / ".cache" / f"{issue_key.upper()}-confluence.json"
    if conf_path.exists():
        conf = json.loads(conf_path.read_text(encoding="utf-8"))
        for page in conf.get("pages") or []:
            if page.get("webUrl"):
                links.append(f'<a href="{esc(page["webUrl"])}" target="_blank">Confluence</a>')
                break
    return '<div class="quick-links">' + " · ".join(links) + "</div>" if links else ""


def _badge_for_status(status: str, kind: str = "code") -> str:
    mapping = {
        "implemented": "badge-implemented",
        "covered": "badge-covered",
        "partial": "badge-partial",
        "missing": "badge-missing",
    }
    cls = mapping.get(status, "badge-not-verified")
    label = status.replace("_", " ").title()
    return f'<span class="badge {cls}">{esc(label)}</span>'


def render_requirement_rows_from_mapping(issue_key: str, root: Path | None = None) -> str:
    mapping = load_mapping_cache(issue_key, root)
    rows = []
    for req in mapping.get("requirements") or []:
        rid = req.get("id", "")
        files = ", ".join(req.get("matchedFiles") or [])[:200] or "—"
        conf = req.get("confidence", "low")
        rows.append(
            f"<tr>"
            f"<td>{esc(rid)}</td>"
            f"<td>{esc(req.get('text', ''))}</td>"
            f"<td>{_badge_for_status(req.get('codeStatus', 'missing'))}</td>"
            f"<td>{_badge_for_status(req.get('devTestStatus', 'missing'), 'dev')}</td>"
            f'<td><span class="badge badge-dev">{esc(str(req.get("owner", "shared")).title())}</span></td>'
            f'<td><span class="badge badge-e2e">{esc(str(req.get("qaScope", "e2e")).title())}</span></td>'
            f'<td><code>{esc(files)}</code> <span class="conf-badge">{esc(conf)}</span></td>'
            f"</tr>"
        )
    return "\n".join(rows) if rows else '<tr><td colspan="7">—</td></tr>'


def compute_release_score(
    req_pct: float | None,
    dev_pct: float | None,
    tp_pct: float | None,
    gap_count: int,
) -> tuple[int, str]:
    """Weighted 0–100 release readiness score."""
    scores: list[tuple[float, float]] = []
    if req_pct is not None:
        scores.append((req_pct, 0.3))
    if dev_pct is not None:
        scores.append((dev_pct, 0.25))
    if tp_pct is not None:
        scores.append((tp_pct, 0.25))
    ci_placeholder = 70.0
    scores.append((ci_placeholder, 0.1))
    gap_penalty = max(0, 100 - gap_count * 15)
    scores.append((gap_penalty, 0.1))
    if not scores:
        return 0, "metric-na"
    total_w = sum(w for _, w in scores)
    val = sum(s * w for s, w in scores) / total_w if total_w else 0
    score = int(round(val))
    cls = "metric-good" if score >= 85 else "metric-warn" if score >= 70 else "metric-fail"
    return score, cls


def build_release_score_block(
    req_pct: Any,
    dev_pct: Any,
    tp_pct: Any,
    gap_summary: str,
) -> str:
    gap_n = gap_summary.count("High") + gap_summary.count("Med") if gap_summary else 0
    try:
        r = float(req_pct) if req_pct is not None else None
    except (TypeError, ValueError):
        r = None
    try:
        d = float(dev_pct) if dev_pct is not None else None
    except (TypeError, ValueError):
        d = None
    try:
        t = float(tp_pct) if tp_pct is not None else None
    except (TypeError, ValueError):
        t = None
    score, cls = compute_release_score(r, d, t, gap_n)
    return (
        f'<div class="metric-card {cls} release-score-card">'
        f'<div class="label">Release readiness score</div>'
        f'<div class="metric-value">{score}%</div>'
        f'<div class="note">Weighted: dev code, dev tests, test plan, gaps</div>'
        f"</div>"
    )


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
        ev = evidence_type_badges(tc) + render_testplan_evidence(tc, jira_requirements)
        rows.append(
            f"<tr>"
            f"<td>{esc(tc.get('id', ''))}</td>"
            f"<td>{esc(scenario)}</td>"
            f"<td>{esc(', '.join(tc.get('mapped_requirements') or []) or '—')}</td>"
            f"<td>{gwt_quality_badge(steps)}</td>"
            f"<td>{render_gwt_steps(steps)}</td>"
            f"<td>{pr_alignment_for_tc(tc.get('mapped_requirements') or [])}</td>"
            f"<td>{ev}</td>"
            f"</tr>"
        )
    return "\n".join(rows) if rows else '<tr><td colspan="7">—</td></tr>'


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


def coverage_to_template_fields(cov: dict[str, Any]) -> dict[str, str]:
    """Map ci_coverage.coverage_to_report_fields() output to HTML template placeholders."""
    from ci_coverage import coverage_to_report_fields

    fields = coverage_to_report_fields(cov)
    return {
        "{{CI_LINE_COVERAGE}}": fields["lineCoverage"],
        "{{CI_LINE_CLASS}}": fields["lineClass"],
        "{{CI_LINE_NOTE}}": fields["lineNote"],
        "{{CI_BRANCH_COVERAGE}}": fields["branchCoverage"],
        "{{CI_BRANCH_CLASS}}": fields["branchClass"],
        "{{CI_BRANCH_NOTE}}": fields["branchNote"],
        # Legacy keys for regen scripts using patch_metric_note
        "lineCoverage": fields["lineCoverage"],
        "branchCoverage": fields["branchCoverage"],
        "lineNote": fields["lineNote"],
        "branchNote": fields["branchNote"],
        "lineClass": fields["lineClass"],
        "branchClass": fields["branchClass"],
    }


def _ci_coverage_from_pr_entry(pr: dict[str, Any]) -> dict[str, Any]:
    """Re-extract CI coverage from stored PR fields and apply branch display fallback."""
    from ci_coverage import extract_ci_coverage, finalize_ci_coverage, merge_coverage

    org = pr.get("org") or ""
    repo_name = pr.get("repo") or ""
    full_repo = f"{org}/{repo_name}" if org and repo_name else ""
    fresh = extract_ci_coverage(
        codecov_comment=pr.get("codecovComment"),
        sonar_comment=pr.get("sonarComment"),
        checks_text=pr.get("checks"),
        repo=full_repo or None,
    )
    cached = pr.get("ciCoverage") or {}
    return finalize_ci_coverage(merge_coverage(fresh, cached))


def ci_coverage_report_fields(issue_key: str, root: Path | None = None) -> dict[str, str]:
    """Build CI line/branch card placeholders from prefetch cache."""
    from ci_coverage import finalize_ci_coverage, merge_coverage

    cache = load_prefetch_cache(issue_key, root)
    merged: dict[str, Any] = {}
    for pr in cache.get("prs") or []:
        merged = merge_coverage(merged, _ci_coverage_from_pr_entry(pr))
    fields = coverage_to_template_fields(finalize_ci_coverage(merged))
    if not cache.get("prs") and cache.get("branchCompare"):
        bc = cache["branchCompare"]
        head = bc.get("head") or "branch"
        note = f"No PR for {issue_key.upper()}; {head} branch only"
        fields["{{CI_LINE_COVERAGE}}"] = "NA"
        fields["{{CI_BRANCH_COVERAGE}}"] = "NA"
        fields["{{CI_LINE_CLASS}}"] = "metric-na"
        fields["{{CI_BRANCH_CLASS}}"] = "metric-na"
        fields["{{CI_LINE_NOTE}}"] = note
        fields["{{CI_BRANCH_NOTE}}"] = note
    return fields


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


def is_test_diff_path(path: str) -> bool:
    """True when a PR diff path is a test or test-support file."""
    low = (path or "").lower()
    return (
        "/test" in low
        or low.startswith("test")
        or "_test." in low
        or low.endswith("_test.py")
        or "/tests/" in low
    )


def is_dev_test_module_path(path: str) -> bool:
    """Unit/integration pytest modules in a PR diff (excludes samples and fixture JSON)."""
    if not path or not is_test_diff_path(path):
        return False
    low = path.lower()
    if low.endswith(".json") or "samples/" in low or "/fixtures/" in low:
        return False
    name = Path(path).name
    return (
        (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def format_dev_tests_summary(test_paths: list[str], *, max_items: int = 6) -> str:
    """Comma-separated pytest module names from PR diff test paths."""
    modules: list[str] = []
    has_conftest = False
    for raw in test_paths:
        if not raw:
            continue
        name = Path(raw).name
        if name == "conftest.py" and is_test_diff_path(raw):
            has_conftest = True
            continue
        if not is_dev_test_module_path(raw):
            continue
        if name not in modules:
            modules.append(name)
    if has_conftest:
        modules.append("conftest.py")
    if not modules:
        return ""
    if len(modules) <= max_items:
        return ", ".join(modules)
    shown = modules[:max_items]
    return f"{', '.join(shown)} (+{len(modules) - max_items} more)"


def dev_tests_by_number_from_caches(issue_key: str, root: Path | None = None) -> dict[int | str, str]:
    """Build per-PR dev test summaries from mapping cache and prefetch diffNames."""
    mapping = load_mapping_cache(issue_key, root)
    prefetch = load_prefetch_cache(issue_key, root)
    by_num: dict[int | str, str] = {}

    for pr in mapping.get("prs") or []:
        num = pr.get("number")
        if num is None:
            continue
        summary = str(pr.get("devTests") or pr.get("dev_tests") or "").strip()
        if summary:
            by_num[num] = summary

    for pr in prefetch.get("prs") or []:
        num = pr.get("number")
        if num is None:
            continue
        if by_num.get(num):
            continue
        names = [n for n in (pr.get("diffNames") or []) if is_dev_test_module_path(n)]
        summary = format_dev_tests_summary(names)
        if summary:
            by_num[num] = summary

    return by_num


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
    file_count: int | str = "",
    test_file_count: int | str = "",
) -> str:
    """One §2 Linked PR(s) row with optional file counts."""
    repo_display = repo or "—"
    if author and not repo:
        repo_display = author
    state_display = (state or "—").strip()
    title_display = (title or "—").strip()
    dev_display = (dev_tests or "—").strip()
    if dev_display != "—":
        dev_display = f"<code>{esc(dev_display)}</code>"
    ci_cell = ci_status_html(checks)
    files_cell = "—"
    if file_count != "":
        tf = test_file_count if test_file_count != "" else 0
        files_cell = f"{file_count} files ({tf} test)"
    return (
        "<tr>"
        f"<td>{_pr_link_cell(url, number, repo_display)}</td>"
        f"<td><code>{esc(repo_display)}</code></td>"
        f"<td>{esc(state_display)}</td>"
        f"<td>{esc(title_display)}</td>"
        f"<td>{files_cell}</td>"
        f"<td>{dev_display}</td>"
        f"<td>{ci_cell}</td>"
        "</tr>"
    )


def render_pr_rows(prs: list[dict[str, Any]]) -> str:
    if not prs:
        return '<tr><td colspan="7">—</td></tr>'
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
            file_count=p.get("fileCount", p.get("file_count", "")),
            test_file_count=p.get("testFileCount", p.get("test_file_count", "")),
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
    diff_names = pr_entry.get("diffNames") or []
    test_n = sum(1 for n in diff_names if "/test" in n.lower() or "_test." in n.lower())
    return {
        "url": pr_entry.get("url") or "",
        "number": pr_entry.get("number", ""),
        "repo": full_repo,
        "state": view.get("state") or "",
        "title": view.get("title") or "",
        "dev_tests": dev_tests,
        "checks": pr_entry.get("checks"),
        "author": login,
        "fileCount": len(diff_names),
        "testFileCount": test_n,
    }


def build_branch_compare_pr_note(issue_key: str, root: Path | None = None) -> str:
    """Note box for stories implemented on a branch without a linked PR."""
    cache = load_prefetch_cache(issue_key, root)
    bc = cache.get("branchCompare") or {}
    if not bc:
        return ""
    repo = bc.get("repo") or cache.get("repo") or "—"
    head = bc.get("head") or "develop"
    base = bc.get("base") or "main"
    ahead = bc.get("ahead_by", "?")
    key = issue_key.upper()
    related = (
        ' Related UAT fix: <a href="https://github.com/wbd-msc/pegasus-ess/pull/94">'
        "pegasus-ess#94</a> (MSC-209847, merged)."
        if "pegasus-ess" in repo
        else ""
    )
    return (
        f'<div class="note-box"><strong>No PR references {esc(key)}.</strong> '
        f"Implementation is on <code>{esc(head)}</code> in <code>{esc(repo)}</code> "
        f"({ahead} commits ahead of <code>{esc(base)}</code>).{related}</div>"
    )


def render_branch_compare_pr_rows(issue_key: str, root: Path | None = None) -> str:
    """Linked PR table rows when evidence comes from branch compare instead of PRs."""
    cache = load_prefetch_cache(issue_key, root)
    bc = cache.get("branchCompare") or {}
    if not bc:
        return '<tr><td colspan="7">—</td></tr>'
    repo = bc.get("repo") or cache.get("repo") or ""
    mapping = load_mapping_cache(issue_key, root)
    dev_tests = ""
    for entry in mapping.get("prs") or []:
        dev_tests = str(entry.get("devTests") or "").strip()
        if dev_tests:
            break
    if not dev_tests:
        dev_tests = format_dev_tests_summary(
            [n for n in (bc.get("files") or []) if is_dev_test_module_path(n)]
        )
    rows: list[str] = []
    primary = next(
        (c for c in (bc.get("commits") or []) if "caption" in str(c.get("message", "")).lower()),
        (bc.get("commits") or [{}])[0],
    )
    sha = primary.get("sha") or ""
    if sha and repo:
        rows.append(
            render_pr_row(
                url=f"https://github.com/{repo}/commit/{sha}",
                number=f"commit {sha}",
                repo=primary.get("author") or repo,
                state="on develop",
                title=primary.get("message") or "Primary caption V2 implementation",
                dev_tests=dev_tests,
                checks=None,
            )
        )
    if "pegasus-ess" in repo:
        rows.append(
            render_pr_row(
                url="https://github.com/wbd-msc/pegasus-ess/pull/94",
                number="pegasus-ess#94",
                repo="@srsilla",
                state="MERGED",
                title="MSC-209847 fix (related)",
                checks=None,
            )
        )
    base = bc.get("base") or "main"
    head = bc.get("head") or "develop"
    rows.append(
        render_pr_row(
            url=f"https://github.com/{repo}/compare/{base}...{head}" if repo else "",
            number=f"{head} vs {base}",
            repo="—",
            state=f"{bc.get('ahead_by', '?')} ahead",
            title=f"{len(bc.get('files') or [])} files including caption workflow",
            dev_tests=dev_tests,
            checks=None,
        )
    )
    return "\n".join(rows)


def render_pr_rows_from_prefetch(
    issue_key: str,
    root: Path | None = None,
    dev_tests_by_number: dict[int | str, str] | None = None,
) -> str:
    cache = load_prefetch_cache(issue_key, root)
    prs = cache.get("prs") or []
    if not prs and cache.get("branchCompare"):
        return render_branch_compare_pr_rows(issue_key, root)
    dev_map = dev_tests_by_number if dev_tests_by_number is not None else dev_tests_by_number_from_caches(
        issue_key, root
    )
    rows = []
    for pr in prs:
        num = pr.get("number")
        dev = dev_map.get(num, "") if dev_map else ""
        if not dev:
            names = [n for n in (pr.get("diffNames") or []) if is_dev_test_module_path(n)]
            dev = format_dev_tests_summary(names)
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
    "Release readiness score": (
        "Weighted composite score from dev code coverage, dev test coverage, "
        "test plan coverage, and open-gap severity (higher is better)."
    ),
}

HEADER_H1_INFO = (
    "MSC coverage validation report comparing the Jira story to linked GitHub PRs, "
    "attached QMetry test plan, and CI pipeline metrics."
)

CACHE_META_INFO = (
    "UTC timestamps when GitHub (PR diff), test plan, and Jira story caches were last "
    "prefetched for this report run."
)

QUICK_LINKS_INFO = (
    "Quick navigation to the Jira story, SharePoint test plan, linked pull requests, "
    "and Confluence (when a design page was cached)."
)

META_FIELD_INFO: dict[str, str] = {
    "Jira": "Link to the Jira story on wbdstreaming.atlassian.net.",
    "Status": "Current Jira workflow status of the story (e.g. In Progress, Done).",
    "Type": "Jira issue type (Story, Bug, Task, etc.).",
    "Generated": "Date and time this HTML report was generated (local timezone).",
}

READINESS_PANEL_INFO: dict[str, str] = {
    "Jira input readiness": (
        "Pre-flight checklist: whether Jira acceptance criteria, PR links, test plan, "
        "and optional Confluence LADR are available for accurate scoring."
    ),
}

READINESS_ITEM_INFO: dict[str, str] = {
    "Acceptance criteria": (
        "Numbered requirements (R1, R2, …) extracted from the Jira description for traceability."
    ),
    "GitHub PR": (
        "Pull requests linked in Jira or discovered during prefetch — source of code and dev tests."
    ),
    "Test plan": (
        "QMetry Excel attachment parsed for scenarios, Given/When/Then steps, and requirement mapping."
    ),
    "Confluence / LADR": (
        "Optional Confluence design page for LADR (L1, L2, …) traceability; optional when story has no LADR."
    ),
}

NOTE_BOX_INFO = (
    "Source of the attached QMetry test plan: Jira attachment file, Excel sheet/tab, and scenario count."
)

SPLIT_METRIC_INFO: dict[str, str] = {
    "Jira acceptance criteria:": (
        "How many Jira acceptance criteria (R-items) have at least one mapped test case in the plan."
    ),
    "LADR scenarios:": (
        "How many Confluence LADR requirements (L-items) have at least one mapped test case in the plan."
    ),
}

SECTION_LEAD_INFO = (
    "Dev-owned acceptance criteria should be proven by unit or integration tests in the linked PR; "
    "QA-owned items need functional, E2E, or manual verification outside the PR test suite."
)

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
    header h1 .heading-label-row { display: inline-flex; align-items: flex-start; gap: 0.35rem; flex-wrap: wrap; }
    header .meta .metric-info-tip { vertical-align: middle; margin-left: 0.15rem; }
    .cache-meta-with-tip, .quick-links-with-tip, .note-box-with-tip, .section-lead-with-tip {
      display: flex; align-items: flex-start; gap: 0.35rem; flex-wrap: wrap;
    }
    .jira-readiness-block .readiness-item .metric-info-tip { margin-left: 0.2rem; vertical-align: middle; }
    .split-metric-with-tip { display: inline-flex; align-items: center; gap: 0.2rem; vertical-align: middle; }
"""

PR_TABLE_COLUMN_INFO: dict[str, str] = {
    "PR": "GitHub pull request number with a link to the PR page.",
    "Repo": "GitHub organization and repository (org/repo) that contains the pull request.",
    "State": "Pull request lifecycle state from GitHub (open, merged, or closed).",
    "Title": "Pull request title as shown on GitHub.",
    "Files": "Count of changed files in the PR diff, including test files.",
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
    "GWT": "Whether the test case has full Given, When, and Then steps in the plan.",
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
    "Unmapped test cases": (
        "Test plan scenarios with no mapped Jira R-item or LADR L-item — may indicate missing "
        "requirement tags or orphan scenarios."
    ),
    "Suggested test plan ↔ acceptance criteria mappings": (
        "Low-confidence keyword overlaps between uncovered requirements and test cases — "
        "consider adding explicit R/L tags in the test plan."
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


def inject_report_h1_tooltip(html: str) -> str:
    if 'aria-label="About Report title"' in html:
        return html
    match = re.search(r"<h1>([^<]+)</h1>", html)
    if not match:
        return html
    title = match.group(1)
    wrapped = (
        f"<h1><span class=\"heading-label-row\">{title}"
        f"{metric_info_icon_html('Report title', HEADER_H1_INFO)}</span></h1>"
    )
    return html.replace(match.group(0), wrapped, 1)


def inject_meta_field_tooltips(html: str) -> str:
    for label, tip in META_FIELD_INFO.items():
        key = f"About {label}"
        if key in html:
            continue
        plain = f"<strong>{label}:</strong>"
        if plain not in html:
            continue
        html = html.replace(plain, plain + metric_info_icon_html(label, tip), 1)
    return html


def inject_cache_meta_tooltip(html: str) -> str:
    if 'aria-label="About Cache freshness"' in html:
        return html
    plain = '<div class="cache-meta">'
    if plain not in html:
        return html
    icon = metric_info_icon_html("Cache freshness", CACHE_META_INFO)
    return html.replace(plain, f'<div class="cache-meta cache-meta-with-tip">{icon} ', 1)


def inject_quick_links_tooltip(html: str) -> str:
    if 'aria-label="About Quick links"' in html:
        return html
    plain = '<div class="quick-links">'
    if plain not in html:
        return html
    icon = metric_info_icon_html("Quick links", QUICK_LINKS_INFO)
    return html.replace(plain, f'<div class="quick-links quick-links-with-tip">{icon} ', 1)


def inject_readiness_block_tooltips(html: str) -> str:
    for title, tip in READINESS_PANEL_INFO.items():
        html = _inject_heading_tooltip(html, "h3", title, tip)
    for label, tip in READINESS_ITEM_INFO.items():
        marker = f'<strong>{label}</strong>{metric_info_icon_html(label, tip)}'
        if marker in html:
            continue
        plain = f"<strong>{label}</strong>"
        if plain in html:
            html = html.replace(plain, marker, 1)
    return html


def inject_note_box_tooltip(html: str) -> str:
    if "note-box-with-tip" in html:
        return html
    plain = '<div class="note-box">'
    if plain not in html:
        return html
    icon = metric_info_icon_html("Test plan source", NOTE_BOX_INFO)
    return html.replace(
        plain,
        f'<div class="note-box note-box-with-tip">{icon} ',
        1,
    )


def inject_split_metric_tooltips(html: str) -> str:
    for prefix, tip in SPLIT_METRIC_INFO.items():
        if f'aria-label="About {prefix.rstrip(":")}' in html:
            continue
        needle = f'<span class="split-metric">{prefix}'
        if needle not in html:
            continue
        icon = metric_info_icon_html(prefix.rstrip(":"), tip)
        html = html.replace(
            f'<span class="split-metric">{prefix}',
            f'<span class="split-metric split-metric-with-tip">{icon} {prefix}',
            1,
        )
    return html


def inject_section_lead_tooltip(html: str) -> str:
    if "section-lead-with-tip" in html:
        return html
    plain = '<p class="section-lead">'
    if plain not in html:
        return html
    icon = metric_info_icon_html("Dev vs QA ownership", SECTION_LEAD_INFO)
    return html.replace(plain, f'<p class="section-lead section-lead-with-tip">{icon} ', 1)


def inject_all_metric_label_tooltips(html: str) -> str:
    """Wrap summary, ownership, and release-score metric labels with info icons."""
    merged: dict[str, str] = {}
    merged.update(SUMMARY_METRIC_INFO)
    merged.update(OWNERSHIP_LABEL_INFO)
    for label, tip in merged.items():
        html = _inject_label_row(html, label, tip)
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
    html = inject_report_h1_tooltip(html)
    html = inject_meta_field_tooltips(html)
    html = inject_cache_meta_tooltip(html)
    html = inject_quick_links_tooltip(html)
    html = inject_readiness_block_tooltips(html)
    html = inject_verdict_tooltip(html)
    html = inject_section_header_tooltips(html)
    html = inject_all_metric_label_tooltips(html)
    html = inject_summary_group_tooltips(html)
    html = inject_pr_table_header_tooltips(html)
    html = inject_testplan_table_header_tooltips(html)
    html = inject_note_box_tooltip(html)
    html = inject_split_metric_tooltips(html)
    html = inject_section_lead_tooltip(html)
    html = inject_review_panel_tooltips(html)
    html = inject_trace_table_header_tooltips(html)
    html = inject_report_footer(html)
    return html


def wrap_summary_metric_labels(html: str) -> str:
    """Add info-icon tooltips to §1 coverage summary metric labels (legacy alias)."""
    return inject_all_metric_label_tooltips(html)
