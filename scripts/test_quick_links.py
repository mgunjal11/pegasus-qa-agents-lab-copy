#!/usr/bin/env python3
"""Tests for coverage report quick navigation links."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from coverage_report_helpers import build_quick_links  # noqa: E402


def test_build_quick_links_includes_confluence_for_msc204417():
    html = build_quick_links("MSC-204417")
    assert "quick-links" in html
    assert "Jira</a>" in html
    assert "Test plan (SharePoint)</a>" in html
    assert "2984378410" in html
    assert "Confluence</a>" in html or "LADR" in html
