"""Preflight script smoke tests."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from preflight_coverage_validator import run_preflight  # noqa: E402


def test_preflight_returns_checks_structure():
    report = run_preflight()
    assert "checks" in report
    assert "ok" in report
    ids = {c["id"] for c in report["checks"]}
    assert "python" in ids
    assert "gh" in ids
    assert "template" in ids


def test_preflight_json_serializable():
    report = run_preflight("MSC-205625", verify_jira=False)
    json.dumps(report)
