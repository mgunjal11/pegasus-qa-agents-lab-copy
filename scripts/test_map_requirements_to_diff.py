"""Tests for requirement-to-diff mapping."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from map_requirements_to_diff import _overlap_score, _status_from_score, _tokens  # noqa: E402


def test_overlap_score():
    tokens = _tokens("passport re-fetch from FMAM when fulfillmentType full")
    score = _overlap_score(tokens, "passport_manager fulfillmentType full incremental")
    assert score > 0.2


def test_status_from_score():
    assert _status_from_score(0.4) == "implemented"
    assert _status_from_score(0.2) == "partial"
