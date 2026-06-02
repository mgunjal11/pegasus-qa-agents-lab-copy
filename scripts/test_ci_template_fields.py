#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from coverage_report_helpers import ci_coverage_report_fields, coverage_to_template_fields


def test_coverage_to_template_fields():
    fields = coverage_to_template_fields(
        {"linePct": 95.3, "branchPct": 94.5, "lineSource": "Sonar", "branchSource": "Sonar"}
    )
    assert fields["{{CI_LINE_COVERAGE}}"] == "95.3%"
    assert fields["{{CI_BRANCH_COVERAGE}}"] == "94.5%"
    assert fields["lineCoverage"] == "95.3%"
    assert "metric-good" in fields["{{CI_LINE_CLASS}}"]


def test_ci_coverage_report_fields_from_prefetch_cache():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cache_dir = root / "reports" / ".cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "MSC-TEST-prefetch.json").write_text(
            json.dumps(
                {
                    "prs": [
                        {
                            "ciCoverage": {"linePct": 88.0, "branchPct": 77.5},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        fields = ci_coverage_report_fields("MSC-TEST", root)
        assert fields["{{CI_LINE_COVERAGE}}"] == "88.0%"
        assert fields["{{CI_BRANCH_COVERAGE}}"] == "77.5%"
        assert "{{CI_LINE_COVERAGE}}" not in fields.values()
