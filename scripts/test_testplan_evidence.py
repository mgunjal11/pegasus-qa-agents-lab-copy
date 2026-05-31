#!/usr/bin/env python3
"""Tests for test plan evidence fallback (Mascot links vs Edit/Job/Request IDs)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from coverage_report_helpers import render_testplan_evidence  # noqa: E402
from testplan_evidence import extract_testcase_evidence_ids  # noqa: E402


def test_extract_edit_and_media_request_from_jira_ac():
    tc = {
        "id": "TC1",
        "summary": "SIT passport validation",
        "steps": {},
        "mapped_requirements": ["R4"],
        "mascot_links": [],
    }
    jira = [
        {
            "id": "R4",
            "text": "Fix must be validated in SIT using Edit ID 37ea180e-77cc-413f-95cf-9dfcebf08cd2, Media Request fc919602-2a91-49c9-ac61-1444a5889e6a",
        }
    ]
    ids = extract_testcase_evidence_ids(tc, jira)
    values = {i["value"] for i in ids}
    assert "37ea180e-77cc-413f-95cf-9dfcebf08cd2" in values
    assert "fc919602-2a91-49c9-ac61-1444a5889e6a" in values


def test_render_prefers_mascot_over_ids():
    tc = {
        "id": "TC2",
        "summary": "scenario",
        "steps": {},
        "mapped_requirements": ["R1"],
        "mascot_links": [{"label": "SIT Mascot", "url": "https://stg.foundry.wbdapps.com/mascot/fulfill-details/abc"}],
        "evidence_ids": [{"label": "Edit ID", "value": "37ea180e-77cc-413f-95cf-9dfcebf08cd2"}],
    }
    html = render_testplan_evidence(tc)
    assert "foundry.wbdapps.com/mascot" in html
    assert "37ea180e" not in html


def test_render_ids_when_no_mascot():
    tc = {
        "id": "TC3",
        "summary": "Job id abcdef01-2345-6789-abcd-ef0123456789 run",
        "steps": {"then": "Then verify output"},
        "mapped_requirements": [],
        "mascot_links": [],
    }
    html = render_testplan_evidence(tc)
    assert "abcdef01-2345-6789-abcd-ef0123456789" in html
    assert "badge-not-verified" not in html


def test_sit_jobs_column_evidence_text():
    from testplan_evidence import extract_testcase_evidence_ids, row_evidence_text

    header = ["Summary", "Step Summary", "SIT Jobs", "Comments"]
    row = [
        "Manifestation availability",
        "Given an edit is created",
        "Edit id:  6ef01765-d63f-4f75-8281-6ad6a5594229\ncaptionGroupID:  3922db5c-e27e-4aba-b2ab-b04b51df71b4",
        "",
    ]
    evidence = row_evidence_text(header, row)
    tc = {
        "id": "TC3",
        "summary": "Manifestation availability",
        "steps": {"given": "Given an edit is created"},
        "evidence_text": evidence,
        "mascot_links": [],
    }
    ids = extract_testcase_evidence_ids(tc)
    values = {i["value"] for i in ids}
    assert "6ef01765-d63f-4f75-8281-6ad6a5594229" in values
    assert "3922db5c-e27e-4aba-b2ab-b04b51df71b4" in values


if __name__ == "__main__":
    test_extract_edit_and_media_request_from_jira_ac()
    test_render_prefers_mascot_over_ids()
    test_render_ids_when_no_mascot()
    test_sit_jobs_column_evidence_text()
    print("ok")
