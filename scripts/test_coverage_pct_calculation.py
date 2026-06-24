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
