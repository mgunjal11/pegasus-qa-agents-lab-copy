#!/usr/bin/env python3
from ci_coverage import (
    coverage_to_report_fields,
    finalize_ci_coverage,
    merge_coverage,
    parse_codecov_comment,
    parse_cobertura_xml_snippets_log,
    parse_coverage_xml,
    parse_sonar_text,
)


def test_parse_sonar_pr_comment():
    body = (
        "95.30% Coverage (94.50% Estimated after merge)"
    )
    cov = parse_sonar_text(body)
    assert cov["linePct"] == 95.3
    assert cov["branchPct"] == 94.5
    fields = coverage_to_report_fields(cov)
    assert fields["lineCoverage"] == "95.3%"
    assert fields["branchCoverage"] == "94.5%"
    assert fields["lineClass"] == "metric-good"


def test_parse_codecov():
    body = "Coverage: 87.2% on 120 lines\nBranch coverage: 79.1%"
    cov = parse_codecov_comment(body)
    assert cov["linePct"] == 87.2
    assert cov["branchPct"] == 79.1


def test_parse_coverage_xml_line_only():
    xml = b'<?xml version="1.0" ?><coverage line-rate="0.9419" branch-rate="0" lines-covered="1540" lines-valid="1635"></coverage>'
    cov = parse_coverage_xml(xml)
    assert cov["linePct"] == 94.2
    assert "branchPct" not in cov


def test_merge_priority():
    merged = merge_coverage(
        parse_codecov_comment("Coverage: 80.0%"),
        parse_sonar_text("95.30% Coverage (94.50% Estimated after merge)"),
    )
    assert merged["linePct"] == 80.0
    assert merged["branchPct"] == 94.5


def test_parse_cobertura_branch_rate_from_log():
    log = '<coverage line-rate="0.88" branch-rate="0.72"></coverage>'
    cov = parse_cobertura_xml_snippets_log(log)
    assert cov["branchPct"] == 72.0


def test_finalize_sonar_line_only_branch_fallback():
    merged = finalize_ci_coverage(
        {
            "linePct": 77.7,
            "lineSource": "SonarQube quality gate (new code line)",
        }
    )
    assert merged["branchPct"] == 77.7
    assert "Not reported separately" in merged["branchSource"]
    fields = coverage_to_report_fields(merged)
    assert fields["branchCoverage"] == "77.7%"
