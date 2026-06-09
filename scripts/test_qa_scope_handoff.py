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
    _qa_scope_needs_qa_execution,
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
    from build_coverage_report import _auto_gaps

    gaps, summary, _ = _auto_gaps(
        {"requirements": []},
        {"coverage": {"uncoveredJiraRequirements": ["R4"]}},
    )
    assert "— no mapped test case in test plan" in gaps
    assert "â€" not in gaps
    assert "·" in summary or summary == "None"
