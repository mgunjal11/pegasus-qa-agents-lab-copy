"""Verdict must align with release readiness score bands."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_helpers.sections import compute_release_score, derive_release_verdict  # noqa: E402


def test_msc204417_like_low_score_is_fail_not_pass_with_gaps():
    """63% code, 0% dev tests, 100% plan, 26 Med → ~49% readiness → Fail."""
    verdict, css, _, score, score_cls = derive_release_verdict(
        63.3, 0.0, 100.0, "0 High · 26 Med", mode="pragmatic"
    )
    assert score < 50
    assert score_cls == "metric-fail"
    assert verdict == "Fail"
    assert css == "fail"


def test_release_score_bands_match_pass_pass_gaps_fail():
    assert compute_release_score(100, 100, 100, med_gaps=0)[1] == "metric-good"
    assert compute_release_score(80, 80, 80, med_gaps=2)[1] == "metric-warn"
    assert compute_release_score(40, 0, 100, med_gaps=10)[1] == "metric-fail"


def test_high_score_no_med_is_pass():
    verdict, css, _, score, score_cls = derive_release_verdict(
        100.0, 100.0, 100.0, "None", mode="pragmatic"
    )
    assert score >= 85
    assert score_cls == "metric-good"
    assert verdict == "Pass"
    assert css == "pass"


def test_warn_band_is_pass_with_gaps():
    verdict, css, _, score, _ = derive_release_verdict(
        94.0, 87.5, 77.8, "0 High · 7 Med", mode="pragmatic", ci_pct=95.0
    )
    assert 50 <= score < 85
    assert verdict == "Pass with gaps"
    assert css == "pass-gaps"
