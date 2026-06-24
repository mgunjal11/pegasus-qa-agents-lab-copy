#!/usr/bin/env python3
"""Tests for release readiness score computation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from report_helpers.sections import compute_release_score  # noqa: E402


def test_release_score_all_hundred_no_gaps_no_ci():
    score, cls = compute_release_score(100.0, 100.0, 100.0, high_gaps=0, med_gaps=0, ci_pct=None)
    assert score == 100
    assert cls == "metric-good"


def test_release_score_uses_parsed_medium_gap_penalty():
    # 4 medium gaps → penalty 100 - 4*7 = 72
    score, _ = compute_release_score(100.0, 100.0, 100.0, high_gaps=0, med_gaps=4, ci_pct=95.0)
    expected = round(100 * 0.3 + 100 * 0.25 + 100 * 0.25 + 95 * 0.1 + 72 * 0.1)
    assert score == expected


def test_release_score_not_pulled_by_fake_ci_placeholder():
    # Old bug: hardcoded 70% CI always applied. Without CI, perfect metrics should score 100.
    score, _ = compute_release_score(100.0, 100.0, 100.0, high_gaps=0, med_gaps=0, ci_pct=None)
    assert score == 100


def test_release_score_msc205625_like_attached_plan():
    # Attached plan 77.8%, dev/code 100%, CI ~95%, 4 medium gaps
    score, cls = compute_release_score(100.0, 100.0, 77.8, high_gaps=0, med_gaps=4, ci_pct=95.0)
    assert 88 <= score <= 92
    assert cls == "metric-good"
