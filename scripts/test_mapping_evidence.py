"""Tests for symbol/pytest-name mapping evidence."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mapping_evidence import (  # noqa: E402
    extract_diff_context,
    pr_gated_code_status,
    pr_gated_dev_test_status,
    rank_matched_files,
    score_requirement_evidence,
)


def test_extract_test_functions_from_diff_only_not_module_stems():
    diff = """
+++ b/tests/unit/test_passport_manager.py
+def test_passport_retained_incremental_full():
+    assert True
+def merge_passport():
+    pass
"""
    ctx = extract_diff_context(diff, [], ["tests/unit/test_passport_manager.py"])
    assert "test_passport_retained_incremental_full" in ctx.test_functions
    assert "test_passport_manager" not in ctx.test_functions
    assert "merge_passport" in ctx.symbols


def test_score_matches_test_name_in_pr_diff():
    diff = "+def test_passport_retained_incremental_full():\n"
    ctx = extract_diff_context(
        diff,
        ["src/utils/passport_manager.py"],
        ["tests/unit/test_passport_manager.py"],
    )
    req_tokens = ["passport", "retained", "incremental", "full"]
    result = score_requirement_evidence(
        "passport retained incremental full",
        req_tokens,
        ctx,
        ["src/utils/passport_manager.py"],
        ["tests/unit/test_passport_manager.py"],
        ["passport"],
    )
    assert result["matchedTests"]
    assert float(result["testScore"]) >= 0.3


def test_module_in_pr_without_diff_test_is_not_covered():
    ctx = extract_diff_context("", ["src/utils/passport_manager.py"], ["tests/unit/test_passport_manager.py"])
    result = score_requirement_evidence(
        "passport retained incremental full",
        ["passport", "retained", "incremental", "full"],
        ctx,
        ["src/utils/passport_manager.py"],
        ["tests/unit/test_passport_manager.py"],
        ["passport"],
    )
    status = pr_gated_dev_test_status(
        float(result["testScore"]),
        matched_tests=list(result["matchedTests"]),
        test_module_hits=list(result["testModuleHits"]),
        test_files_in_pr=True,
    )
    assert status in ("partial", "missing")
    assert not result["matchedTests"]


def test_negative_requirement_filters_generic_passport_tests():
    diff = "+def test_passport_attached_in_pick_phase():\n"
    ctx = extract_diff_context(diff, ["src/utils/passport_manager.py"], ["tests/unit/test_passport.py"])
    result = score_requirement_evidence(
        "MDU in Pick — passport not attached (expected)",
        ["passport", "attached", "pick"],
        ctx,
        ["src/utils/passport_manager.py"],
        ["tests/unit/test_passport.py"],
        ["passport"],
    )
    assert result["matchedTests"] == []


def test_pr_gated_code_requires_production_file():
    assert pr_gated_code_status(0.9, []) == "partial"
    assert pr_gated_code_status(0.9, ["src/utils/passport_manager.py"]) == "implemented"


def test_rank_matched_files_prefers_src_over_samples():
    ranked = rank_matched_files(
        [
            "tests/samples/partner_config/domino-clear.json",
            "src/utils/passport_manager.py",
            "conftest.py",
        ]
    )
    assert ranked[0] == "src/utils/passport_manager.py"
