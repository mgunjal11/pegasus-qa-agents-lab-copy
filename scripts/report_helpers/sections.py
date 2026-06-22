"""Section HTML builders for coverage reports (content only; not tooltips)."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from testplan_gwt import steps_for_display
from testplan_evidence import extract_testcase_evidence_ids, has_mascot_links

from report_helpers.common import REPORT_AGENT_NAME, REPORT_DEVELOPER, esc


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
    exec_path = base / "reports" / ".cache" / f"{issue_key.upper()}-test-execution.json"
    if exec_path.exists():
        try:
            ex = json.loads(exec_path.read_text(encoding="utf-8"))
            st = ex.get("status")
            if st == "ok":
                parts.append(f"Pytest {int(ex.get('passed') or 0)} passed")
            elif st == "fail":
                parts.append(f"Pytest {int(ex.get('failed') or 0)} failed")
            elif st == "skipped":
                parts.append("Pytest skipped (no local repo)")
        except (json.JSONDecodeError, OSError):
            pass
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


def _compact_evidence_path(path: str) -> str:
    """Short §5 Evidence label; full path goes in the HTML title attribute."""
    norm = str(path).replace("\\", "/")
    parts = [p for p in norm.split("/") if p]
    if len(parts) <= 2:
        return norm
    return "/".join(parts[-2:])


def _summarize_trace_evidence(
    matched_files: list[str],
    matched_tests: list[str] | None = None,
    *,
    max_files: int = 2,
    max_tests: int = 1,
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """
    Compact Evidence for §5 — visible rows plus extra rows for expand (+N more).
    Returns (visible_items, extra_items) as (display_label, kind, full_value).
    """
    from mapping_evidence import _is_weak_evidence_path, rank_matched_files

    files = [f for f in (matched_files or []) if f and not str(f).startswith("symbol:")]
    tests = [t for t in (matched_tests or []) if t]
    ranked = rank_matched_files(files, limit=24)
    strong = [f for f in ranked if not _is_weak_evidence_path(f)]
    weak = [f for f in ranked if _is_weak_evidence_path(f)]

    display_files: list[str] = []
    seen_src = False
    for path in strong:
        if len(display_files) >= max_files:
            break
        low = path.lower()
        is_src = "/src/" in low or low.startswith("src/")
        if is_src:
            if seen_src:
                continue
            seen_src = True
        if path not in display_files:
            display_files.append(path)

    file_stems = {Path(f).stem.lower() for f in display_files}
    display_tests: list[str] = []
    for name in tests:
        if len(display_tests) >= max_tests:
            break
        low = name.lower()
        if low in file_stems:
            continue
        if any(low.startswith(stem.replace("test_", "")) or stem in low for stem in file_stems):
            continue
        display_tests.append(name)

    def _as_items(paths: list[str], test_names: list[str]) -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []
        for path in paths:
            out.append((_compact_evidence_path(path), "file", path))
        for name in test_names:
            label = name if len(name) <= 44 else f"{name[:41]}…"
            out.append((label, "test", name))
        return out

    visible = _as_items(display_files, display_tests)
    extra_files = [p for p in strong if p not in display_files]
    extra_tests = [n for n in tests if n not in display_tests]
    extra = _as_items(extra_files + weak, extra_tests)
    return visible, extra


def _evidence_list_item(label: str, kind: str, full: str) -> str:
    title = f' title="{esc(full)}"' if full != label else ""
    if kind == "test":
        return f'<li><code{title}>{esc(label)}</code> <span class="evidence-tag">test</span></li>'
    return f"<li><code{title}>{esc(label)}</code></li>"


def _render_trace_evidence_cell(
    matched_files: list[str],
    confidence: str,
    evidence_note: str = "",
    matched_tests: list[str] | None = None,
) -> str:
    """Evidence column: compact list + expandable +N more (details/summary) + confidence."""
    conf = confidence or "low"
    note = (evidence_note or "").strip()
    items, extra = _summarize_trace_evidence(matched_files, matched_tests)
    if not items and not extra:
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
    rows = "".join(_evidence_list_item(label, kind, full) for label, kind, full in items)
    expand_html = ""
    if extra:
        extra_rows = "".join(_evidence_list_item(label, kind, full) for label, kind, full in extra)
        expand_html = (
            f'<details class="evidence-expand">'
            f'<summary class="evidence-more">+{len(extra)} more</summary>'
            f'<ul class="evidence-list evidence-list-extra">{extra_rows}</ul>'
            f"</details>"
        )
    note_html = f'<p class="evidence-note">{esc(note)}</p>' if note and not any(i[1] == "test" for i in items) else ""
    return (
        f'<td class="evidence-cell">'
        f"{note_html}"
        f'<ul class="evidence-list">{rows}</ul>{expand_html}'
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
            list(req.get("matchedTests") or []),
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
    from report_helpers.ui import metric_info_icon_html

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


