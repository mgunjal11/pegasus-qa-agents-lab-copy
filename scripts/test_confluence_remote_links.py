"""Tests for Confluence URL extraction from Jira remote links."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from confluence_requirements import (  # noqa: E402
    extract_confluence_from_jira_links,
    merge_confluence_url_lists,
)


def test_remote_link_page_id():
    jira = {
        "remoteLinks": [
            {
                "url": "https://wbdstreaming.atlassian.net/wiki/pages/viewpage.action?pageId=3207659643",
                "title": "DirecTV Spec",
            }
        ]
    }
    refs = extract_confluence_from_jira_links(jira)
    assert len(refs) == 1
    assert refs[0]["pageId"] == "3207659643"


def test_merge_dedupes():
    a = [{"pageId": "1", "url": "https://x/1", "context": ""}]
    b = [{"pageId": "1", "url": "https://x/1b", "context": ""}, {"pageId": "2", "url": "https://x/2", "context": ""}]
    merged = merge_confluence_url_lists(a, b)
    assert len(merged) == 2
