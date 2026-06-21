#!/usr/bin/env python3
"""
Generic HTML coverage report builder for msc-dev-code-and-qa-test-coverage-validator.

Uses caches: jira, testplan, prefetch, mapping (+ optional analysis JSON for overrides).

  python scripts/build_coverage_report.py MSC-205625
  python scripts/build_coverage_report.py MSC-205625 --analysis reports/.cache/MSC-205625-analysis.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from coverage_report_helpers import (  # noqa: E402
    apply_report_ui_enhancements,
    build_assumptions_list,
    build_branch_compare_pr_note,
    build_correctly_implemented_list,
    build_implementation_gaps_list,
    build_jira_readiness_block,
    build_open_gaps_detail,
    build_qa_ownership_fields,
    build_quick_links,
    build_release_score_block,
    build_req_coverage_detail,
    build_testplan_report_fields,
    build_cache_meta_line,
    ci_coverage_report_fields,
    load_jira_cache,
    load_mapping_cache,
    load_prefetch_cache,
    load_testplan_cache,
    render_pr_rows_from_prefetch,
    render_requirement_rows_from_mapping,
    testplan_coverage_class,
)
from coverage_report_timestamp import report_paths  # noqa: E402

SKILL_TEMPLATE = (
    ROOT / ".cursor/skills/coverage-validator/report-template.html"
)


def _metric_class(pct: Any) -> str:
    if pct is None:
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


def _verdict(req_pct: float | None, tp_pct: float | None, gap_summary: str) -> tuple[str, str, str]:
    has_high = bool(re.search(r"[1-9]\d*\s+High", gap_summary or ""))
    if has_high or (req_pct is not None and req_pct < 50):
        return "Fail", "fail", "Critical gaps in code or test plan mapping"
    if (tp_pct is not None and tp_pct < 85) or (req_pct is not None and req_pct < 100):
        return "Pass with gaps", "pass-gaps", "Implementation or test plan has remaining gaps — see sections below"
    return "Pass", "pass", "Requirements, dev tests, and test plan alignment are satisfactory"


def build_report(
    issue_key: str,
    *,
    root: Path | None = None,
    analysis: dict[str, Any] | None = None,
    dev_tests_by_number: dict[int | str, str] | None = None,
    rerun_mapping: bool = False,
    execute_tests: bool = False,
) -> tuple[str, Path, str, str]:
    base = root or ROOT
    key = issue_key.upper()
    from cache_freshness import ensure_fresh_mapping, is_mapping_stale, load_manifest_max_age

    max_age = load_manifest_max_age(key, base)
    if execute_tests:
        subprocess.run(
            [sys.executable, str(SCRIPTS / "execute_pr_tests.py"), key],
            cwd=base,
            check=False,
        )
        rerun_mapping = True
    if rerun_mapping:
        ensure_fresh_mapping(key, base, force=True, max_age_hours=max_age)
    else:
        stale, _ = is_mapping_stale(key, base, max_age_hours=max_age)
        if stale:
            ensure_fresh_mapping(key, base, force=False, max_age_hours=max_age)

    jira = load_jira_cache(key, base)
    tp = load_testplan_cache(key, base)
    prefetch = load_prefetch_cache(key, base)
    mapping = load_mapping_cache(key, base)

    if not mapping:
        subprocess.run(
            [sys.executable, str(SCRIPTS / "map_requirements_to_diff.py"), key],
            cwd=base,
            check=False,
        )
        mapping = load_mapping_cache(key, base)

    cov = tp.get("coverage") or {}
    req_pct = mapping.get("reqCoveragePct")
    dev_pct = mapping.get("devTestCoveragePct")
    if analysis is not None:
        if analysis.get("reqCoveragePct") is not None:
            req_pct = analysis["reqCoveragePct"]
        if analysis.get("devCoveragePct") is not None:
            dev_pct = analysis["devCoveragePct"]
    tp_pct = cov.get("testplanCoveragePct")

    gaps_html, gap_summary, gap_class = build_implementation_gaps_list(
        mapping, tp, prefetch=prefetch
    )
    gaps_detail = build_open_gaps_detail(
        mapping, tp, prefetch=prefetch, gap_summary=gap_summary
    )
    implemented_html = build_correctly_implemented_list(mapping)
    assumptions_html = build_assumptions_list(mapping, tp)
    if analysis and analysis.get("gapsList"):
        gaps_html = analysis["gapsList"]

    verdict, verdict_class, rationale = _verdict(req_pct, tp_pct, gap_summary)
    if analysis:
        verdict = analysis.get("verdict", verdict)
        verdict_class = analysis.get("verdictClass", verdict_class)
        rationale = analysis.get("verdictRationale", rationale)

    tc_n = cov.get("testCaseCount", 0)
    gwt_n = cov.get("completeGwtCount", 0)
    qa_fields = build_qa_ownership_fields(key, base)
    jira_n = mapping.get("jiraRequirementCount") or len(mapping.get("requirements") or [])
    ladr_n = mapping.get("ladrRequirementCount") or 0
    if ladr_n:
        ac_label = f"{jira_n} Jira + {ladr_n} LADR requirements"
    else:
        ac_label = f"{len(mapping.get('requirements') or [])} acceptance criteria"
    if not analysis or not analysis.get("verdictRationale"):
        rationale = (
            f"{verdict} — {ac_label}; "
            f"test plan {tp_pct}% ({tc_n} scenarios, {gwt_n}/{tc_n} full Given When Then); "
            f"dev code {req_pct}%; dev tests {dev_pct}%."
        )

    req_detail_default = build_req_coverage_detail(mapping)
    replacements: dict[str, str] = {
        "{{ISSUE_KEY}}": key,
        "{{STORY_TITLE}}": (analysis or {}).get("storyTitle") or jira.get("summary") or key,
        "{{JIRA_URL}}": f"https://wbdstreaming.atlassian.net/browse/{key}",
        "{{ISSUE_STATUS}}": jira.get("status") or "—",
        "{{ISSUE_TYPE}}": jira.get("issuetype") or "Story",
        "{{VERDICT}}": verdict,
        "{{VERDICT_CLASS}}": verdict_class,
        "{{VERDICT_RATIONALE}}": rationale,
        "{{REQ_COVERAGE_PCT}}": f"{req_pct}%" if req_pct is not None else "NA",
        "{{REQ_COVERAGE_CLASS}}": _metric_class(req_pct),
        "{{REQ_COVERAGE_DETAIL}}": (
            analysis.get("reqCoverageDetail", req_detail_default)
            if analysis
            else req_detail_default
        ),
        "{{DEV_COVERAGE_PCT}}": f"{dev_pct}%" if dev_pct is not None else "NA",
        "{{DEV_COVERAGE_CLASS}}": _metric_class(dev_pct),
        "{{DEV_COVERAGE_DETAIL}}": (
            analysis.get("devCoverageDetail", "auto-mapped from PR test files")
            if analysis
            else "auto-mapped from PR test files"
        ),
        "{{REQ_MAPPED_SUMMARY}}": f"{cov.get('requirementsCovered', 0)}/{cov.get('requirementCount', 0)} AC in test plan",
        "{{REQ_MAPPED_CLASS}}": testplan_coverage_class(tp_pct),
        "{{REQ_MAPPED_DETAIL}}": "Jira + LADR from test plan cache",
        "{{QA_SCOPE_SUMMARY}}": (
            analysis.get("qaScopeSummary", qa_fields["qaScopeSummary"])
            if analysis
            else qa_fields["qaScopeSummary"]
        ),
        "{{QA_SCOPE_DETAIL}}": (
            analysis.get("qaScopeDetail", qa_fields["qaScopeDetail"])
            if analysis
            else qa_fields["qaScopeDetail"]
        ),
        "{{OPEN_GAPS_SUMMARY}}": (
            analysis.get("openGapsSummary", gap_summary) if analysis else gap_summary
        ),
        "{{OPEN_GAPS_CLASS}}": (
            analysis.get("openGapsClass", gap_class) if analysis else gap_class
        ),
        "{{OPEN_GAPS_DETAIL}}": (
            analysis.get("openGapsDetail", gaps_detail)
            if analysis
            else gaps_detail
        ),
        "{{PR_NOTE}}": (
            analysis.get("prNote", "")
            if analysis and analysis.get("prNote")
            else build_branch_compare_pr_note(key, base)
        ),
        "{{PR_ROWS}}": render_pr_rows_from_prefetch(key, base, dev_tests_by_number=dev_tests_by_number),
        "{{REQUIREMENT_ROWS}}": (
            analysis.get("requirementRows")
            if analysis and analysis.get("requirementRows")
            else render_requirement_rows_from_mapping(key, base)
        ),
        "{{DEV_COVERED_LIST}}": (
            analysis.get("devCoveredList", qa_fields["devCoveredList"])
            if analysis
            else qa_fields["devCoveredList"]
        ),
        "{{QA_HANDOFF_LIST}}": (
            analysis.get("qaHandoffList", qa_fields["qaHandoffList"])
            if analysis
            else qa_fields["qaHandoffList"]
        ),
        "{{CORRECTLY_IMPLEMENTED_LIST}}": (
            analysis.get("correctlyImplementedList", implemented_html)
            if analysis
            else implemented_html
        ),
        "{{GAPS_LIST}}": (
            analysis.get("gapsList", gaps_html) if analysis and analysis.get("gapsList") else gaps_html
        )
        or "<li>—</li>",
        "{{ASSUMPTIONS_LIST}}": (
            analysis.get("assumptionsList", assumptions_html)
            if analysis
            else assumptions_html
        ),
        "{{ACTIONS_LIST}}": (
            analysis.get("actionsList", qa_fields["actionsList"])
            if analysis
            else qa_fields["actionsList"]
        ),
        "{{CACHE_META}}": build_cache_meta_line(key, base),
        "{{QUICK_LINKS}}": build_quick_links(key, base),
        "{{JIRA_READINESS_BLOCK}}": build_jira_readiness_block(key, base),
        "{{RELEASE_SCORE_BLOCK}}": build_release_score_block(req_pct, dev_pct, tp_pct, gap_summary),
    }
    replacements.update(build_testplan_report_fields(key, base))
    replacements.update(ci_coverage_report_fields(key, base))

    template = SKILL_TEMPLATE.read_text(encoding="utf-8")
    out_path, generated, tz = report_paths(key, root=base)
    replacements["{{GENERATED_DATE}}"] = generated

    html = template
    for k, v in replacements.items():
        html = html.replace(k, v)

    html = apply_report_ui_enhancements(html)
    return html, out_path, generated, tz


def main() -> int:
    parser = argparse.ArgumentParser(description="Build coverage validation HTML report")
    parser.add_argument("issue_key")
    parser.add_argument("--analysis", help="Optional JSON overrides for narrative sections")
    parser.add_argument(
        "--rerun",
        action="store_true",
        help="Force remap requirements before building (also remaps when upstream caches are newer)",
    )
    parser.add_argument(
        "--execute-tests",
        action="store_true",
        help="Run local pytest on PR test files (requires testRepoRoot), then remap and build",
    )
    args = parser.parse_args()

    analysis = None
    if args.analysis:
        analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))

    html, out_path, generated, tz = build_report(
        args.issue_key.upper(),
        analysis=analysis,
        rerun_mapping=args.rerun,
        execute_tests=args.execute_tests,
    )
    out_path.write_text(html, encoding="utf-8")

    manifest_path = ROOT / "reports" / ".cache" / f"{args.issue_key.upper()}-manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["lastReportFile"] = str(out_path.relative_to(ROOT)).replace("\\", "/")
    manifest["timezoneLabel"] = tz
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(out_path.resolve())
    print(generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
