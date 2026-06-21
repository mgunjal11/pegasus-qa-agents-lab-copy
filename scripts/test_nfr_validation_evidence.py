"""NFR validation (SIT) evidence must not reach high confidence from PR unit tests alone."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from map_requirements_to_diff import (  # noqa: E402
    adjust_nfr_validation_evidence,
    apply_pytest_execution_to_mapping,
    finalize_mapping_evidence,
)

R4_TEXT = (
    "Fix must be validated in SIT using provided test data "
    "(Edit ID 37ea180e-77cc-413f-95cf-9dfcebf08cd2, Media Request fc919602-2a91-49c9-ac61-1444a5889e6a)"
)


def _sit_validation_row(**overrides):
    row = {
        "id": "R4",
        "text": R4_TEXT,
        "requirementType": "non_functional",
        "nfrCategory": "validation",
        "codeStatus": "implemented",
        "devTestStatus": "covered",
        "devTestScore": 0.8,
        "confidence": "high",
        "matchedFiles": [
            "tests/unit/test_caption.py",
            "tests/conftest.py",
            "src/workflow/caption.py",
        ],
        "matchedTests": ["test_caption_merge", "test_conftest_fixture"],
    }
    row.update(overrides)
    return row


def test_sit_validation_strips_unit_tests_and_caps_confidence():
    out = adjust_nfr_validation_evidence(_sit_validation_row(), R4_TEXT)
    assert out["confidence"] in ("medium", "low")
    assert out["confidence"] != "high"
    assert out["matchedTests"] == []
    assert all("/src/" in f for f in out["matchedFiles"])
    assert out["devTestStatus"] == "missing"
    assert out["codeStatus"] == "partial"
    assert "SIT" in out["evidenceNote"] or "pytest" in out["evidenceNote"].lower()


def test_sit_validation_never_high_even_with_pytest_passed():
    row = _sit_validation_row(pytestPassed=True)
    out = adjust_nfr_validation_evidence(row, R4_TEXT)
    assert out["confidence"] == "medium"
    assert "pytest" in out["evidenceNote"].lower() or "SIT" in out["evidenceNote"]


def test_functional_row_untouched():
    row = {
        "id": "R1",
        "text": "Passport retained in cumulative output",
        "requirementType": "functional",
        "confidence": "high",
        "matchedTests": ["test_passport"],
        "devTestStatus": "covered",
    }
    out = adjust_nfr_validation_evidence(dict(row), row["text"])
    assert out["confidence"] == "high"
    assert out["matchedTests"] == ["test_passport"]


def test_finalize_applies_pytest_then_nfr_cap():
    mapping = {
        "requirements": [_sit_validation_row()],
    }
    execution = {
        "status": "ok",
        "passed": 3,
        "failed": 0,
        "testFiles": ["tests/unit/test_caption.py"],
    }
    out = finalize_mapping_evidence(mapping, execution)
    r4 = out["requirements"][0]
    assert r4["pytestPassed"] is True
    assert r4["confidence"] == "medium"
    assert r4["matchedTests"] == []
