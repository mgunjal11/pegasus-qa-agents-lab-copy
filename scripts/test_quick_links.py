#!/usr/bin/env python3
"""Tests for coverage report quick navigation links."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from coverage_report_helpers import build_quick_links  # noqa: E402


def test_build_quick_links_includes_ladr_only_for_msc204417(fixture_repo_root):
    html = build_quick_links("MSC-204417", fixture_repo_root)
    assert "quick-links" in html
    assert "Jira</a>" in html
    assert "Test plan (SharePoint)</a>" in html
    assert "2984378410" in html
    assert "LADR" in html
    assert "3621063040" not in html
    assert "Deployment" not in html
