"""Tests for §1 coverage % alignment with §5 traceability badges."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from map_requirements_to_diff import (  # noqa: E402
    adjust_nfr_validation_evidence,
    compute_coverage_pcts,
    finalize_mapping_evidence,
)


def test_compute_coverage_pcts_counts_partial_not_as_full():
    reqs = [
        {"id": "R1", "codeStatus": "implemented", "devTestStatus": "covered", "owner": "dev"},
        {"id": "R2", "codeStatus": "implemented", "devTestStatus": "covered", "owner": "dev"},
        {"id": "R3", "codeStatus": "implemented", "devTestStatus": "covered", "owner": "dev"},
        {"id": "R4", "codeStatus": "partial", "devTestStatus": "missing", "owner": "qa"},
        {"id": "L1", "codeStatus": "implemented", "devTestStatus": "covered", "owner": "dev"},
        {"id": "L2", "codeStatus": "implemented", "devTestStatus": "covered", "owner": "dev"},
    ]
    metrics = compute_coverage_pcts(reqs, jira_requirement_count=4, ladr_requirement_count=2)
    assert metrics["reqCoveragePct"] == round(100 * (5.5 / 6), 1)
    assert metrics["codeCoverageCounts"]["partial"] == 1
    assert "1 Partial" in metrics["reqCoverageDetail"]


def test_finalize_recomputes_pct_after_nfr_validation_cap():
    mapping = {
        "jiraRequirementCount": 1,
        "ladrRequirementCount": 0,
        "requirements": [
            {
                "id": "R4",
                "text": "Fix must be validated in SIT using provided test data",
                "source": "jira",
                "codeStatus": "implemented",
                "codeScore": 0.65,
                "devTestStatus": "partial",
                "devTestScore": 0.2,
                "owner": "dev",
                "requirementType": "non_functional",
                "nfrCategory": "validation",
                "matchedFiles": ["src/foo.py"],
                "matchedTests": ["test_foo"],
            }
        ],
    }
    out = finalize_mapping_evidence(mapping)
    assert out["requirements"][0]["codeStatus"] == "partial"
    assert out["requirements"][0]["devTestStatus"] == "missing"
    assert out["reqCoveragePct"] == 50.0


def test_dev_coverage_detail_shows_qa_excluded_and_scored_split():
    """MSC-205625-style: 9 total, R4 QA excluded → 8 dev-scored, 7 covered + 1 missing."""
    reqs = [
        {"id": "R1", "owner": "shared", "devTestStatus": "missing", "codeStatus": "implemented"},
        {"id": "R2", "owner": "dev", "devTestStatus": "covered", "codeStatus": "implemented"},
        {"id": "R3", "owner": "dev", "devTestStatus": "covered", "codeStatus": "implemented"},
        {"id": "R4", "owner": "qa", "devTestStatus": "missing", "codeStatus": "partial"},
        {"id": "L1", "owner": "dev", "devTestStatus": "covered", "codeStatus": "implemented"},
        {"id": "L2", "owner": "dev", "devTestStatus": "covered", "codeStatus": "implemented"},
        {"id": "L3", "owner": "dev", "devTestStatus": "covered", "codeStatus": "implemented"},
        {"id": "L4", "owner": "dev", "devTestStatus": "covered", "codeStatus": "implemented"},
        {"id": "L5", "owner": "dev", "devTestStatus": "covered", "codeStatus": "implemented"},
    ]
    metrics = compute_coverage_pcts(reqs, jira_requirement_count=4, ladr_requirement_count=5)
    assert metrics["devTestCoveragePct"] == 87.5
    detail = metrics["devCoverageDetail"]
    assert "3/4 Jira + 5/5 LADR" in detail
    assert "8 dev-scored" in detail
    assert "1 QA excluded" in detail
    assert "7 Covered" in detail
    assert "1 Missing" in detail
