"""Tests for symbol/pytest-name mapping evidence."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mapping_evidence import (  # noqa: E402
    extract_diff_context,
    rank_matched_files,
    score_requirement_evidence,
)


def test_extract_test_functions_from_diff():
    diff = """
+++ b/tests/unit/test_passport_manager.py
+def test_passport_retained_incremental_full():
+    assert True
+def merge_passport():
+    pass
"""
    ctx = extract_diff_context(diff, [], ["tests/unit/test_passport_manager.py"])
    assert "test_passport_retained_incremental_full" in ctx.test_functions
    assert "merge_passport" in ctx.symbols


def test_score_matches_test_name():
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
    assert float(result["testScore"]) >= 0.25


def test_rank_matched_files_prefers_src_over_samples():
    ranked = rank_matched_files(
        [
            "tests/samples/partner_config/domino-clear.json",
            "src/utils/passport_manager.py",
            "conftest.py",
        ]
    )
    assert ranked[0] == "src/utils/passport_manager.py"
