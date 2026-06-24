"""Verdict mode: pragmatic vs strict."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_coverage_report import _verdict  # noqa: E402


def test_pragmatic_pass_with_gaps_on_tp_below_100():
    verdict, css, _ = _verdict(100.0, 77.8, "0 High · 6 Med", mode="pragmatic", dev_pct=100.0)
    assert verdict == "Pass with gaps"
    assert css == "pass-gaps"


def test_pragmatic_pass_when_perfect():
    verdict, css, _ = _verdict(100.0, 100.0, "None", mode="pragmatic", dev_pct=100.0)
    assert verdict == "Pass"
    assert css == "pass"


def test_strict_never_pass_with_med_gaps():
    verdict, _, _ = _verdict(100.0, 100.0, "0 High · 1 Med", mode="strict", dev_pct=100.0)
    assert verdict == "Pass with gaps"


def test_strict_pass_only_when_perfect():
    verdict, css, _ = _verdict(100.0, 100.0, "None", mode="strict", dev_pct=100.0)
    assert verdict == "Pass"
    assert css == "pass"


def test_fail_on_high_both_modes():
    for mode in ("pragmatic", "strict"):
        verdict, css, _ = _verdict(100.0, 100.0, "1 High · 0 Med", mode=mode)
        assert verdict == "Fail"
        assert css == "fail"
