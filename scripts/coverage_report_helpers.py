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


def is_generated_testplan(testplan_cache: dict[str, Any]) -> bool:
    return testplan_cache.get("testPlanSource") == "workspace_generated"


def render_testplan_evidence(
    tc: dict[str, Any],
    jira_requirements: list[dict[str, str]] | None = None,
    *,
    generated_local: bool = False,
) -> str:
    """Evidence column: Mascot links when present; else Edit/Job/Request UUIDs from plan or Jira AC."""
    mascot_html = render_mascot_links(tc.get("mascot_links") or [])
    if mascot_html:
        return mascot_html
    evidence_ids = list(tc.get("evidence_ids") or [])
    if not evidence_ids and not generated_local:
        evidence_ids = extract_testcase_evidence_ids(tc, jira_requirements)
    id_html = render_evidence_ids(evidence_ids)
    if id_html:
        return id_html
    if generated_local:
        return '<span class="badge badge-not-verified">No execution evidence</span>'
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
    from confluence_requirements import collect_ladr_page_links

    issue_key = str(testplan_cache.get("issueKey") or "")
    page_links = []
    for page in collect_ladr_page_links(issue_key) if issue_key else []:
        page_links.append(
            f'<a href="{esc(page["url"])}" target="_blank">{esc(page["title"])}</a>'
        )
    if not page_links:
        confluence = testplan_cache.get("confluence") or {}
        for page in confluence.get("pages") or []:
            url = page.get("webUrl") or page.get("url") or ""
            title = page.get("title") or page.get("pageId") or "Confluence"
            if url:
                page_links.append(f'<a href="{esc(url)}" target="_blank">{esc(title)}</a>')
    source_line = " · ".join(page_links) if page_links else "Confluence LADR (inferred — no wiki URL in cache)"
    lead = (
        f"{ladr_covered}/{ladr_total} LADR requirements mapped to test cases in the attached Excel plan. "
        f"Source: {source_line}."
    )
    return (
        '<div class="review-panel review-info ladr-trace-block" style="margin-bottom:1rem;">'
        "<h3>LADR ↔ test plan traceability</h3>"
        f'<p class="ladr-section-lead">{lead}</p>'
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
        "{{TESTPLAN_ROWS}}": render_testplan_rows(
            tp.get("testCases") or [],
            jira_reqs,
            generated_local=is_generated_testplan(tp),
        ),
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
    cls = "ready-ok" if ok else "ready-missing"
    icon = "✓" if ok else "✗"
    return (
        f'<li class="readiness-item {cls}">'
        f'<span class="readiness-icon" aria-hidden="true">{icon}</span>'
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
    from confluence_requirements import collect_ladr_page_links

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
    conf_pages = collect_ladr_page_links(issue_key, root)
    for page in conf_pages:
        title = (page.get("title") or "").strip()
        if len(conf_pages) == 1 and not title.upper().startswith("LADR"):
            label = "LADR" if title else "LADR (Confluence)"
        else:
            label = title or "LADR"
        if len(label) > 48:
            label = label[:45] + "…"
        links.append(f'<a href="{esc(page["url"])}" target="_blank">{esc(label)}</a>')
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


def _badge_for_qa_scope(scope: str) -> str:
    """QA scope column badge — None when dev tests fully cover the requirement."""
    key = (scope or "e2e").lower().replace(" ", "-")
    labels = {
        "none": ("badge-na", "None"),
        "n/a": ("badge-na", "N/A"),
        "na": ("badge-na", "N/A"),
        "spot-check": ("badge-spot", "Spot-check"),
        "e2e": ("badge-e2e", "E2E"),
        "manual": ("badge-manual", "Manual"),
        "regression": ("badge-e2e", "Regression"),
    }
    cls, label = labels.get(key, ("badge-e2e", key.replace("-", " ").title()))
    return f'<span class="badge {cls}">{esc(label)}</span>'


def _qa_scope_needs_qa_execution(scope: str) -> bool:
    return (scope or "").lower() not in ("none", "n/a", "na", "")


def _format_qa_scope_summary(reqs: list[dict[str, Any]], reqs_needing_qa: set[str]) -> str:
    """Metric value: count with optional E2E / Manual / … breakdown."""
    n_qa = len(reqs_needing_qa)
    if not n_qa:
        return "0 items"
    scope_counts: dict[str, int] = {}
    for req in reqs:
        rid = str(req.get("id") or "")
        if rid not in reqs_needing_qa:
            continue
        scope = str(req.get("qaScope") or "e2e").lower()
        if scope in ("none", "n/a", "na", ""):
            continue
        label = {
            "e2e": "E2E",
            "manual": "Manual",
            "regression": "Regression",
            "spot-check": "Spot-check",
        }.get(scope, scope.replace("-", " ").title())
        scope_counts[label] = scope_counts.get(label, 0) + 1
    if scope_counts:
        breakdown = " · ".join(f"{v} {k}" for k, v in sorted(scope_counts.items()))
        return f"{n_qa} item(s) ({breakdown})"
    return f"{n_qa} item(s)"


def _format_qa_scope_detail(
    reqs: list[dict[str, Any]],
    reqs_needing_qa: set[str],
    tc_ids: list[str],
) -> str:
    """One-line note under QA scope remaining card (not the hover tooltip)."""
    if not reqs_needing_qa:
        n_none = sum(
            1
            for r in reqs
            if not _qa_scope_needs_qa_execution(str(r.get("qaScope") or ""))
            and str(r.get("devTestStatus")) == "covered"
        )
        if n_none:
            return f"All scored requirements dev-covered ({n_none} with QA scope None)"
        return "No separate QA execution required"

    jira_ids = sorted((r for r in reqs_needing_qa if str(r).startswith("R")), key=lambda x: (len(x), x))
    ladr_ids = sorted((r for r in reqs_needing_qa if str(r).startswith("L")), key=lambda x: (len(x), x))
    parts: list[str] = []
    if jira_ids:
        parts.append(f"Jira: {', '.join(jira_ids)}")
    if ladr_ids:
        parts.append(f"LADR: {', '.join(ladr_ids)}")
    if tc_ids:
        tc_sorted = ", ".join(sorted(set(tc_ids), key=lambda x: (len(x), x)))
        parts.append(f"Test plan cases: {tc_sorted}")
    return " · ".join(parts)


def _parse_open_gaps_summary_counts(gap_summary: str | None) -> tuple[int, int]:
    """Parse ``2 High · 10 Med`` from Open gaps card summary."""
    if not gap_summary or gap_summary.strip().lower() == "none":
        return 0, 0
    high_m = re.search(r"(\d+)\s+High", gap_summary)
    med_m = re.search(r"(\d+)\s+Med", gap_summary)
    return (
        int(high_m.group(1)) if high_m else 0,
        int(med_m.group(1)) if med_m else 0,
    )


def _open_gap_card_themes(
    mapping: dict[str, Any],
    tp: dict[str, Any],
    *,
    prefetch: dict[str, Any] | None = None,
) -> list[str]:
    """High-level gap themes for condensed Open gaps card note."""
    themes: list[str] = []
    cov = tp.get("coverage") or {}
    if cov.get("uncoveredJiraRequirements") or cov.get("uncoveredLadrRequirements"):
        themes.append("Test plan gaps")

    for req in mapping.get("requirements") or []:
        code = str(req.get("codeStatus") or "").lower()
        dev = str(req.get("devTestStatus") or "").lower()
        owner = str(req.get("owner") or "").lower()
        text = str(req.get("text") or "")

        if code == "missing":
            if "Missing PR code" not in themes:
                themes.append("Missing PR code")
        elif code == "partial":
            if "Partial PR code" not in themes:
                themes.append("Partial PR code")

        if _is_qa_sit_validation_requirement(text):
            if "SIT validation" not in themes:
                themes.append("SIT validation")
        elif dev == "missing" and owner != "qa":
            if "Missing dev tests" not in themes:
                themes.append("Missing dev tests")
        elif dev == "partial" and owner in ("dev", "shared"):
            if "Partial dev tests" not in themes:
                themes.append("Partial dev tests")

    if prefetch:
        for pr in prefetch.get("prs") or []:
            checks = str(pr.get("checks") or "")
            if checks and re.search(r"\b(?:fail(?:ed|ing|ure)?|failing)\b", checks.lower()):
                if "CI failures" not in themes:
                    themes.append("CI failures")
                break

    order = [
        "Test plan gaps",
        "Missing PR code",
        "Partial PR code",
        "Missing dev tests",
        "Partial dev tests",
        "SIT validation",
        "CI failures",
    ]
    return [label for label in order if label in themes]


def _open_gap_detail_line_items(
    mapping: dict[str, Any],
    tp: dict[str, Any],
    *,
    prefetch: dict[str, Any] | None = None,
) -> list[str]:
    """Named gap bullets for Open gaps card when the gap count is small."""
    cov = tp.get("coverage") or {}
    parts: list[str] = []

    unc_j = cov.get("uncoveredJiraRequirements") or []
    unc_l = cov.get("uncoveredLadrRequirements") or []
    if unc_j:
        parts.append(f"Test plan gap — Jira {', '.join(unc_j)}")
    if unc_l:
        parts.append(f"Test plan gap — LADR {', '.join(unc_l)}")

    for req in mapping.get("requirements") or []:
        rid = str(req.get("id") or "")
        if req.get("codeStatus") == "missing":
            parts.append(f"No PR code — {rid}")
        elif req.get("devTestStatus") == "missing" and str(req.get("owner") or "").lower() != "qa":
            parts.append(f"No dev tests — {rid}")

    if prefetch:
        for pr in prefetch.get("prs") or []:
            checks = str(pr.get("checks") or "")
            if checks and re.search(r"\b(?:fail(?:ed|ing|ure)?|failing)\b", checks.lower()):
                org = pr.get("org") or ""
                repo = pr.get("repo") or ""
                num = pr.get("number")
                parts.append(f"CI failing — {org}/{repo}#{num}")
                break

    return parts


OPEN_GAPS_DETAIL_SECTION6_THRESHOLD = 5


def build_open_gaps_detail(
    mapping: dict[str, Any],
    tp: dict[str, Any],
    *,
    prefetch: dict[str, Any] | None = None,
    gap_summary: str | None = None,
) -> str:
    """One-line note under Open gaps card — names IDs/themes, not tooltip text."""
    high_n, med_n = _parse_open_gaps_summary_counts(gap_summary)
    total = high_n + med_n

    if total >= OPEN_GAPS_DETAIL_SECTION6_THRESHOLD:
        themes = _open_gap_card_themes(mapping, tp, prefetch=prefetch)
        if themes:
            return f"{', '.join(themes)} — see §6 for full list"
        return "Multiple open gaps — see §6 for full list"

    parts = _open_gap_detail_line_items(mapping, tp, prefetch=prefetch)
    if not parts:
        return "No open gaps detected"
    return " · ".join(parts[:5])


def _is_qa_sit_validation_requirement(text: str) -> bool:
    """SIT/manual validation AC — QA-owned; not scored as missing dev tests alone."""
    return bool(
        re.search(
            r"\b(validated in sit|sit validation|validate in sit|manual sit)\b",
            text or "",
            re.I,
        )
    )


def _primary_matched_file_label(matched_files: list[str]) -> str:
    for raw in matched_files or []:
        if raw and not str(raw).endswith(".json") and "samples/" not in str(raw).lower():
            name = Path(raw).name
            if name and name != "conftest.py":
                return name
    for raw in matched_files or []:
        if raw:
            return Path(raw).name
    return ""


def build_correctly_implemented_list(mapping: dict[str, Any]) -> str:
    """§6 Correctly implemented panel — Jira + LADR with implemented code in PR."""
    items: list[str] = []
    for req in mapping.get("requirements") or []:
        rid = str(req.get("id") or "")
        if not rid:
            continue
        code = str(req.get("codeStatus") or "").lower()
        if code != "implemented":
            continue
        dev = str(req.get("devTestStatus") or "").lower()
        snippet = esc((req.get("text") or "")[:100])
        source = "LADR" if rid.startswith("L") or str(req.get("source") or "") == "ladr" else "Jira"
        primary = esc(_primary_matched_file_label(list(req.get("matchedFiles") or [])))
        file_bit = f" — <code>{primary}</code>" if primary else ""
        if dev == "covered":
            detail = f"dev tests covered{file_bit}"
        elif dev == "partial":
            detail = f"code in PR; dev tests partial{file_bit}"
        else:
            detail = f"code in PR; dev tests {esc(dev.title())}{file_bit}"
        items.append(f"<li><strong>{esc(rid)}</strong> ({source}) — {snippet} — {detail}.</li>")

    if not items:
        return "<li>See requirements traceability (§5) for PR evidence.</li>"
    return "".join(items)


def build_implementation_gaps_list(
    mapping: dict[str, Any],
    tp: dict[str, Any],
    *,
    prefetch: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    """§6 Gaps panel + summary card counts (High/Med)."""
    highs: list[str] = []
    meds: list[str] = []
    seen: set[str] = set()
    cov = tp.get("coverage") or {}
    unc_j = set(cov.get("uncoveredJiraRequirements") or [])
    unc_l = set(cov.get("uncoveredLadrRequirements") or [])

    def _add(severity: str, key: str, html: str) -> None:
        if key in seen:
            return
        seen.add(key)
        (highs if severity == "high" else meds).append(html)

    for r in sorted(unc_j, key=lambda x: (len(x), x)):
        _add(
            "medium",
            f"tp:{r}",
            f'<li class="medium"><strong>{esc(r)}</strong> — no mapped test case in test plan</li>',
        )
    for r in sorted(unc_l, key=lambda x: (len(x), x)):
        _add(
            "medium",
            f"tp-l:{r}",
            f'<li class="medium"><strong>{esc(r)}</strong> — no mapped test case in test plan (LADR)</li>',
        )

    for req in mapping.get("requirements") or []:
        rid = str(req.get("id") or "")
        if not rid:
            continue
        text = str(req.get("text") or "")
        code = str(req.get("codeStatus") or "").lower()
        dev = str(req.get("devTestStatus") or "").lower()
        owner = str(req.get("owner") or "").lower()

        if code == "missing":
            _add(
                "high",
                f"code:{rid}",
                f'<li class="high"><strong>{esc(rid)}</strong> — no matching code in PR diff</li>',
            )
        elif code == "partial":
            _add(
                "medium",
                f"code-partial:{rid}",
                f'<li class="medium"><strong>{esc(rid)}</strong> — partial PR code match; review edge cases</li>',
            )

        if _is_qa_sit_validation_requirement(text):
            _add(
                "medium",
                f"sit:{rid}",
                f'<li class="medium"><strong>{esc(rid)}</strong> — SIT validation with provided test data '
                f"(QA manual; not proven by PR unit/integration tests alone)</li>",
            )
        elif dev == "missing" and owner != "qa":
            _add(
                "medium",
                f"dev:{rid}",
                f'<li class="medium"><strong>{esc(rid)}</strong> — no dev test evidence in PR</li>',
            )
        elif dev == "partial" and owner in ("dev", "shared"):
            _add(
                "medium",
                f"dev-partial:{rid}",
                f'<li class="medium"><strong>{esc(rid)}</strong> — dev tests partial in PR</li>',
            )

    if prefetch:
        for pr in prefetch.get("prs") or []:
            checks = str(pr.get("checks") or "")
            if checks and re.search(r"\b(?:fail(?:ed|ing|ure)?|failing)\b", checks.lower()):
                org = pr.get("org") or ""
                repo = pr.get("repo") or ""
                num = pr.get("number")
                _add(
                    "medium",
                    f"ci:{org}/{repo}#{num}",
                    f'<li class="medium"><strong>CI</strong> — failing checks on '
                    f"{esc(org)}/{esc(repo)}#{esc(str(num))}</li>",
                )

    gap_summary = f"{len(highs)} High · {len(meds)} Med" if highs or meds else "None"
    gap_class = "metric-fail" if highs else "metric-warn" if meds else "metric-good"
    gaps_html = "".join(highs + meds)
    return gaps_html, gap_summary, gap_class


ASSUMPTIONS_MAX_BULLETS = 3


def build_assumptions_list(mapping: dict[str, Any], tp: dict[str, Any] | None = None) -> str:
    """§7 Assumptions — at most 3 short bullets (detail lives in §5/§6)."""
    tp = tp or {}
    bullets: list[str] = []

    tp_status = str(tp.get("status") or "")
    if tp_status == "workspace_generated":
        bullets.append(
            "<li>Test plan generated locally — no execution evidence until QA runs it.</li>"
        )
    elif tp_status == "referenced_not_local":
        bullets.append(
            "<li>Test plan referenced in Jira but not found locally — coverage may be Pending.</li>"
        )

    cov = tp.get("coverage") or {}
    unc_j = [str(r) for r in cov.get("uncoveredJiraRequirements") or []]
    unc_l = [str(r) for r in cov.get("uncoveredLadrRequirements") or []]
    if unc_j or unc_l:
        parts: list[str] = []
        if unc_j:
            parts.append(f"Jira {', '.join(unc_j)}")
        if unc_l:
            parts.append(f"LADR {', '.join(unc_l)}")
        bullets.append(
            f"<li><strong>Open questions</strong> — no test plan case for {'; '.join(parts)} (see §6).</li>"
        )

    weak: list[str] = []
    for req in mapping.get("requirements") or []:
        rid = str(req.get("id") or "")
        conf = str(req.get("confidence") or "").lower()
        if rid and conf in ("low", "medium"):
            weak.append(f"{rid} ({conf})")
    if weak:
        shown = ", ".join(weak[:3])
        if len(weak) > 3:
            shown += "…"
        bullets.append(f"<li><strong>Mapping</strong> — confirm {shown} in §5.</li>")

    j_n = int(mapping.get("jiraRequirementCount") or 0)
    l_n = int(mapping.get("ladrRequirementCount") or 0)
    if l_n and j_n:
        scope = f"{j_n} Jira + {l_n} LADR"
    elif j_n:
        scope = f"{j_n} Jira"
    else:
        scope = "scored requirements"
    bullets.append(
        f"<li>Scores use PR diff token overlap ({scope}); review §5 before sign-off.</li>"
    )

    return "".join(bullets[:ASSUMPTIONS_MAX_BULLETS])


def build_qa_ownership_fields(issue_key: str, root: Path | None = None) -> dict[str, str]:
    """
    §4 Dev vs QA lists and QA scope summary from mapping + test plan.

    Requirements with QA scope **None** (dev unit/integration covered) are listed under
    dev-covered only — not in QA handoff or execute-test-plan bullets.
    """
    mapping = load_mapping_cache(issue_key, root)
    tp = load_testplan_cache(issue_key, root)
    reqs = mapping.get("requirements") or []

    dev_items: list[str] = []
    qa_items: list[str] = []
    reqs_needing_qa: set[str] = set()

    for req in reqs:
        rid = str(req.get("id") or "")
        if not rid:
            continue
        scope = str(req.get("qaScope") or "e2e")
        dev = str(req.get("devTestStatus") or "missing")
        snippet = (req.get("text") or "")[:90]
        if not _qa_scope_needs_qa_execution(scope):
            if dev == "covered":
                # §4 dev-covered list only: omit QA scope badge (incl. None); §5 traceability still shows scope.
                dev_items.append(
                    f"<li><strong>{esc(rid)}</strong> — {esc(snippet)}"
                    f" — proven by PR unit/integration tests.</li>"
                )
            continue

        reqs_needing_qa.add(rid)
        qa_items.append(
            f"<li><strong>{esc(rid)}</strong> — {esc(snippet)} — {_badge_for_qa_scope(scope)}</li>"
        )

    tc_ids: list[str] = []
    for tc in tp.get("testCases") or []:
        mapped_req_ids = [
            str(m)
            for m in (tc.get("mapped_requirements") or [])
            if str(m).startswith("R") or str(m).startswith("L")
        ]
        if not mapped_req_ids:
            continue
        if any(m in reqs_needing_qa for m in mapped_req_ids):
            tid = str(tc.get("id") or "")
            if tid:
                tc_ids.append(tid)

    if qa_items:
        if tc_ids:
            tc_sorted = ", ".join(sorted(set(tc_ids), key=lambda x: (len(x), x)))
            qa_items.append(
                f'<li class="medium">Execute attached test plan case(s) for QA-scoped requirements only: '
                f"<strong>{esc(tc_sorted)}</strong> — skip scenarios mapped only to dev-covered acceptance criteria.</li>"
            )
    else:
        qa_items.append(
            "<li>No Jira acceptance criteria require separate QA execution — "
            "dev unit/integration tests in the PR cover the scored requirements.</li>"
        )

    n_qa = len(reqs_needing_qa)
    summary = _format_qa_scope_summary(reqs, reqs_needing_qa)
    detail = _format_qa_scope_detail(reqs, reqs_needing_qa, tc_ids)

    if not dev_items:
        dev_items.append(
            "<li>See requirements traceability (§5) for dev test file evidence.</li>"
        )

    actions = build_recommended_actions_list(
        issue_key,
        mapping=mapping,
        tp=tp,
        qa_tc_ids=tc_ids,
        reqs_needing_qa=set(reqs_needing_qa),
        root=root,
    )

    return {
        "devCoveredList": "".join(dev_items),
        "qaHandoffList": "".join(qa_items),
        "qaScopeSummary": summary,
        "qaScopeDetail": detail,
        "actionsList": actions,
    }


def _actions_group_ol(items: list[str]) -> str:
    if not items:
        return "<li>None — no open items identified for this role.</li>"
    return "".join(items)


def build_recommended_actions_list(
    issue_key: str,
    *,
    mapping: dict[str, Any] | None = None,
    tp: dict[str, Any] | None = None,
    qa_tc_ids: list[str] | None = None,
    reqs_needing_qa: set[str] | None = None,
    root: Path | None = None,
) -> str:
    """§8 Recommended actions — separate Dev and QA action item lists (content only; tooltips unchanged)."""
    key = issue_key.upper()
    mapping = mapping or load_mapping_cache(key, root)
    tp = tp or load_testplan_cache(key, root)
    prefetch = load_prefetch_cache(key, root)
    jira = load_jira_cache(key, root)
    reqs = mapping.get("requirements") or []
    if reqs_needing_qa is None:
        reqs_needing_qa = {
            str(r.get("id") or "")
            for r in reqs
            if r.get("id") and _qa_scope_needs_qa_execution(str(r.get("qaScope") or "e2e"))
        }
    else:
        reqs_needing_qa = set(reqs_needing_qa)
    if qa_tc_ids is None:
        qa_tc_ids = []
        for tc in tp.get("testCases") or []:
            mapped_req_ids = [
                str(m)
                for m in (tc.get("mapped_requirements") or [])
                if str(m).startswith("R") or str(m).startswith("L")
            ]
            if any(m in reqs_needing_qa for m in mapped_req_ids):
                tid = str(tc.get("id") or "")
                if tid:
                    qa_tc_ids.append(tid)
    else:
        qa_tc_ids = list(qa_tc_ids)

    dev_actions: list[str] = []
    qa_actions: list[str] = []

    for req in reqs:
        rid = str(req.get("id") or "")
        if not rid:
            continue
        snippet = esc((req.get("text") or "")[:100])
        if req.get("codeStatus") == "missing":
            dev_actions.append(
                f"<li><strong>Implement {esc(rid)}</strong> — {snippet} — add production code in linked PR.</li>"
            )
        if req.get("devTestStatus") == "missing" and str(req.get("owner") or "") != "qa":
            dev_actions.append(
                f"<li><strong>Add dev tests for {esc(rid)}</strong> — unit or integration coverage in PR diff.</li>"
            )
        suggested = req.get("suggestedTestCases") or []
        if suggested and req.get("devTestStatus") == "missing":
            dev_actions.append(
                f"<li>Consider dev tests: {esc(', '.join(str(s) for s in suggested[:3]))}</li>"
            )

    for pr in prefetch.get("prs") or []:
        org = pr.get("org") or ""
        repo_name = pr.get("repo") or ""
        full_repo = f"{org}/{repo_name}" if org and repo_name else str(repo_name)
        number = pr.get("number")
        view = pr.get("view") or {}
        state = str(view.get("state") or "").upper()
        title = esc((view.get("title") or "")[:70])
        if state == "OPEN":
            dev_actions.append(
                f"<li><strong>Merge PR</strong> — {esc(full_repo)}#{number} (open): {title}</li>"
            )
        checks = str(pr.get("checks") or "")
        if checks and re.search(r"\b(?:fail(?:ed|ing|ure)?|failing)\b", checks.lower()):
            dev_actions.append(
                f"<li><strong>Fix CI</strong> — failing checks on {esc(full_repo)}#{number}.</li>"
            )

    if not prefetch.get("prs") and prefetch.get("branchCompare"):
        bc = prefetch.get("branchCompare") or {}
        head = bc.get("head") or "branch"
        dev_actions.append(
            f"<li><strong>Link or open a PR</strong> — changes on <code>{esc(head)}</code> only (no PR for {key}).</li>"
        )

    cov = tp.get("coverage") or {}
    for rid in cov.get("uncoveredJiraRequirements") or cov.get("uncoveredRequirements") or []:
        if str(rid).startswith("R"):
            qa_actions.append(
                f"<li><strong>Test plan gap</strong> — add case(s) for Jira {esc(rid)} in attached Excel.</li>"
            )
    for rid in cov.get("uncoveredLadrRequirements") or []:
        qa_actions.append(
            f"<li><strong>LADR gap</strong> — add case(s) for {esc(rid)} (Confluence ESS scenario).</li>"
        )

    if reqs_needing_qa:
        for rid in sorted(reqs_needing_qa, key=lambda x: (len(x), x)):
            req = next((r for r in reqs if str(r.get("id")) == rid), {})
            snippet = esc((req.get("text") or "")[:90])
            scope = str(req.get("qaScope") or "e2e")
            qa_actions.append(
                f"<li><strong>Verify {esc(rid)}</strong> — {snippet} ({esc(scope)}).</li>"
            )
        if qa_tc_ids:
            tc_sorted = ", ".join(sorted(set(qa_tc_ids), key=lambda x: (len(x), x)))
            qa_actions.append(
                f"<li><strong>Execute test plan</strong> — run {esc(tc_sorted)} for QA-scoped acceptance criteria only (see §4).</li>"
            )
    else:
        qa_actions.append(
            "<li>No separate QA execution — dev unit/integration tests cover scored acceptance criteria (§4).</li>"
        )

    if tp.get("testPlanSource") == "workspace_generated":
        qa_actions.append(
            f"<li><strong>Attach test plan on Jira</strong> — upload "
            f"<code>testcases/{key}-testcases.xlsx</code> (locally generated plan).</li>"
        )

    if tp.get("status") == "referenced_not_local":
        hint = tp.get("localSetupHint") or "Place referenced Excel under testplans/ and re-run validator."
        qa_actions.append(f"<li><strong>Test plan file missing</strong> — {esc(hint)}</li>")

    if not dev_actions:
        dev_actions.append(
            "<li>No dev code or CI actions — implementation and PR checks look complete for scored requirements.</li>"
        )

    return (
        '<div class="recommended-actions-groups">'
        '<h3 class="actions-group-title">Dev</h3>'
        f'<ol class="actions-group-list">{_actions_group_ol(dev_actions)}</ol>'
        '<h3 class="actions-group-title">QA</h3>'
        f'<ol class="actions-group-list">{_actions_group_ol(qa_actions)}</ol>'
        "</div>"
    )


def _render_trace_evidence_cell(
    matched_files: list[str],
    confidence: str,
    evidence_note: str = "",
) -> str:
    """Evidence column: file list (not truncated) + mapping confidence."""
    conf = confidence or "low"
    files = [f for f in (matched_files or []) if f]
    if not files:
        note = (evidence_note or "").strip()
        body = (
            f'<p class="evidence-note">{esc(note)}</p>'
            if note
            else '<span class="evidence-empty">—</span>'
        )
        return (
            f'<td class="evidence-cell">'
            f"{body} "
            f'<span class="conf-badge" title="Mapping confidence for cited evidence">'
            f"{esc(conf)}</span></td>"
        )
    shown = files[:6]
    items = "".join(f"<li><code>{esc(f)}</code></li>" for f in shown)
    extra = ""
    if len(files) > 6:
        extra = f'<li class="evidence-more">+{len(files) - 6} more file(s)</li>'
    return (
        f'<td class="evidence-cell">'
        f'<ul class="evidence-list">{items}{extra}</ul>'
        f'<span class="conf-badge">{esc(conf)}</span></td>'
    )


def build_req_coverage_detail(mapping: dict[str, Any]) -> str:
    """Human-readable scored-requirement count for Dev code coverage detail line."""
    j_n = int(mapping.get("jiraRequirementCount") or 0)
    l_n = int(mapping.get("ladrRequirementCount") or 0)
    total = int(mapping.get("requirementCount") or 0)
    if l_n and j_n:
        return f"{j_n} Jira + {l_n} LADR scored from PR diff mapping"
    if total:
        return f"{total} scored from PR diff mapping"
    return "0 scored from PR diff mapping"


def _render_requirement_type_badge(req: dict[str, Any]) -> str:
    """Type badge on every §5 row — FR / NFR / Process (content only; no new table column)."""
    from map_requirements_to_diff import resolve_requirement_type

    rtype, cat = resolve_requirement_type(req)
    if rtype == "non_functional":
        title = f"Non-functional ({cat.replace('_', ' ')})" if cat else "Non-functional"
        return f' <span class="badge badge-nfr" title="{esc(title)}">NFR</span>'
    if rtype == "process":
        return (
            ' <span class="badge badge-na" title="Process or documentation requirement">Process</span>'
        )
    return ' <span class="badge badge-fr" title="Functional requirement">FR</span>'


def render_requirement_rows_from_mapping(issue_key: str, root: Path | None = None) -> str:
    mapping = load_mapping_cache(issue_key, root)
    rows = []
    for req in mapping.get("requirements") or []:
        rid = req.get("id", "")
        conf = req.get("confidence", "low")
        evidence = _render_trace_evidence_cell(
            req.get("matchedFiles") or [],
            conf,
            str(req.get("evidenceNote") or ""),
        )
        id_cell = esc(rid)
        if str(req.get("source") or "") == "ladr" or str(rid).startswith("L"):
            id_cell = f'{id_cell} <span class="badge badge-shared">LADR</span>'
        id_cell += _render_requirement_type_badge(req)
        rows.append(
            f"<tr>"
            f"<td>{id_cell}</td>"
            f"<td>{esc(req.get('text', ''))}</td>"
            f"<td>{_badge_for_status(req.get('codeStatus', 'missing'))}</td>"
            f"<td>{_badge_for_status(req.get('devTestStatus', 'missing'), 'dev')}</td>"
            f'<td><span class="badge badge-dev">{esc(str(req.get("owner", "shared")).title())}</span></td>'
            f"<td>{_badge_for_qa_scope(str(req.get('qaScope', 'e2e')))}</td>"
            f"{evidence}"
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
        f'<div class="label-row"><div class="label">Release readiness score</div>'
        f'{metric_info_icon_html("Release readiness score")}</div>'
        f'<div class="metric-value">{score}%</div>'
        f'<div class="note">Weighted: dev code, dev tests, test plan, gaps</div>'
        f"</div>"
    )


def render_testplan_rows(
    test_cases: list[dict[str, Any]],
    jira_requirements: list[dict[str, str]] | None = None,
    *,
    generated_local: bool = False,
) -> str:
    rows = []
    for tc in test_cases:
        steps = tc.get("steps") or {}
        section = tc.get("section") or ""
        summary = tc.get("summary") or ""
        scenario = f"{section} · {summary}" if section and summary else (section or summary or tc.get("id", ""))
        ev = evidence_type_badges(tc) + render_testplan_evidence(
            tc,
            jira_requirements,
            generated_local=generated_local,
        )
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
        "Weighted composite score (0–100%) combining dev code coverage, "
        "dev unit/integration test coverage, test plan acceptance criteria coverage, "
        "and open-gap severity from the review (higher is better)."
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
    "and LADR Confluence (only when a LADR or design-requirements page is linked)."
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

TRACE_SECTION_LEAD_INFO = (
    "Per-requirement mapping from Jira acceptance criteria (R1, R2, …) to branch/PR code, "
    "dev unit/integration tests, Dev vs QA ownership, QA scope, and file-level evidence."
)

LADR_SECTION_LEAD_INFO = (
    "Summary of how many Confluence LADR requirements (L1, L2, …) are covered by test cases "
    "in the attached Excel plan, with links to the source design page when available."
)

LEAD_PARAGRAPH_INFO: dict[str, tuple[str, str]] = {
    "trace-section-lead": ("Requirements traceability intro", TRACE_SECTION_LEAD_INFO),
    "ladr-section-lead": ("LADR traceability summary", LADR_SECTION_LEAD_INFO),
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
      left: 50%; right: auto; top: calc(100% + 10px);
      transform: translateX(-50%);
      width: min(340px, calc(100vw - 2.5rem));
      max-width: 340px;
      min-width: 12rem;
      height: auto;
      max-height: none;
      overflow: visible;
      padding: 0.75rem 0.85rem;
      background: #0f172a; color: #e2e8f0;
      font-size: 0.72rem; font-weight: 400;
      text-transform: none; letter-spacing: normal;
      border-radius: 8px; box-shadow: 0 8px 20px rgba(15,23,42,0.32);
      transition: opacity 0.15s ease, visibility 0.15s ease;
      pointer-events: none;
      white-space: normal;
      text-align: left;
      box-sizing: border-box;
    }
    .metric-info-tooltip .tooltip-title {
      display: block;
      font-weight: 600;
      font-size: 0.75rem;
      color: #f8fafc;
      margin: 0 0 0.55rem;
      padding: 0 0 0.55rem 0;
      border-bottom: 1px solid rgba(248,250,252,0.22);
      line-height: 1.35;
    }
    .metric-info-tooltip .tooltip-body {
      display: block;
      color: #cbd5e1;
      line-height: 1.55;
      margin: 0;
      padding: 0.1rem 0 0;
    }
    th:last-child .metric-info-tooltip,
    th:nth-last-child(2) .metric-info-tooltip {
      left: auto;
      right: calc(100% + 10px);
      top: 50%;
      bottom: auto;
      transform: translateY(-50%);
    }
    th:nth-last-child(-n+2) .metric-info-tip {
      position: relative;
    }
    /* Description on hover (or keyboard focus) */
    .metric-info-tip:hover .metric-info-tooltip,
    .metric-info-tip:focus .metric-info-tooltip,
    .metric-info-tip:focus-within .metric-info-tooltip {
      visibility: visible; opacity: 1; pointer-events: auto;
    }
    .trace-section-lead-with-tip,
    .ladr-section-lead-with-tip {
      position: relative;
      padding-right: 2rem;
      margin-bottom: 0.75rem;
    }
    .trace-section-lead-with-tip .metric-info-tip,
    .ladr-section-lead-with-tip .metric-info-tip {
      position: absolute;
      top: 0.1rem;
      right: 0;
    }
    .trace-section-lead-with-tip .metric-info-tip > .metric-info-tooltip,
    .ladr-section-lead-with-tip .metric-info-tip > .metric-info-tooltip {
      left: 50%;
      right: auto;
      transform: translateX(-50%);
      top: calc(100% + 10px);
    }
"""

METRIC_INFO_CLICK_JS_MARKER = "/* metric-info-tip click toggle */"
METRIC_INFO_CLICK_JS = """
    """ + METRIC_INFO_CLICK_JS_MARKER + """
    (function () {
      function closeAll(except) {
        document.querySelectorAll('.metric-info-tip.is-open').forEach(function (t) {
          if (t !== except) {
            t.classList.remove('is-open');
            t.setAttribute('aria-expanded', 'false');
          }
        });
      }
      document.querySelectorAll('.metric-info-tip').forEach(function (tip) {
        if (!tip.getAttribute('aria-expanded')) tip.setAttribute('aria-expanded', 'false');
        tip.addEventListener('click', function (e) {
          e.stopPropagation();
          var open = tip.classList.toggle('is-open');
          tip.setAttribute('aria-expanded', open ? 'true' : 'false');
          closeAll(open ? tip : null);
          if (open) tip.focus();
        });
        tip.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            var open = tip.classList.toggle('is-open');
            tip.setAttribute('aria-expanded', open ? 'true' : 'false');
            closeAll(open ? tip : null);
          }
          if (e.key === 'Escape') {
            tip.classList.remove('is-open');
            tip.setAttribute('aria-expanded', 'false');
          }
        });
      });
      document.addEventListener('click', function (e) {
        if (!e.target.closest('.metric-info-tip')) closeAll(null);
      });
    })();
"""

TOOLTIP_LAYOUT_FIX_MARKER = "/* tooltip layout fix v22 — group titles open below, right-aligned to icon */"

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
      position: relative !important;
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
    header,
    header .meta,
    header .cache-meta,
    header .quick-links,
    header .jira-readiness-block,
    header .verdict {
      overflow: visible !important;
      position: relative;
    }
    .metric-info-tip {
      position: relative !important;
      vertical-align: middle;
    }
    .metric-info-tip > .metric-info-tooltip {
      z-index: 500 !important;
      left: 50% !important;
      right: auto !important;
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      transform: translateX(-50%) !important;
      width: min(300px, calc(100vw - 2rem)) !important;
      max-width: 300px !important;
      min-width: 12rem;
      padding: 0.75rem 0.85rem !important;
      white-space: normal !important;
      word-wrap: break-word !important;
      overflow-wrap: break-word !important;
      box-sizing: border-box !important;
    }
    .metric-info-tooltip .tooltip-title {
      margin-bottom: 0.55rem !important;
      padding-bottom: 0.55rem !important;
      line-height: 1.35 !important;
    }
    .metric-info-tooltip .tooltip-body {
      line-height: 1.55 !important;
      padding-top: 0.1rem !important;
    }
    .metric-info-tip:hover,
    .metric-info-tip:focus-within {
      z-index: 600 !important;
    }
    .heading-label-row,
    .group-title-row,
    .label-row,
    .th-label-row,
    .split-metric-with-tip {
      position: relative;
      overflow: visible !important;
    }
    .section-head .heading-label-row,
    header h1 .heading-label-row {
      display: inline-flex !important;
      align-items: center !important;
      gap: 0.35rem !important;
      flex-wrap: wrap !important;
    }
    /* Header / meta lines: icon at line start — center transform clips text off the left */
    header .cache-meta-with-tip,
    header .quick-links-with-tip,
    header .meta,
    header .verdict,
    .jira-readiness-block .readiness-item,
    .split-metric-with-tip,
    .note-box-with-tip {
      overflow: visible !important;
      position: relative;
    }
    header .cache-meta-with-tip .metric-info-tip,
    header .quick-links-with-tip .metric-info-tip,
    header .meta .metric-info-tip,
    header .verdict .metric-info-tip,
    .jira-readiness-block .readiness-item .metric-info-tip,
    .split-metric-with-tip .metric-info-tip,
    .note-box-with-tip .metric-info-tip {
      position: static !important;
    }
    header .cache-meta-with-tip .metric-info-tip > .metric-info-tooltip,
    header .quick-links-with-tip .metric-info-tip > .metric-info-tooltip,
    header .meta .metric-info-tip > .metric-info-tooltip,
    header .verdict .metric-info-tip > .metric-info-tooltip,
    .jira-readiness-block .readiness-item .metric-info-tip > .metric-info-tooltip,
    .split-metric-with-tip .metric-info-tip > .metric-info-tooltip,
    .note-box-with-tip .metric-info-tip > .metric-info-tooltip {
      left: 0 !important;
      right: auto !important;
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      transform: none !important;
      z-index: 850 !important;
      width: min(360px, calc(100vw - 2rem)) !important;
      max-width: 360px !important;
    }
    header .cache-meta-with-tip:has(.metric-info-tip:hover),
    header .quick-links-with-tip:has(.metric-info-tip:hover),
    header .meta:has(.metric-info-tip:hover),
    header:has(.cache-meta-with-tip .metric-info-tip:hover),
    header:has(.quick-links-with-tip .metric-info-tip:hover) {
      z-index: 400 !important;
      overflow: visible !important;
    }
    /* §1–§8 section banners: tooltip above h2 (below was hidden under section-body) */
    .report-section .section-head {
      position: relative !important;
      z-index: 8 !important;
      overflow: visible !important;
    }
    .report-section .section-head h2 {
      overflow: visible !important;
      position: relative !important;
    }
    .report-section .section-body {
      position: relative !important;
      z-index: 1 !important;
    }
    .report-section .section-head:has(.metric-info-tip:hover),
    .report-section .section-head:has(.metric-info-tip:focus-within) {
      z-index: 900 !important;
      overflow: visible !important;
    }
    .report-section .section-head .heading-label-row {
      position: relative !important;
      overflow: visible !important;
    }
    .report-section .section-head .heading-label-row .metric-info-tip {
      position: static !important;
    }
    .report-section .section-head .heading-label-row .metric-info-tip > .metric-info-tooltip {
      top: auto !important;
      bottom: calc(100% + 10px) !important;
      left: 0 !important;
      right: auto !important;
      transform: none !important;
      z-index: 950 !important;
    }
    .report-section .section-head .metric-info-tip:hover,
    .report-section .section-head .metric-info-tip:focus-within {
      z-index: 960 !important;
    }
    /* Last two columns (e.g. QA scope + Evidence): open to the left of header */
    /* First table column: centered tooltip clips off the left edge of the grid */
    thead th:first-child .th-label-row,
    th:first-child .th-label-row {
      position: relative !important;
      overflow: visible !important;
    }
    thead th:first-child .metric-info-tip,
    th:first-child .metric-info-tip {
      position: static !important;
    }
    thead th:first-child .metric-info-tip > .metric-info-tooltip,
    th:first-child .metric-info-tip > .metric-info-tooltip {
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      left: 0 !important;
      right: auto !important;
      transform: none !important;
      z-index: 600 !important;
    }
    th:nth-last-child(-n+2) .metric-info-tip > .metric-info-tooltip {
      top: 50% !important;
      bottom: auto !important;
      left: auto !important;
      right: calc(100% + 10px) !important;
      transform: translateY(-50%) !important;
      max-width: min(320px, calc(100vw - 2rem)) !important;
      width: min(320px, calc(100vw - 2rem)) !important;
    }
    th:last-child .metric-info-tip:hover,
    th:nth-last-child(2) .metric-info-tip:hover,
    th:last-child .metric-info-tip:focus-within,
    th:nth-last-child(2) .metric-info-tip:focus-within {
      z-index: 350 !important;
    }
    .section-testplan .table-wrap,
    .section-trace .table-wrap {
      overflow-x: auto !important;
      overflow-y: visible !important;
      padding-top: 0.75rem;
      margin-bottom: 1rem;
    }
    .section-testplan table,
    .section-trace table.trace-table,
    .section-trace .table-wrap > table {
      overflow: visible !important;
    }
    .section-trace thead,
    .section-testplan thead {
      position: relative;
      z-index: 2;
    }
    .section-trace .section-head h2,
    .section-trace .section-head .heading-label-row {
      color: #fff !important;
      text-shadow: 0 1px 2px rgba(0,0,0,0.15);
    }
    /* Metric cards: label-row tooltips must paint above .metric-value / .note (sibling below in DOM) */
    .metric-card {
      overflow: visible !important;
    }
    .metric-card .metric-value,
    .metric-card .note {
      position: relative;
      z-index: 0;
    }
    .metric-card .label-row {
      position: relative;
      z-index: 2;
    }
    .metric-card:has(.label-row .metric-info-tip:hover) .label-row,
    .metric-card:has(.label-row .metric-info-tip:focus-within) .label-row {
      z-index: 100 !important;
    }
    /* Metric / summary grids: row-anchored tooltips (fixes first grid column left clip) */
    .metric-grid,
    .summary-grid,
    .summary-groups {
      overflow: visible !important;
    }
    .metric-card .label-row {
      position: relative !important;
      overflow: visible !important;
      z-index: 2;
    }
    .metric-card:has(.label-row .metric-info-tip:hover),
    .metric-card:has(.label-row .metric-info-tip:focus-within) {
      z-index: 50 !important;
    }
    .metric-card .label-row .metric-info-tip {
      position: static !important;
      flex-shrink: 0;
    }
    .metric-card .label-row .metric-info-tip > .metric-info-tooltip {
      top: auto !important;
      bottom: calc(100% + 10px) !important;
      left: 0 !important;
      right: auto !important;
      transform: none !important;
      z-index: 800 !important;
      width: min(340px, calc(100vw - 2rem)) !important;
      max-width: 340px !important;
      min-width: 12rem;
      height: auto !important;
      max-height: none !important;
      overflow: visible !important;
    }
    .metric-card .label-row .metric-info-tip:hover,
    .metric-card .label-row .metric-info-tip:focus-within {
      z-index: 850 !important;
    }
    /* Summary group titles (Implementation & tests, …): open below — flip-up was clipped under release score */
    .summary-group-title {
      overflow: visible !important;
      position: relative;
    }
    .summary-group-title .group-title-row {
      position: relative !important;
      overflow: visible !important;
      z-index: 2;
    }
    .summary-group-title:has(.metric-info-tip:hover),
    .summary-group-title:has(.metric-info-tip:focus-within) {
      z-index: 120 !important;
    }
    .summary-group-title .group-title-row .metric-info-tip {
      position: static !important;
      flex-shrink: 0;
    }
    .summary-group-title .group-title-row .metric-info-tip > .metric-info-tooltip {
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      left: auto !important;
      right: 0 !important;
      transform: none !important;
      z-index: 900 !important;
      width: min(340px, calc(100vw - 2rem)) !important;
      max-width: 340px !important;
      min-width: 12rem;
      height: auto !important;
      max-height: none !important;
      overflow: visible !important;
    }
    .summary-group-title .group-title-row .metric-info-tip:hover,
    .summary-group-title .group-title-row .metric-info-tip:focus-within {
      z-index: 910 !important;
    }
    .summary-groups > div:first-child .summary-group-title:has(.metric-info-tip:hover),
    .summary-groups > div:first-child .summary-group-title:has(.metric-info-tip:focus-within) {
      z-index: 200 !important;
    }
    /* Review panel h3 titles (same row layout as metric labels) */
    .review-panel h3 .heading-label-row {
      position: relative !important;
      overflow: visible !important;
    }
    .review-panel h3 .heading-label-row .metric-info-tip {
      position: static !important;
    }
    .review-panel h3 .heading-label-row .metric-info-tip > .metric-info-tooltip {
      top: auto !important;
      bottom: calc(100% + 10px) !important;
      left: 0 !important;
      right: auto !important;
      transform: none !important;
      z-index: 700 !important;
    }
    /* Release readiness: wider tooltip + stack above §1 body */
    .release-score-row,
    .release-score-card {
      overflow: visible !important;
      position: relative;
    }
    .release-score-row {
      margin-bottom: 1.5rem;
      z-index: 12 !important;
    }
    .section-summary:has(.release-score-card .metric-info-tip:hover) .section-body,
    .section-summary:has(.release-score-card .metric-info-tip:focus-within) .section-body {
      z-index: 30 !important;
    }
    .release-score-card .label-row .metric-info-tip > .metric-info-tooltip {
      width: min(360px, calc(100vw - 2.5rem)) !important;
      max-width: 360px !important;
      min-width: 18rem;
      z-index: 1200 !important;
    }
    .release-score-card:has(.metric-info-tip:hover),
    .release-score-card:has(.metric-info-tip:focus-within),
    .release-score-row:has(.metric-info-tip:hover),
    .release-score-row:has(.metric-info-tip:focus-within) {
      z-index: 995 !important;
    }
"""

OWNERSHIP_TOOLTIP_CSS_MARKER = "/* ownership section tooltips v3 */"

OWNERSHIP_TOOLTIP_CSS = """
    """ + OWNERSHIP_TOOLTIP_CSS_MARKER + """
    .section-ownership,
    .section-ownership .section-head,
    .section-ownership .section-body,
    .section-ownership .metric-grid,
    .section-ownership .metric-card {
      overflow: visible !important;
    }
    .section-ownership .section-head {
      position: relative;
      z-index: 5;
    }
    .section-ownership .section-head:has(.metric-info-tip:hover),
    .section-ownership .section-head:has(.metric-info-tip:focus-within) {
      z-index: 500 !important;
    }
    .section-ownership .section-head .metric-info-tip > .metric-info-tooltip {
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      left: 50% !important;
      right: auto !important;
      transform: translateX(-50%) !important;
      z-index: 501 !important;
    }
    .section-ownership .section-body {
      position: relative;
      z-index: 1;
    }
    .section-ownership .section-lead-with-tip {
      display: block !important;
      position: relative;
      overflow: visible !important;
      padding-right: 2.25rem;
      margin-bottom: 1.25rem;
    }
    .section-ownership .section-lead-with-tip .metric-info-tip {
      position: absolute;
      top: 0.65rem;
      right: 0.75rem;
      margin: 0;
    }
    .section-ownership .section-lead-with-tip .metric-info-tip > .metric-info-tooltip {
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      left: 50% !important;
      right: auto !important;
      transform: translateX(-50%) !important;
      z-index: 400 !important;
    }
    .section-ownership .section-lead-with-tip .metric-info-tip:hover,
    .section-ownership .section-lead-with-tip .metric-info-tip:focus-within {
      z-index: 450 !important;
    }
    .section-ownership .metric-grid {
      padding-top: 0.25rem;
      position: relative;
      align-items: start;
    }
    .section-ownership .metric-card {
      position: relative;
      isolation: isolate;
    }
    .section-ownership .metric-card:has(.label-row .metric-info-tip:hover),
    .section-ownership .metric-card:has(.label-row .metric-info-tip:focus-within) {
      z-index: 40 !important;
    }
    /* §4 metric cards use global row-anchored tooltips (v21) */
    .ladr-section-lead {
      color: #475569;
      font-size: 0.875rem;
      margin: 0 0 0.75rem;
      line-height: 1.45;
    }
"""

OWNERSHIP_TOOLTIP_CSS_BLOCK_RE = re.compile(
    r"\s*/\* ownership section tooltips v\d+ \*/[\s\S]*?"
    r"(?=\n\s*(?:/\* trace section visibility|\s*</style>))",
    re.MULTILINE,
)

TOOLTIP_LAYOUT_FIX_BLOCK_RE = re.compile(
    r"\s*/\* tooltip layout fix(?: v\d+)? — prevent clipping in panels and sections \*/[\s\S]*?"
    r"(?=\n\s*</style>)",
    re.MULTILINE,
)

TRACE_SECTION_CSS_MARKER = "/* trace section visibility v2 */"

TRACE_SECTION_CSS = """
    """ + TRACE_SECTION_CSS_MARKER + """
    .section-trace { border: 2px solid #8b5cf6 !important; }
    .section-trace .section-head { background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 100%) !important; }
    .section-trace .section-head h2,
    .section-trace .section-head .heading-label-row { color: #fff !important; text-shadow: 0 1px 2px rgba(0,0,0,0.12); }
    .section-trace .section-body {
      padding: 1.25rem 1.5rem 1.5rem !important;
      background: linear-gradient(180deg, #faf5ff 0%, #fff 100%) !important;
    }
    .section-trace .trace-section-lead {
      color: #4c1d95;
      font-size: 0.875rem;
      margin-bottom: 1rem;
      padding: 0.65rem 0.9rem;
      background: #ede9fe;
      border-left: 3px solid #7c3aed;
      border-radius: 0 6px 6px 0;
      line-height: 1.5;
    }
    .section-trace .table-wrap {
      padding: 0.5rem 0 0 !important;
      overflow-y: visible !important;
      margin-bottom: 1rem;
    }
    .section-trace table.trace-table,
    .section-trace .table-wrap > table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      border: 1px solid #c4b5fd;
      border-radius: 8px;
      overflow: visible;
      font-size: 0.9rem;
      background: #fff;
    }
    .section-trace table th {
      background: #ede9fe !important;
      color: #4c1d95 !important;
      font-weight: 700;
      padding: 0.7rem 0.75rem !important;
      border-bottom: 2px solid #c4b5fd !important;
    }
    .section-trace table td {
      color: #1e293b !important;
      vertical-align: top;
      padding: 0.7rem 0.75rem !important;
      border-bottom: 1px solid #ede9fe !important;
      line-height: 1.45;
    }
    .section-trace tbody tr:nth-child(even) td { background: #faf5ff; }
    .section-trace tbody tr:hover td { background: #f5f3ff; }
    .section-trace td:first-child { font-weight: 700; color: #6d28d9 !important; white-space: nowrap; }
    .section-trace td:nth-child(2) { min-width: 200px; max-width: 340px; }
    .section-trace td.evidence-cell { min-width: 180px; max-width: 320px; }
    .section-trace .evidence-list {
      margin: 0.25rem 0 0.35rem;
      padding-left: 1.15rem;
      font-size: 0.8rem;
      list-style: disc;
    }
    .section-trace .evidence-list code {
      font-size: 0.78rem;
      word-break: break-word;
      white-space: normal;
      background: #f1f5f9;
      padding: 0.1rem 0.25rem;
      border-radius: 3px;
    }
    .section-trace .evidence-empty { color: #94a3b8; }
    .section-trace .evidence-note {
      font-size: 0.78rem;
      color: #475569;
      margin: 0 0 0.35rem;
      line-height: 1.4;
    }
    .section-trace .conf-badge {
      font-size: 0.72rem;
      color: #64748b;
      font-style: italic;
    }
    .badge-nfr { background: #fef3c7; color: #92400e; }
    .badge-fr { background: #ecfdf5; color: #047857; }
"""

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
    .jira-readiness-block ul { list-style: none; padding: 0; margin: 0.5rem 0 0; }
    .jira-readiness-block .readiness-item {
      display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.4rem 0; line-height: 1.45;
    }
    .jira-readiness-block .readiness-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 1.4rem; height: 1.4rem; border-radius: 50%;
      font-weight: 700; font-size: 0.8rem; line-height: 1; flex-shrink: 0; margin-top: 0.05rem;
    }
    .readiness-item.ready-ok .readiness-icon {
      color: var(--pass); background: var(--pass-bg); border: 1px solid var(--pass-border);
    }
    .readiness-item.ready-missing .readiness-icon,
    .readiness-item.ready-warn .readiness-icon {
      color: var(--fail); background: var(--fail-bg); border: 1px solid var(--fail-border);
    }
    .split-metric-with-tip { display: inline-flex; align-items: center; gap: 0.2rem; vertical-align: middle; }
"""

JIRA_READINESS_UI_MARKER = "/* jira readiness status icons */"

JIRA_READINESS_UI_CSS = """
    """ + JIRA_READINESS_UI_MARKER + """
    .jira-readiness-block ul { list-style: none; padding: 0; margin: 0.5rem 0 0; }
    .jira-readiness-block .readiness-item {
      display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.4rem 0; line-height: 1.45;
    }
    .jira-readiness-block .readiness-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 1.4rem; height: 1.4rem; border-radius: 50%;
      font-weight: 700; font-size: 0.8rem; line-height: 1; flex-shrink: 0; margin-top: 0.05rem;
    }
    .readiness-item.ready-ok .readiness-icon {
      color: var(--pass); background: var(--pass-bg); border: 1px solid var(--pass-border);
    }
    .readiness-item.ready-missing .readiness-icon,
    .readiness-item.ready-warn .readiness-icon {
      color: var(--fail); background: var(--fail-bg); border: 1px solid var(--fail-border);
    }
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
    "Evidence": (
        "Changed file paths (or commit message) supporting the code/dev-test assessment. "
        "Confidence: high = matched files; medium/low = keyword-only in diff/commits with no path hit."
    ),
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
    title = f"About {label}"
    return (
        f'<span class="metric-info-tip" tabindex="0" role="button" '
        f'aria-label="{esc(title)}">'
        f'<span class="metric-info-icon" aria-hidden="true">i</span>'
        f'<span class="metric-info-tooltip" role="tooltip">'
        f'<span class="tooltip-title">{esc(title)}</span>'
        f'<span class="tooltip-body">{esc(text)}</span></span></span>'
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
    if f'aria-label="About {esc(title)}"' in html:
        return html
    if f'<span class="heading-label-row">{esc(title)}' in html:
        return html
    if f'<span class="heading-label-row">{title}' in html:
        return html
    icon = metric_info_icon_html(title, tip)
    inner = f'<span class="heading-label-row">{title}{icon}</span>'
    wrapped = f"<{tag}>{inner}</{tag}>"
    for plain in (f"<{tag}>{title}</{tag}>", f"<{tag}>{esc(title)}</{tag}>"):
        if plain in html:
            return html.replace(plain, wrapped, 1)
    pattern = (
        rf'(<div class="section-head">[\s\S]*?<{tag}>)\s*'
        rf'{re.escape(title)}\s*'
        rf'(</{tag}>)'
    )
    if re.search(pattern, html):
        return re.sub(pattern, rf"\1{inner}\2", html, count=1)
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
    """Report h1 title is intentionally without an info tooltip."""
    if 'aria-label="About Report title"' in html:
        html = re.sub(
            r"<h1><span class=\"heading-label-row\">([\s\S]*?)"
            r"<span class=\"metric-info-tip\"[\s\S]*?</span></span></h1>",
            r"<h1>\1</h1>",
            html,
            count=1,
        )
    return html


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
    """Checklist item tooltips only; Jira input readiness h3 heading has no tooltip."""
    for title in READINESS_PANEL_INFO:
        if f'aria-label="About {title}"' in html:
            html = re.sub(
                rf"<h3><span class=\"heading-label-row\">{re.escape(title)}"
                r"<span class=\"metric-info-tip\"[\s\S]*?</span></span></h3>",
                f"<h3>{title}</h3>",
                html,
                count=1,
            )
    for label, tip in READINESS_ITEM_INFO.items():
        marker = f'<strong>{label}</strong>{metric_info_icon_html(label, tip)}'
        if marker in html:
            continue
        plain = f"<strong>{label}</strong>"
        if plain in html:
            html = html.replace(plain, marker, 1)
    return html


def inject_note_box_tooltip(html: str) -> str:
    if 'aria-label="About Test plan source"' in html:
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


def _normalize_ladr_section_lead(html: str) -> str:
    """LADR block in §3 must not use section-lead (reserved for §4 ownership intro)."""
    html = re.sub(
        r'(<div class="review-panel review-info ladr-trace-block"[\s\S]*?<h3>[^<]*</h3>\s*)'
        r'<p class="section-lead section-lead-with-tip">'
        r'<span class="metric-info-tip" tabindex="0" role="button" aria-label="About Dev vs QA ownership">'
        r'<span class="metric-info-icon" aria-hidden="true">i</span>'
        r'<span class="metric-info-tooltip">[^<]*</span></span>\s*',
        r'\1<p class="ladr-section-lead">',
        html,
        count=1,
    )
    return re.sub(
        r'(<div class="review-panel review-info ladr-trace-block"[\s\S]*?<h3>[^<]*</h3>\s*)'
        r'<p class="section-lead">',
        r'\1<p class="ladr-section-lead">',
        html,
        count=1,
    )


def _normalize_ownership_section_lead_icon(html: str) -> str:
    """Move §4 lead info icon to end of callout (v1 injected it at the start)."""
    icon = metric_info_icon_html("Dev vs QA ownership", SECTION_LEAD_INFO)
    lead_tip_re = (
        r'<span class="metric-info-tip" tabindex="0" role="button" '
        r'aria-label="About Dev vs QA ownership">'
        r'<span class="metric-info-icon" aria-hidden="true">i</span>'
        r'<span class="metric-info-tooltip">[^<]*</span></span>'
    )
    pattern = (
        r'(<section class="report-section section-ownership">[\s\S]*?)'
        r'<p class="section-lead section-lead-with-tip">\s*'
        + lead_tip_re
        + r'\s*([\s\S]*?)</p>'
    )

    def _repl(m: re.Match[str]) -> str:
        body = re.sub(r"\s+", " ", m.group(2).strip())
        return f'{m.group(1)}<p class="section-lead section-lead-with-tip">{body} {icon}</p>'

    return re.sub(pattern, _repl, html, count=1, flags=re.DOTALL)


def inject_lead_paragraph_tooltips(html: str) -> str:
    """Standard info icon on §3 LADR and §5 trace intro paragraphs."""
    for css_class, (label, tip) in LEAD_PARAGRAPH_INFO.items():
        aria = f'aria-label="About {esc(label)}"'
        if aria in html:
            continue
        pattern = rf'(<p class="{re.escape(css_class)}">)([\s\S]*?)(</p>)'
        match = re.search(pattern, html)
        if not match:
            continue
        body = match.group(2).strip()
        icon = metric_info_icon_html(label, tip)
        replacement = (
            f'<p class="{css_class} {css_class}-with-tip">{body} {icon}</p>'
        )
        html = html[: match.start()] + replacement + html[match.end() :]
    return html


def inject_section_lead_tooltip(html: str) -> str:
    """Tooltip on §4 ownership intro only (not LADR lead in §3)."""
    html = _normalize_ownership_section_lead_icon(html)
    if re.search(
        r'<section class="report-section section-ownership">[\s\S]*?'
        r'<p class="section-lead section-lead-with-tip">',
        html,
    ):
        return html
    icon = metric_info_icon_html("Dev vs QA ownership", SECTION_LEAD_INFO)
    pattern = (
        r'(<section class="report-section section-ownership">[\s\S]*?)'
        r'<p class="section-lead">([\s\S]*?)</p>'
    )
    if not re.search(pattern, html, flags=re.DOTALL):
        return html
    return re.sub(
        pattern,
        rf'\1<p class="section-lead section-lead-with-tip">\2 {icon}</p>',
        html,
        count=1,
        flags=re.DOTALL,
    )


def inject_ownership_tooltip_styles(html: str) -> str:
    """§4 Dev vs QA ownership tooltip layout (idempotent; upgrades v1 → v2)."""
    if OWNERSHIP_TOOLTIP_CSS_MARKER in html:
        return html
    html = OWNERSHIP_TOOLTIP_CSS_BLOCK_RE.sub("", html)
    return html.replace("</style>", OWNERSHIP_TOOLTIP_CSS + "\n  </style>", 1)


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


TRACE_SECTION_CSS_BLOCK_RE = re.compile(
    r"\s*/\* trace section visibility v\d+ \*/[\s\S]*?"
    r"(?=\n\s*(?:/\* tooltip layout fix|\s*</style>))",
    re.MULTILINE,
)


def inject_trace_section_styles(html: str) -> str:
    """Stronger §5 Requirements traceability layout (idempotent; upgrades v1 → v2)."""
    if TRACE_SECTION_CSS_MARKER in html:
        return html
    html = TRACE_SECTION_CSS_BLOCK_RE.sub("", html)
    return html.replace("</style>", TRACE_SECTION_CSS + "\n  </style>", 1)


def inject_trace_section_markup(html: str) -> str:
    """Add section lead and trace-table class when template is legacy."""
    if "trace-section-lead" not in html and 'class="report-section section-trace"' in html:
        html = re.sub(
            r'(<section class="report-section section-trace">.*?<div class="section-body">)\s*'
            r'(<div class="table-wrap">)',
            r'\1\n        <p class="trace-section-lead">Per-requirement mapping from Jira acceptance criteria '
            r"and linked Confluence LADR (when present) to branch/PR code, dev tests, ownership, "
            r"and file-level evidence.</p>\n        \2",
            html,
            count=1,
            flags=re.DOTALL,
        )
    if 'class="trace-table"' not in html:
        html = re.sub(
            r'(<section class="report-section section-trace">.*?<div class="table-wrap">\s*)<table>',
            r'\1<table class="trace-table">',
            html,
            count=1,
            flags=re.DOTALL,
        )
    return html


def _strip_modern_tooltip_layout_fix(html: str) -> str:
    """Remove tooltip layout fix v4+ block so v20 can replace v19."""
    return re.sub(
        r"\s*/\* tooltip layout fix v\d+[^*]*\*/[\s\S]*?"
        r"(?=\n\s*/\* ownership section tooltips|\n\s*/\* trace section visibility|\n\s*</style>)",
        "\n",
        html,
        count=1,
    )


def inject_tooltip_layout_fix(html: str) -> str:
    """Ensure tooltip CSS avoids overflow clipping (idempotent; upgrades v1–v19 → v20)."""
    html = html.replace("cursor: help;", "cursor: pointer;")
    html = _strip_legacy_tooltip_layout_fix(html)
    html = TOOLTIP_LAYOUT_FIX_BLOCK_RE.sub("", html)
    html = _strip_modern_tooltip_layout_fix(html)
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


def inject_metric_info_click_script(html: str) -> str:
    """Click (or tap) the i icon toggles the definition callout; Escape / outside click closes."""
    if METRIC_INFO_CLICK_JS_MARKER in html:
        return html
    script = f"  <script>{METRIC_INFO_CLICK_JS}\n  </script>"
    if "</body>" in html:
        return html.replace("</body>", f"{script}\n  </body>", 1)
    return html + script


def normalize_jira_readiness_icons(html: str) -> str:
    """Green ✓ when input present; red ✗ when missing (upgrades legacy ! / ready-warn)."""
    if "jira-readiness-block" not in html:
        return html
    html = html.replace('class="readiness-item ready-warn"', 'class="readiness-item ready-missing"')
    html = re.sub(
        r'(<li class="readiness-item ready-missing">)\s*'
        r'<span class="readiness-icon"[^>]*>!</span>',
        r'\1<span class="readiness-icon" aria-hidden="true">✗</span>',
        html,
        flags=re.I,
    )
    html = re.sub(
        r'(<li class="readiness-item ready-ok">)\s*'
        r'<span class="readiness-icon"(?![^>]*aria-hidden)[^>]*>',
        r'\1<span class="readiness-icon" aria-hidden="true">',
        html,
        flags=re.I,
    )
    return html


METRIC_INFO_CSS_BLOCK_RE = re.compile(
    r"\s*\.label-row \{ display: flex[\s\S]*?"
    r"\.ladr-section-lead-with-tip \.metric-info-tip \{[\s\S]*?\}\s*",
    re.MULTILINE,
)

PR_TABLE_INFO_CSS_BLOCK_RE = re.compile(
    r"\s*\.section-pr th \.th-label-row[\s\S]*?"
    r"\.split-metric-with-tip \{[\s\S]*?\}\s*",
    re.MULTILINE,
)

METRIC_INFO_SCRIPT_RE = re.compile(
    r"\s*<script>\s*/\* metric-info-tip click toggle \*/[\s\S]*?</script>",
    re.IGNORECASE,
)


def _remove_metric_info_tip_spans(html: str) -> str:
    """Remove nested metric-info-tip markup (one span tree per iteration)."""
    marker = '<span class="metric-info-tip"'
    while marker in html:
        start = html.find(marker)
        if start < 0:
            break
        depth = 0
        i = start
        end = -1
        while i < len(html):
            if html.startswith("<span", i):
                depth += 1
                close = html.find(">", i)
                if close < 0:
                    break
                i = close + 1
            elif html.startswith("</span>", i):
                depth -= 1
                i += len("</span>")
                if depth == 0:
                    end = i
                    break
            else:
                i += 1
        if end < 0:
            break
        html = html[:start] + html[end:]
    return html


def strip_report_tooltips(html: str) -> str:
    """Remove info-icon tooltips, related CSS, and click script (idempotent)."""
    html = _remove_metric_info_tip_spans(html)
    html = METRIC_INFO_CSS_BLOCK_RE.sub("", html)
    html = PR_TABLE_INFO_CSS_BLOCK_RE.sub("", html)
    html = TOOLTIP_LAYOUT_FIX_BLOCK_RE.sub("", html)
    html = _strip_modern_tooltip_layout_fix(html)
    html = OWNERSHIP_TOOLTIP_CSS_BLOCK_RE.sub("", html)
    html = METRIC_INFO_SCRIPT_RE.sub("", html)
    html = _strip_legacy_tooltip_layout_fix(html)
    for tag in ("h1", "h2", "h3"):
        html = re.sub(
            rf"<{tag}><span class=\"heading-label-row\">([\s\S]*?)</span></{tag}>",
            rf"<{tag}>\1</{tag}>",
            html,
            flags=re.IGNORECASE,
        )
    html = re.sub(
        r'<div class="summary-group-title"><span class="group-title-row">'
        r'<span class="group-title-text">([^<]*)</span></span></div>',
        r'<div class="summary-group-title">\1</div>',
        html,
    )
    html = re.sub(
        r'<div class="label-row"><div class="label">([^<]*)</div>\s*</div>',
        r'<div class="label">\1</div>',
        html,
    )
    html = re.sub(
        r"<th><span class=\"th-label-row\">([^<]*)</span></th>",
        r"<th>\1</th>",
        html,
    )
    html = html.replace("cache-meta-with-tip", "cache-meta")
    html = html.replace("quick-links-with-tip", "quick-links")
    html = html.replace("note-box-with-tip", "note-box")
    html = html.replace("split-metric-with-tip", "split-metric")
    html = re.sub(r'\bsection-lead-with-tip\b', "section-lead", html)
    html = re.sub(r'\btrace-section-lead-with-tip\b', "trace-section-lead", html)
    html = re.sub(r'\bladr-section-lead-with-tip\b', "ladr-section-lead", html)
    html = re.sub(
        r'<p class="section-lead">\s*([\s\S]*?)\s*</p>',
        lambda m: f'<p class="section-lead">{m.group(1).strip()}</p>',
        html,
        count=1,
    )
    return html


def inject_jira_readiness_styles(html: str) -> str:
    """Green ✓ / red ✗ readiness row styling (no tooltips)."""
    if JIRA_READINESS_UI_MARKER in html or "jira-readiness-block" not in html:
        return html
    return html.replace("</style>", JIRA_READINESS_UI_CSS + "\n  </style>", 1)


RECOMMENDED_ACTIONS_UI_MARKER = "recommended-actions-groups v1"
RECOMMENDED_ACTIONS_UI_CSS = f"""
    /* {RECOMMENDED_ACTIONS_UI_MARKER} */
    .section-actions .actions-group-title {{
      font-size: 0.95rem;
      font-weight: 700;
      color: #9a3412;
      margin: 1rem 0 0.5rem;
      padding-bottom: 0.25rem;
      border-bottom: 1px solid #fed7aa;
    }}
    .section-actions .recommended-actions-groups .actions-group-title:first-child {{
      margin-top: 0;
    }}
    .section-actions .actions-group-list {{
      list-style: none;
      padding-left: 0;
      counter-reset: action;
      margin-bottom: 0.25rem;
    }}
"""


def inject_recommended_actions_styles(html: str) -> str:
    """§8 Dev/QA action group layout (no tooltip changes)."""
    if RECOMMENDED_ACTIONS_UI_MARKER in html or "recommended-actions-groups" not in html:
        return html
    return html.replace("</style>", RECOMMENDED_ACTIONS_UI_CSS + "\n  </style>", 1)


def inject_recommended_actions_markup(html: str) -> str:
    """Unwrap legacy <ol> around Dev/QA action groups (template-safe)."""
    if "recommended-actions-groups" not in html:
        return html
    return re.sub(
        r"(<div class=\"section-body\">\s*)<ol>\s*(<div class=\"recommended-actions-groups\">.*?</div>)\s*</ol>",
        r"\1\2",
        html,
        count=1,
        flags=re.DOTALL,
    )


def apply_report_ui_enhancements(html: str) -> str:
    """Info-icon tooltips on all labels, readiness icons, trace layout, footer."""
    html = strip_report_tooltips(html)
    html = _ensure_info_icon_styles(html)
    html = inject_jira_readiness_styles(html)
    html = normalize_jira_readiness_icons(html)
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
    html = _normalize_ladr_section_lead(html)
    html = inject_lead_paragraph_tooltips(html)
    html = inject_section_lead_tooltip(html)
    html = inject_ownership_card_tooltips(html)
    html = inject_ownership_tooltip_styles(html)
    html = inject_review_panel_tooltips(html)
    html = inject_trace_table_header_tooltips(html)
    html = inject_trace_section_styles(html)
    html = inject_trace_section_markup(html)
    html = inject_lead_paragraph_tooltips(html)
    html = inject_recommended_actions_styles(html)
    html = inject_recommended_actions_markup(html)
    html = inject_report_footer(html)
    return html


def wrap_summary_metric_labels(html: str) -> str:
    """Add info-icon tooltips to §1 coverage summary metric labels (legacy alias)."""
    return inject_all_metric_label_tooltips(html)
