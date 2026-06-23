"""Tests for multi-org PR prefetch and Jira dev-panel metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from jira_story import extract_pr_urls, parse_jira_dev_panel  # noqa: E402
from prefetch_coverage_inputs import fetch_pr_safe, load_jira_pr_urls  # noqa: E402


def test_parse_jira_dev_panel_count():
    fields = {
        "customfield_10000": (
            '{pullrequest={dataType=pullrequest, state=MERGED, stateCount=5}, '
            'json={"cachedValue":{"summary":{"pullrequest":{"overall":{"count":5}}}},'
            '"isStale":true}}'
        )
    }
    out = parse_jira_dev_panel(fields)
    assert out.get("githubPrCount") == 5
    assert out.get("isStale") is True


def test_extract_pr_urls_from_remote_links():
    data = {
        "comments": [],
        "remoteLinks": [
            {"url": "https://github.com/discoveryinc-cs/distribute-configuration/pull/8432"},
        ],
    }
    urls = extract_pr_urls(data)
    assert len(urls) == 1
    assert "8432" in urls[0]


def test_fetch_pr_safe_returns_error_not_raise():
    with patch("prefetch_coverage_inputs.fetch_pr", side_effect=RuntimeError("Not Found")):
        pr, err = fetch_pr_safe("discoveryinc-cs", "distribute-configuration", 8432, "https://github.com/discoveryinc-cs/distribute-configuration/pull/8432")
    assert pr is None
    assert err is not None
    assert "8432" in err.get("url", "")
    assert err.get("hint")


def test_load_jira_pr_urls(tmp_path):
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    (cache / "MSC-TEST-jira.json").write_text(
        json.dumps({"prUrls": ["https://github.com/wbd-msc/a/pull/1"]}) + "\n",
        encoding="utf-8",
    )
    urls = load_jira_pr_urls("MSC-TEST", cache)
    assert urls == ["https://github.com/wbd-msc/a/pull/1"]
