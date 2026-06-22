"""Tests for jira_story.py and fetch_jira_story.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from jira_story import extract_pr_urls, extract_requirements_from_issue, normalize_mcp_issue  # noqa: E402


def test_msc205625_infer_requirements_from_description():
    cache_path = ROOT / "reports" / ".cache" / "MSC-205625-jira.json"
    if not cache_path.exists():
        return
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    probe = dict(data)
    probe.pop("requirements", None)
    reqs = extract_requirements_from_issue(probe)
    ids = [r["id"] for r in reqs]
    assert "R1" in ids
    assert "R4" in ids
    assert len(ids) == 4
    r4 = next(r for r in reqs if r["id"] == "R4")
    assert "SIT" in r4["text"]
    assert "37ea180e" in r4["text"]


def test_msc213475_ac_numbered_requirement_extraction():
    cache_path = ROOT / "reports" / ".cache" / "MSC-213475-jira.json"
    if not cache_path.exists():
        return
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    probe = dict(data)
    probe.pop("requirements", None)
    reqs = extract_requirements_from_issue(probe)
    ids = [r["id"] for r in reqs]
    assert len(ids) == 10
    assert ids == [f"R{i}" for i in range(1, 11)]


def test_extract_pr_urls_from_comments():
    data = {
        "comments": [
            {
                "body": "PR1 - https://github.com/wbd-msc/pegasus-pick-genie/pull/161\n"
                "PR2- https://github.com/wbd-msc/pegasus-encode-monitor/pull/195"
            }
        ]
    }
    urls = extract_pr_urls(data)
    assert len(urls) == 2
    assert any("pick-genie" in u for u in urls)


def test_normalize_mcp_issue_shape():
    mcp = {
        "key": "MSC-TEST",
        "fields": {
            "summary": "Sample",
            "description": "## Expected Behavior\n\nPassport retained.",
            "status": {"name": "Open"},
            "issuetype": {"name": "Bug"},
            "attachment": [],
            "comment": {"comments": []},
        },
        "comments": [],
    }
    out = normalize_mcp_issue(mcp, "MSC-TEST")
    assert out["issueKey"] == "MSC-TEST"
    assert out["summary"] == "Sample"
    assert isinstance(out.get("requirements"), list)
