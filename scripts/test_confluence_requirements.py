#!/usr/bin/env python3
"""Tests for LADR / Confluence requirement mapping."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from confluence_requirements import (  # noqa: E402
    build_ladr_traceability,
    collect_confluence_page_links,
    compute_testplan_coverage,
    map_testcases_to_requirements,
    merge_requirement_sets,
    parse_ladr_ess_requirements,
)


@dataclass
class FakeTC:
    summary: str
    story: str = "MSC-204417"
    steps: dict[str, str] = field(default_factory=dict)
    mapped_requirements: list[str] = field(default_factory=list)


def test_parse_ladr_ess_requirements():
    body = "ESS demandAcknowledgment orderStatus STATUS_FAILURE 8000 STATUS_ERROR 9000"
    reqs = parse_ladr_ess_requirements(body)
    assert len(reqs) >= 12
    assert any(r["task"] == "orderStatus" and r["status"] == "Failure" for r in reqs)


def test_map_caption_monitoring_scenarios():
    jira = [
        {"id": "R1", "text": "V2 messaging in ESS is implemented"},
        {"id": "R2", "text": "Caption statuses are propagated"},
        {"id": "R3", "text": "LADR status codes STATUS_ERROR 9000 and STATUS_FAILURE 8000"},
    ]
    ladr = parse_ladr_ess_requirements("ESS section with orderStatus registrationStatus")
    reqs = merge_requirement_sets(jira, ladr)
    cases = [
        FakeTC(
            "Demand Acknowledged – Completed status",
            steps={
                "given": "Given a CAT demand is received",
                "when": "When the system acknowledges the demand",
                "then": "Then demandAcknowledgment milestone is marked Completed",
            },
        ),
        FakeTC(
            "Caption order failure when failure response is received",
            steps={
                "given": "Given Zoo request fails",
                "when": "When failure response is received",
                "then": "Then order Status is Failure",
            },
        ),
    ]
    map_testcases_to_requirements(cases, reqs)
    assert "R1" in cases[0].mapped_requirements
    assert "R2" in cases[0].mapped_requirements
    assert any(m.startswith("L") for m in cases[0].mapped_requirements)
    assert "R3" in cases[1].mapped_requirements or any("L" in m for m in cases[1].mapped_requirements)

    cov = compute_testplan_coverage(cases, reqs, jira_requirements=jira, ladr_requirements=ladr)
    assert cov["jiraRequirementsCovered"] >= 2
    assert cov["testplanCoveragePct"] != 0

    trace = build_ladr_traceability(cases, ladr)
    assert trace
    assert any(r["id"] == "L1" and r["mapped"] for r in trace)


def test_collect_confluence_page_links_from_issue_caches():
    """MSC-204417 analysis cache embeds LADR wiki URL even when confluence.json has no pages."""
    links = collect_confluence_page_links("MSC-204417")
    assert links
    assert any("2984378410" in link["url"] for link in links)
    assert any(
        "LADR" in link["title"] or "Captions" in link["title"] or "2984378410" in link["url"]
        for link in links
    )


def test_collect_confluence_page_links_dedupes():
    links = collect_confluence_page_links("MSC-205625")
    urls = [link["url"] for link in links]
    assert urls
    assert len(urls) == len(set(urls))


if __name__ == "__main__":
    test_parse_ladr_ess_requirements()
    test_map_caption_monitoring_scenarios()
    print("ok")
