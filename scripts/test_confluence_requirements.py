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
    collect_ladr_page_links,
    compute_testplan_coverage,
    dedupe_ladr_requirements,
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


def test_compute_testplan_coverage_dedupes_duplicate_ladr_ids():
    """MSC-204417: same L1–L12 parsed from two Confluence pages must not halve coverage %."""
    jira = [{"id": f"R{i}", "text": f"ac{i}"} for i in range(1, 4)]
    ladr = [{"id": f"L{i}", "task": "orderStatus", "status": f"Status{i}"} for i in range(1, 13)]
    ladr_dup = ladr + list(ladr)
    assert len(dedupe_ladr_requirements(ladr_dup)) == 12

    mapped = [f"R{i}" for i in range(1, 4)] + [f"L{i}" for i in range(1, 13)]
    cases = [FakeTC("all reqs", mapped_requirements=mapped)]
    cov = compute_testplan_coverage(
        cases,
        merge_requirement_sets(jira, ladr_dup),
        jira_requirements=jira,
        ladr_requirements=ladr_dup,
    )
    assert cov["ladrRequirementCount"] == 12
    assert cov["jiraRequirementCount"] == 3
    assert cov["requirementCount"] == 15
    assert cov["requirementsCovered"] == 15
    assert cov["testplanCoveragePct"] == 100.0
    assert cov["uncoveredLadrRequirements"] == []

    trace = build_ladr_traceability(cases, ladr_dup)
    assert len(trace) == 12


def test_collect_confluence_page_links_from_issue_caches(fixture_repo_root):
    """MSC-204417 analysis cache embeds LADR wiki URL even when confluence.json has no pages."""
    links = collect_confluence_page_links("MSC-204417", fixture_repo_root)
    assert links
    assert any("2984378410" in link["url"] for link in links)
    assert any(
        "LADR" in link["title"] or "Captions" in link["title"] or "2984378410" in link["url"]
        for link in links
    )


def test_collect_confluence_page_links_dedupes(fixture_repo_root):
    links = collect_confluence_page_links("MSC-205625", fixture_repo_root)
    urls = [link["url"] for link in links]
    assert urls
    assert len(urls) == len(set(urls))


def test_collect_ladr_page_links_excludes_non_ladr_remote_links(fixture_repo_root):
    """MSC-204417: LADR wiki yes; deployment / grooming remote links no."""
    ladr_links = collect_ladr_page_links("MSC-204417", fixture_repo_root)
    assert any("2984378410" in link["url"] for link in ladr_links)
    assert not any("3621063040" in link["url"] for link in ladr_links)
    assert not any("Deployment" in (link.get("title") or "") for link in ladr_links)


def test_collect_ladr_page_links_includes_passport_design_page(fixture_repo_root):
    """MSC-205625: passport design page has L1…Ln even without LADR in title."""
    ladr_links = collect_ladr_page_links("MSC-205625", fixture_repo_root)
    assert any("3480813727" in link["url"] for link in ladr_links)


if __name__ == "__main__":
    test_parse_ladr_ess_requirements()
    test_map_caption_monitoring_scenarios()
    print("ok")
