#!/usr/bin/env python3
"""Regenerate MSC-204417 report with local-timezone timestamped filename."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from coverage_report_helpers import (  # noqa: E402
    apply_report_ui_enhancements,
    load_testplan_cache,
    render_testplan_rows,
)
from coverage_report_timestamp import report_paths  # noqa: E402

template = (ROOT / ".cursor/skills/msc-dev-code-and-qa-test-coverage-validator/report-template.html").read_text(encoding="utf-8")

candidates = sorted(ROOT.glob("reports/MSC-204417*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
if not candidates:
    raise SystemExit("No existing MSC-204417 report found under reports/")
old = candidates[0].read_text(encoding="utf-8")

out, generated_date, tz_label = report_paths("MSC-204417", root=ROOT)

replacements = {
    "{{ISSUE_KEY}}": "MSC-204417",
    "{{STORY_TITLE}}": "Implement V2 messaging in ESS to support caption status for Monitor",
    "{{JIRA_URL}}": "https://wbdstreaming.atlassian.net/browse/MSC-204417",
    "{{ISSUE_STATUS}}": "In QA",
    "{{ISSUE_TYPE}}": "Story",
    "{{GENERATED_DATE}}": generated_date,
    "{{VERDICT}}": "Pass with gaps",
    "{{VERDICT_CLASS}}": "pass-gaps",
    "{{VERDICT_RATIONALE}}": "",  # set below from test plan + PR state
    "{{REQ_COVERAGE_PCT}}": "100.0%",
    "{{REQ_COVERAGE_CLASS}}": "metric-good",
    "{{REQ_COVERAGE_DETAIL}}": "3/3 scored",
    "{{DEV_COVERAGE_PCT}}": "83.3%",
    "{{DEV_COVERAGE_CLASS}}": "metric-warn",
    "{{DEV_COVERAGE_DETAIL}}": "2.5/3 dev-owned",
    "{{QA_SCOPE_SUMMARY}}": "2 items",
    "{{REQ_MAPPED_SUMMARY}}": "3/3 AC",
    "{{REQ_MAPPED_CLASS}}": "metric-good",
    "{{REQ_MAPPED_DETAIL}}": "R1–R3",
    "{{OPEN_GAPS_SUMMARY}}": "2 High · 2 Med",
    "{{OPEN_GAPS_CLASS}}": "metric-warn",
    "{{OPEN_GAPS_DETAIL}}": "No linked PR; Monitor E2E; STATUS_ERROR 9000 (L14) test gap",
    "{{CI_LINE_COVERAGE}}": "NA",
    "{{CI_LINE_CLASS}}": "metric-na",
    "{{CI_LINE_NOTE}}": "No PR for MSC-204417; develop branch only",
    "{{CI_BRANCH_COVERAGE}}": "NA",
    "{{CI_BRANCH_CLASS}}": "metric-na",
    "{{CI_BRANCH_NOTE}}": "No PR for MSC-204417; develop branch only",
}

tp = load_testplan_cache("MSC-204417", ROOT)
cov = tp.get("coverage") or {}
tp_pct = cov.get("testplanCoveragePct")
if tp_pct is None:
    replacements["{{TESTPLAN_COVERAGE_PCT}}"] = "NA"
    replacements["{{TESTPLAN_COVERAGE_CLASS}}"] = "metric-na"
else:
    replacements["{{TESTPLAN_COVERAGE_PCT}}"] = f"{tp_pct}%"
    replacements["{{TESTPLAN_COVERAGE_CLASS}}"] = (
        "metric-good" if tp_pct >= 85 else "metric-warn" if tp_pct >= 70 else "metric-fail"
    )
replacements["{{TESTPLAN_COVERAGE_DETAIL}}"] = cov.get(
    "coverageDetail", "No test plan"
)
note = tp.get("testPlanSummaryNote") or ""
replacements["{{TESTPLAN_NOTE}}"] = (
    f'<div class="note-box">{note}</div>' if note else ""
)
replacements["{{TESTPLAN_ROWS}}"] = render_testplan_rows(tp.get("testCases") or [])
uncovered = cov.get("uncoveredRequirements") or []
uncovered_ladr = cov.get("uncoveredLadrRequirements") or []
uncovered_jira = cov.get("uncoveredJiraRequirements") or uncovered
gaps = []
for r in uncovered_jira:
    gaps.append(
        f'<li class="medium"><strong>{r}</strong> — no mapped test case for Jira acceptance criterion</li>'
    )
for r in uncovered_ladr:
    gaps.append(
        f'<li class="medium"><strong>{r}</strong> — no mapped test case for LADR ESS scenario (e.g. STATUS_ERROR 9000)</li>'
    )
if not gaps and not uncovered:
    gaps.append('<li class="medium">Review test plan ↔ PR alignment for Monitor E2E scenarios</li>')
tc_count = cov.get("testCaseCount") or 0
gwt_complete = cov.get("completeGwtCount") or 0
incomplete_gwt = tc_count - gwt_complete
if incomplete_gwt:
    gaps.append(
        f'<li class="medium">{incomplete_gwt} test case(s) missing full Given/When/Then in step text</li>'
    )
replacements["{{TESTPLAN_GAPS_LIST}}"] = "".join(gaps)

tc_n = cov.get("testCaseCount", 12)
gwt_n = cov.get("completeGwtCount", 0)
replacements["{{VERDICT_RATIONALE}}"] = (
    f"V2 caption messaging on develop with strong unit tests; Promo Caption Monitoring test plan "
    f"({tc_n} scenarios, {gwt_n}/{tc_n} full Given When Then, {cov.get('testplanCoveragePct', 'NA')}% combined coverage); "
    f"no PR linked; Monitor E2E and STATUS_ERROR 9000 (L14) need QA."
)
replacements["{{REQ_MAPPED_SUMMARY}}"] = (
    f"{cov.get('requirementsCovered', 0)}/{cov.get('requirementCount', 3)} AC in test plan"
)
replacements["{{REQ_MAPPED_DETAIL}}"] = (
    "auto-mapped from test plan"
    if cov.get("requirementsCovered")
    else "manual mapping needed"
)
if cov.get("testplanCoveragePct") is not None and cov.get("testplanCoveragePct") != "NA":
    pct = float(cov.get("testplanCoveragePct"))
    replacements["{{REQ_MAPPED_CLASS}}"] = (
        "metric-good" if pct >= 85 else "metric-warn" if pct >= 50 else "metric-fail"
    )


def ul_content(old_html: str, heading: str) -> str:
    idx = old_html.find(heading)
    if idx < 0:
        return "<li>—</li>"
    m = re.search(r"<ul[^>]*>(.*?)</ul>", old_html[idx:], re.S)
    return m.group(1).strip() if m else "<li>—</li>"


def ol_content(old_html: str, heading: str) -> str:
    idx = old_html.find(heading)
    if idx < 0:
        return "<li>—</li>"
    m = re.search(r"<ol[^>]*>(.*?)</ol>", old_html[idx:], re.S)
    return m.group(1).strip() if m else "<li>—</li>"


def tbody_rows(old_html: str) -> str:
    m = re.search(r"Requirements traceability.*?<tbody>\s*(.*?)\s*</tbody>", old_html, re.S)
    return m.group(1).strip() if m else '<tr><td colspan="7">—</td></tr>'


pr_note = re.search(r'<div class="note-box">.*?</div>', old, re.S)
replacements["{{PR_NOTE}}"] = pr_note.group(0) if pr_note else ""

pr_section = re.search(r"Linked PR\(s\).*?<tbody>\s*(.*?)\s*</tbody>", old, re.S)
replacements["{{PR_ROWS}}"] = pr_section.group(1).strip() if pr_section else ""

replacements["{{DEV_COVERED_LIST}}"] = ul_content(old, "Covered by dev tests")
replacements["{{QA_HANDOFF_LIST}}"] = ul_content(old, "QA handoff")
replacements["{{REQUIREMENT_ROWS}}"] = tbody_rows(old)
impl = ul_content(old, "Correctly implemented")
impl += (
    "<li><strong>Test plan:</strong> Jira attachment "
    "<code>Promo Caption Monitoring.xlsx</code> — Caption Monitoring sheet, 12 caption status scenarios (TC1–TC12)</li>"
)
replacements["{{CORRECTLY_IMPLEMENTED_LIST}}"] = impl
gaps = ul_content(old, "Gaps and concerns")
tp_pct = cov.get("testplanCoveragePct")
if tp_pct == 0 or tp_pct == 0.0:
    gaps += '<li class="medium"><strong>Medium:</strong> Test plan scenarios not mapped to acceptance criteria — re-run fetch with Confluence/LADR cache</li>'
elif incomplete_gwt:
    gaps += f'<li class="medium"><strong>Medium:</strong> {incomplete_gwt} test case(s) missing full Given/When/Then</li>'
replacements["{{GAPS_LIST}}"] = gaps
replacements["{{ASSUMPTIONS_LIST}}"] = ul_content(old, "Assumptions and open questions")
replacements["{{ACTIONS_LIST}}"] = ol_content(old, "Recommended actions")

html = template
for k, v in replacements.items():
    html = html.replace(k, v)

html = apply_report_ui_enhancements(html)

out.write_text(html, encoding="utf-8")

manifest_path = ROOT / "reports" / ".cache" / "MSC-204417-manifest.json"
manifest = {}
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["lastReportFile"] = str(out.relative_to(ROOT)).replace("\\", "/")
manifest["timezoneLabel"] = tz_label
manifest_path.parent.mkdir(parents=True, exist_ok=True)
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

print(out.resolve())
