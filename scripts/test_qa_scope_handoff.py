#!/usr/bin/env python3
"""Tests for QA scope None when dev tests cover a requirement."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from map_requirements_to_diff import derive_owner_and_qa_scope  # noqa: E402
from coverage_report_helpers import (  # noqa: E402
    _format_qa_scope_detail,
    _format_qa_scope_summary,
    _qa_scope_needs_qa_execution,
    build_open_gaps_detail,
    build_qa_ownership_fields,
    build_recommended_actions_list,
)


def test_dev_covered_sets_qa_scope_none():
    owner, scope = derive_owner_and_qa_scope(
        "Caption statuses are propagated to Kafka",
        "covered",
        "implemented",
    )
    assert owner == "dev"
    assert scope == "none"
    assert not _qa_scope_needs_qa_execution(scope)


def test_dev_missing_monitor_keeps_e2e():
    owner, scope = derive_owner_and_qa_scope(
        "Caption status visible in Monitor UI in UAT",
        "missing",
        "implemented",
    )
    assert owner == "shared"
    assert scope == "e2e"
    assert _qa_scope_needs_qa_execution(scope)


def test_build_qa_handoff_excludes_dev_covered_from_execute_bullet(tmp_path: Path):
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    mapping = {
        "requirements": [
            {
                "id": "R1",
                "text": "V2 messaging",
                "devTestStatus": "covered",
                "qaScope": "none",
                "owner": "dev",
            },
            {
                "id": "R2",
                "text": "Monitor UI visibility",
                "devTestStatus": "missing",
                "qaScope": "e2e",
                "owner": "shared",
            },
        ]
    }
    testplan = {
        "testCases": [
            {"id": "TC1", "mapped_requirements": ["R1"]},
            {"id": "TC2", "mapped_requirements": ["R2"]},
        ]
    }
    (cache / "MSC-TEST-mapping.json").write_text(json.dumps(mapping), encoding="utf-8")
    (cache / "MSC-TEST-testplan.json").write_text(json.dumps(testplan), encoding="utf-8")

    fields = build_qa_ownership_fields("MSC-TEST", root=tmp_path)
    assert "R1" in fields["devCoveredList"]
    # §4 only: dev-covered bullets omit QA scope None; §5 traceability still uses the badge.
    assert "None" not in fields["devCoveredList"]
    assert "proven by PR unit/integration tests" in fields["devCoveredList"]
    assert "R2" in fields["qaHandoffList"]
    assert "TC2" in fields["qaHandoffList"]
    assert "TC1" not in fields["qaHandoffList"]
    assert "0 items" not in fields["qaScopeSummary"]
    assert "skip scenarios" in fields["qaHandoffList"].lower() or "QA-scoped" in fields["qaHandoffList"]
    assert "<h3 class=\"actions-group-title\">Dev</h3>" in fields["actionsList"]
    assert "<h3 class=\"actions-group-title\">QA</h3>" in fields["actionsList"]


def test_recommended_actions_dev_and_qa_sections(tmp_path: Path):
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    mapping = {
        "requirements": [
            {
                "id": "R1",
                "text": "Feature works",
                "codeStatus": "missing",
                "devTestStatus": "missing",
                "owner": "dev",
                "qaScope": "e2e",
            },
        ]
    }
    testplan = {"testCases": [{"id": "TC1", "mapped_requirements": ["R1"]}], "coverage": {}}
    prefetch = {
        "prs": [
            {
                "org": "wbd-msc",
                "repo": "demo",
                "number": 42,
                "view": {"state": "OPEN", "title": "Fix feature"},
                "checks": "build fail",
            }
        ]
    }
    (cache / "MSC-ACT-mapping.json").write_text(json.dumps(mapping), encoding="utf-8")
    (cache / "MSC-ACT-testplan.json").write_text(json.dumps(testplan), encoding="utf-8")
    (cache / "MSC-ACT-prefetch.json").write_text(json.dumps(prefetch), encoding="utf-8")

    html = build_recommended_actions_list("MSC-ACT", root=tmp_path)
    assert "Implement R1" in html
    assert "Merge PR" in html
    assert "Fix CI" in html
    assert "Verify R1" in html
    assert "Execute test plan" in html


def test_auto_gaps_list_uses_utf8_em_dash_not_mojibake():
    from coverage_report_helpers import build_implementation_gaps_list

    gaps, summary, _ = build_implementation_gaps_list(
        {"requirements": []},
        {"coverage": {"uncoveredJiraRequirements": ["R4"]}},
    )
    assert "— no mapped test case in test plan" in gaps
    assert "â€" not in gaps
    assert "·" in summary or summary == "None"


def test_qa_scope_summary_breakdown():
    reqs = [
        {"id": "R1", "qaScope": "e2e"},
        {"id": "R2", "qaScope": "manual"},
        {"id": "R3", "qaScope": "e2e"},
    ]
    needing = {"R1", "R2", "R3"}
    summary = _format_qa_scope_summary(reqs, needing)
    assert "3 item(s)" in summary
    assert "2 E2E" in summary
    assert "1 Manual" in summary


def test_qa_scope_detail_lists_ids_and_test_cases():
    reqs = [
        {"id": "R2", "qaScope": "e2e", "devTestStatus": "missing"},
        {"id": "L1", "qaScope": "regression", "devTestStatus": "partial"},
    ]
    detail = _format_qa_scope_detail(reqs, {"R2", "L1"}, ["TC2", "TC5"])
    assert "Jira: R2" in detail
    assert "LADR: L1" in detail
    assert "TC2" in detail and "TC5" in detail


def test_qa_scope_detail_all_dev_covered():
    reqs = [
        {"id": "R1", "qaScope": "none", "devTestStatus": "covered"},
        {"id": "R2", "qaScope": "none", "devTestStatus": "covered"},
    ]
    detail = _format_qa_scope_detail(reqs, set(), [])
    assert "All scored requirements dev-covered" in detail


def test_open_gaps_detail_names_requirements_and_ci():
    mapping = {
        "requirements": [
            {"id": "R3", "codeStatus": "missing", "devTestStatus": "missing", "owner": "dev"},
            {"id": "R4", "codeStatus": "implemented", "devTestStatus": "missing", "owner": "dev"},
        ]
    }
    tp = {
        "coverage": {
            "uncoveredJiraRequirements": ["R4"],
            "uncoveredLadrRequirements": ["L5"],
        }
    }
    prefetch = {
        "prs": [
            {
                "org": "wbd-msc",
                "repo": "demo",
                "number": 99,
                "checks": "unit tests failing",
            }
        ]
    }
    detail = build_open_gaps_detail(
        mapping, tp, prefetch=prefetch, gap_summary="0 High · 3 Med"
    )
    assert "Test plan gap — Jira R4" in detail
    assert "Test plan gap — LADR L5" in detail
    assert "No PR code — R3" in detail
    assert "No dev tests — R4" in detail
    assert "CI failing" in detail
    assert "§6" not in detail


def test_open_gaps_detail_high_count_points_to_section_6():
    mapping = {
        "requirements": [
            {
                "id": "R3",
                "text": "Pick-genie logic",
                "codeStatus": "implemented",
                "devTestStatus": "partial",
                "owner": "shared",
            },
            {
                "id": "R4",
                "text": "Fix must be validated in SIT using provided test data",
                "codeStatus": "partial",
                "devTestStatus": "partial",
                "owner": "qa",
            },
        ]
    }
    tp = {
        "coverage": {
            "uncoveredJiraRequirements": ["R4"],
            "uncoveredLadrRequirements": ["L5"],
        }
    }
    prefetch = {
        "prs": [
            {
                "org": "wbd-msc",
                "repo": "demo",
                "number": 1,
                "checks": "build failed",
            }
        ]
    }
    detail = build_open_gaps_detail(
        mapping, tp, prefetch=prefetch, gap_summary="0 High · 10 Med"
    )
    assert "see §6 for full list" in detail
    assert "Test plan gaps" in detail
    assert "Partial dev tests" in detail
    assert "SIT validation" in detail
    assert "CI failures" in detail
    assert "Test plan gap — Jira R4" not in detail


def test_build_qa_ownership_fields_includes_scope_detail(tmp_path: Path):
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    mapping = {
        "requirements": [
            {
                "id": "R2",
                "text": "Monitor UI visibility",
                "devTestStatus": "missing",
                "qaScope": "e2e",
                "owner": "shared",
            },
        ]
    }
    testplan = {
        "testCases": [{"id": "TC2", "mapped_requirements": ["R2"]}],
    }
    (cache / "MSC-DET-mapping.json").write_text(json.dumps(mapping), encoding="utf-8")
    (cache / "MSC-DET-testplan.json").write_text(json.dumps(testplan), encoding="utf-8")

    fields = build_qa_ownership_fields("MSC-DET", root=tmp_path)
    assert "1 item(s)" in fields["qaScopeSummary"]
    assert "Jira: R2" in fields["qaScopeDetail"]
    assert "TC2" in fields["qaScopeDetail"]
