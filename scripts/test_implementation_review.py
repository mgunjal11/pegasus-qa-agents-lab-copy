#!/usr/bin/env python3
"""Tests for §6 Implementation review auto-lists."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from coverage_report_helpers import (  # noqa: E402
    build_assumptions_list,
    build_correctly_implemented_list,
    build_implementation_gaps_list,
)


def test_correctly_implemented_includes_jira_and_ladr():
    mapping = {
        "requirements": [
            {
                "id": "R1",
                "source": "jira",
                "text": "Passport retained",
                "codeStatus": "implemented",
                "devTestStatus": "covered",
                "matchedFiles": ["src/utils/passport_manager.py"],
            },
            {
                "id": "L2",
                "source": "ladr",
                "text": "Incremental to Full",
                "codeStatus": "implemented",
                "devTestStatus": "partial",
                "matchedFiles": ["tests/unit/test_passport_manager.py"],
            },
            {
                "id": "R9",
                "text": "Not built",
                "codeStatus": "missing",
                "devTestStatus": "missing",
            },
        ]
    }
    html = build_correctly_implemented_list(mapping)
    assert "R1" in html and "(Jira)" in html
    assert "L2" in html and "(LADR)" in html
    assert "passport_manager.py" in html
    assert "R9" not in html
    assert "None" not in html


def test_implementation_gaps_includes_ci_and_partial_dev():
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
    gaps, summary, gap_class = build_implementation_gaps_list(mapping, tp, prefetch=prefetch)
    assert "R4" in gaps and "test plan" in gaps
    assert "L5" in gaps
    assert "R3" in gaps and "partial" in gaps.lower()
    assert "SIT validation" in gaps
    assert "CI" in gaps
    assert "Med" in summary
    assert gap_class == "metric-warn"


def test_assumptions_list_includes_confidence_and_disclaimer():
    mapping = {
        "requirements": [
            {"id": "R2", "confidence": "low", "evidenceNote": "keyword-only overlap"},
        ]
    }
    html = build_assumptions_list(mapping, {"status": "ok"})
    assert "R2" in html
    assert "low" in html
    assert "Mapping" in html
    assert "token overlap" in html
    assert html.count("<li>") <= 3


def test_assumptions_list_msc205625_style():
    mapping = {
        "jiraRequirementCount": 4,
        "ladrRequirementCount": 5,
        "requirements": [
            {
                "id": "R4",
                "confidence": "medium",
            },
        ],
    }
    tp = {
        "status": "ok",
        "coverage": {
            "uncoveredJiraRequirements": ["R4"],
            "uncoveredLadrRequirements": ["L5"],
        },
    }
    html = build_assumptions_list(mapping, tp)
    assert html.count("<li>") <= 3
    assert "Open questions" in html
    assert "R4" in html and "L5" in html
    assert "see §6" in html
    assert "Mapping" in html and "medium" in html
    assert "token overlap" in html
    assert "Domino" not in html
