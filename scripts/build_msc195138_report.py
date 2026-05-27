#!/usr/bin/env python3
"""Build MSC-195138 coverage validation HTML report."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from coverage_report_helpers import (  # noqa: E402
    load_testplan_cache,
    render_pr_rows,
    render_testplan_rows,
)
from coverage_report_timestamp import report_paths  # noqa: E402

KEY = "MSC-195138"
template = (ROOT / ".cursor/skills/msc-code-coverage-validator/report-template.html").read_text(
    encoding="utf-8"
)

tp = load_testplan_cache(KEY, ROOT)
cov = tp.get("coverage") or {}
tp_pct = cov.get("testplanCoveragePct")

replacements = {
    "{{ISSUE_KEY}}": KEY,
    "{{STORY_TITLE}}": "[Mascot] FF2.0 Messaging Race Conditions",
    "{{JIRA_URL}}": "https://wbdstreaming.atlassian.net/browse/MSC-195138",
    "{{ISSUE_STATUS}}": "Done",
    "{{ISSUE_TYPE}}": "Story",
    "{{VERDICT}}": "Pass with gaps",
    "{{VERDICT_CLASS}}": "pass-gaps",
    "{{VERDICT_RATIONALE}}": "",  # set after test plan load
    "{{REQ_COVERAGE_PCT}}": "83.3%",
    "{{REQ_COVERAGE_CLASS}}": "metric-warn",
    "{{REQ_COVERAGE_DETAIL}}": "2.5/3 scored",
    "{{DEV_COVERAGE_PCT}}": "83.3%",
    "{{DEV_COVERAGE_CLASS}}": "metric-warn",
    "{{DEV_COVERAGE_DETAIL}}": "2.5/3 dev+shared",
    "{{REQ_MAPPED_SUMMARY}}": "2/3 AC in test plan",
    "{{REQ_MAPPED_CLASS}}": "metric-warn",
    "{{REQ_MAPPED_DETAIL}}": "R1, R2 mapped · R3 uncovered",
    "{{QA_SCOPE_SUMMARY}}": "3 items",
    "{{OPEN_GAPS_SUMMARY}}": "1 High · 3 Med",
    "{{OPEN_GAPS_CLASS}}": "metric-warn",
    "{{OPEN_GAPS_DETAIL}}": "mascot-api-transform PrepNotRequired; R3 no TC; 1 TC missing full GWT; Mascot E2E",
    "{{CI_LINE_COVERAGE}}": "NA",
    "{{CI_LINE_CLASS}}": "metric-na",
    "{{CI_LINE_NOTE}}": "PRs merged; codecov prefetch unavailable",
    "{{CI_BRANCH_COVERAGE}}": "NA",
    "{{CI_BRANCH_CLASS}}": "metric-na",
    "{{CI_BRANCH_NOTE}}": "PRs merged; codecov prefetch unavailable",
    "{{PR_NOTE}}": "",
    "{{PR_ROWS}}": render_pr_rows(
        [
            {
                "url": "https://github.com/wbd-msc/pegasus-reps/pull/22",
                "number": 22,
                "repo": "wbd-msc/pegasus-reps",
                "state": "MERGED",
                "title": "RepsPoller — publish unpublished reps_events in timestamp order",
                "dev_tests": "test_poller_service.py",
                "checks": None,
            },
            {
                "url": "https://github.com/wbd-msc/pegasus-texttransform/pull/75",
                "number": 75,
                "repo": "wbd-msc/pegasus-texttransform",
                "state": "MERGED",
                "title": "mediaRequest in status; correlationMetadata; header.timestamp",
                "dev_tests": "test_helper.py",
                "checks": None,
            },
        ]
    ),
    "{{DEV_COVERED_LIST}}": """<li><strong>R1</strong> — <code>poller_service.py</code> streams unpublished <code>reps_events</code> ordered by <code>header.timestamp</code>; <code>test_poller_service.py</code> (404 lines, unit)</li>
<li><strong>R2</strong> — <code>helper.py</code> <code>create_wings_status_message</code> preserves <code>correlationMetadata</code> and UTC <code>header.timestamp</code>; <code>test_helper.py</code> asserts request id namespace (unit)</li>
<li><strong>R3</strong> — indirect: ordered SNS publish reduces Pick-before-PickRequested errors; no unit test for PrepNotRequired-without-PickRequested</li>""",
    "{{QA_HANDOFF_LIST}}": """<li><strong>R1/R2</strong> — <span class="badge badge-e2e">E2E</span> Execute FF Race Condition.xlsx scenarios (TC1–TC11) in INT/SIT — verify Mascot event order and fulfill job status</li>
<li><strong>R3</strong> — <span class="badge badge-manual">Manual</span> Confirm mascot-api-transform handles PrepNotRequired when PickRequested absent (not in linked PRs; no dedicated test case)</li>
<li><strong>Regression</strong> — Compare <code>pegasusId-statusBefore.csv</code> vs <code>pegasusId-statusAfter.csv</code> attachments on Jira</li>""",
    "{{REQUIREMENT_ROWS}}": """<tr><td>R1</td><td>Pick events will not error due to out-of-order or read/write race conditions</td><td><span class="badge badge-implemented">Implemented</span></td><td><span class="badge badge-covered">Covered</span></td><td><span class="badge badge-dev">Dev</span></td><td><span class="badge badge-e2e">E2E</span></td><td>pegasus-reps#22 RepsPoller; test_poller_service.py; TC1/TC10/TC11 map R1</td></tr>
<tr><td>R2</td><td>Fulfill jobs show accurate statuses in Mascot (Request/Select stuck states)</td><td><span class="badge badge-implemented">Implemented</span></td><td><span class="badge badge-covered">Covered</span></td><td><span class="badge badge-shared">Shared</span></td><td><span class="badge badge-e2e">E2E</span></td><td>texttransform#75 correlationMetadata + timestamp; TC1/TC11 map R2</td></tr>
<tr><td>R3</td><td>Handle PrepNotRequired when PickRequested may be missing (temporary Mascot fix)</td><td><span class="badge badge-partial">Partial</span></td><td><span class="badge badge-partial">Partial</span></td><td><span class="badge badge-shared">Shared</span></td><td><span class="badge badge-manual">Manual</span></td><td>Not in PR #22/#75; no test plan case — QA manual required</td></tr>""",
    "{{CORRECTLY_IMPLEMENTED_LIST}}": """<li><strong>pegasus-reps#22</strong> — RepsPoller publishes unpublished <code>reps_events</code> in <code>header.timestamp</code> order with SNS MessageGroupId; 404-line unit test suite</li>
<li><strong>pegasus-texttransform#75</strong> — Status events retain <code>urn:wbd:distribute:request-id</code> in correlationMetadata for Mascot status accuracy</li>
<li><strong>Test plan:</strong> Jira attachment <code>FF Race Condition.xlsx</code> — Scenarios sheet, 11 E2E race-condition scenarios (TC1–TC11)</li>
<li>Jira evidence attachments document before/after fulfill job status for regression analysis</li>""",
    "{{GAPS_LIST}}": "",
    "{{ASSUMPTIONS_LIST}}": """<li>Root cause fix is event publish ordering via RepsPoller + accurate status payloads via texttransform — not mascot-api-transform code in this validation</li>
<li>Larger mongo read/write race deferred to separate ticket per Jira description</li>
<li>Both PRs merged and deployed to SIT per Jira comments (Allyson Yao, May 2026)</li>""",
    "{{ACTIONS_LIST}}": """<li><strong>QA:</strong> Execute FF Race Condition.xlsx E2E scenarios (TC1–TC11) in INT/SIT; attach Mascot links to ticket</li>
<li><strong>QA:</strong> Add test case for R3 PrepNotRequired-without-PickRequested if not covered by existing scenarios</li>
<li><strong>Dev:</strong> Confirm whether mascot-api-transform PrepNotRequired fallback is tracked in a follow-up ticket</li>
<li><strong>QA:</strong> Run regression using Jira before/after CSV attachments</li>""",
}

if tp_pct is None:
    replacements["{{TESTPLAN_COVERAGE_PCT}}"] = "NA"
    replacements["{{TESTPLAN_COVERAGE_CLASS}}"] = "metric-na"
    replacements["{{TESTPLAN_COVERAGE_DETAIL}}"] = "No test plan"
    replacements["{{TESTPLAN_NOTE}}"] = (
        '<div class="note-box">No QMetry test plan attached.</div>'
    )
    replacements["{{TESTPLAN_ROWS}}"] = '<tr><td colspan="6">No test plan attachment</td></tr>'
    replacements["{{TESTPLAN_GAPS_LIST}}"] = (
        '<li class="medium">No attached test plan — acceptance criteria not mapped to formal cases</li>'
    )
    replacements["{{GAPS_LIST}}"] = (
        '<li class="medium"><strong>Medium:</strong> No QMetry test plan parsed — re-attach or download FF Race Condition.xlsx</li>'
    )
else:
    replacements["{{TESTPLAN_COVERAGE_PCT}}"] = f"{tp_pct}%"
    replacements["{{TESTPLAN_COVERAGE_CLASS}}"] = (
        "metric-good" if tp_pct >= 85 else "metric-warn" if tp_pct >= 70 else "metric-fail"
    )
    replacements["{{TESTPLAN_COVERAGE_DETAIL}}"] = cov.get("coverageDetail", "")
    note = (
        "Jira attachment <code>FF Race Condition.xlsx</code> — Scenarios sheet · "
        f"{cov.get('testCaseCount', 11)} E2E scenarios for {KEY}."
    )
    replacements["{{TESTPLAN_NOTE}}"] = f'<div class="note-box">{note}</div>'
    replacements["{{TESTPLAN_ROWS}}"] = render_testplan_rows(tp.get("testCases") or [])
    uncovered = cov.get("uncoveredRequirements") or ["R3"]
    gaps = [
        f'<li class="medium"><strong>{r}</strong> — no auto-mapped test case in FF Race Condition.xlsx</li>'
        for r in uncovered
    ]
    incomplete = (cov.get("testCaseCount") or 0) - (cov.get("completeGwtCount") or 0)
    if incomplete:
        gaps.append(
            f'<li class="medium">{incomplete} test case(s) missing full Given/When/Then in step text</li>'
        )
    replacements["{{TESTPLAN_GAPS_LIST}}"] = "".join(gaps)
    impl_gaps = """<li class="high"><strong>High:</strong> Explicit PrepNotRequired-without-PickRequested handler in <code>mascot-api-transform</code> not found in linked PRs</li>
<li class="medium"><strong>Medium:</strong> Test plan covers R1/R2 only (66.7%) — no scenario for R3 PrepNotRequired-without-PickRequested</li>"""
    if incomplete:
        impl_gaps += f'<li class="medium"><strong>Medium:</strong> {incomplete} test case(s) missing full Given/When/Then in step text</li>'
    impl_gaps += '<li class="medium"><strong>Medium:</strong> Mascot UI E2E not in dev test suite — prod log examples in Jira comments need QA replay</li>'
    replacements["{{GAPS_LIST}}"] = impl_gaps
    gwt_n = cov.get("completeGwtCount", 0)
    tc_n = cov.get("testCaseCount", 11)
    replacements["{{VERDICT_RATIONALE}}"] = (
        f"Merged pegasus-reps #22 and pegasus-texttransform #75 address core race/status issues; "
        f"FF Race Condition.xlsx ({tc_n} E2E scenarios, {gwt_n}/{tc_n} full Given/When/Then, "
        f"{tp_pct}% test plan AC coverage, Mascot links in Evidence); R3 and mascot-api-transform gap remain."
    )

out, generated, tz = report_paths(KEY, root=ROOT)
replacements["{{GENERATED_DATE}}"] = generated

html = template
for k, v in replacements.items():
    html = html.replace(k, v)

out.write_text(html, encoding="utf-8")

manifest_path = ROOT / "reports" / ".cache" / f"{KEY}-manifest.json"
manifest = {}
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest.update(
    {
        "issueKey": KEY,
        "prUrls": [
            "https://github.com/wbd-msc/pegasus-reps/pull/22",
            "https://github.com/wbd-msc/pegasus-texttransform/pull/75",
        ],
        "repo": "wbd-msc/pegasus-reps",
        "lastReportFile": str(out.relative_to(ROOT)).replace("\\", "/"),
        "timezoneLabel": tz,
    }
)
manifest_path.parent.mkdir(parents=True, exist_ok=True)
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

print(out.resolve())
print(generated)
