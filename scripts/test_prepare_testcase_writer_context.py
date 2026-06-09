"""Tests for prepare_testcase_writer_context.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_testcase_writer_context import extract_jira_requirements, load_json  # noqa: E402


def test_extract_jira_requirements_from_cache_shape():
    jira = {
        "requirements": [
            {"id": "R1", "text": "House format skips normalization"},
            {"id": "R2", "text": "Non-house normalizes"},
        ]
    }
    reqs = extract_jira_requirements(jira)
    assert len(reqs) == 2
    assert reqs[0]["id"] == "R1"


def test_msc204417_cache_has_ladr_mode():
    cache = ROOT / "reports" / ".cache" / "MSC-204417-confluence.json"
    if not cache.exists():
        return
    conf = load_json(cache)
    ladr = conf.get("ladrRequirements") or []
    assert ladr, "expected LADR in MSC-204417 fixture cache"


def test_msc209330_cache_jira_only():
    jira = load_json(ROOT / "reports" / ".cache" / "MSC-209330-jira.json")
    conf = load_json(ROOT / "reports" / ".cache" / "MSC-209330-confluence.json")
    if not jira:
        return
    ladr = conf.get("ladrRequirements") or []
    assert not ladr
