"""Tests for generate_testcases_from_requirements.py and run_coverage_validator Step 5a."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from generate_testcases_from_requirements import (  # noqa: E402
    generate_blocks,
    load_requirement_context,
    _mapped_ids_from_summary,
    uncovered_from_testplan,
)


def test_mapped_ids_from_summary():
    assert _mapped_ids_from_summary("MSC-213475_Foo (maps R2 R5)") == {"R2", "R5"}
    assert _mapped_ids_from_summary("MSC-205625_Bar (maps L5)") == {"L5"}


def test_generate_blocks_covers_r_and_l():
    ctx = {
        "jiraRequirements": [{"id": "R1", "text": "Default priority 50 when no rules enabled"}],
        "ladrRequirements": [
            {"id": "L1", "text": "demandAcknowledgment Completed", "task": "demandAcknowledgment", "status": "Completed"}
        ],
    }
    rows = generate_blocks("MSC-TEST", ctx["jiraRequirements"], ctx["ladrRequirements"])
    assert len(rows) == 6  # 2 cases x 3 rows
    assert "(maps R1)" in rows[0][0]
    assert "(maps L1)" in rows[3][0]
    assert rows[2][5].startswith("Then:")


def test_r6_decision_table_expands_to_eight_cases():
    req = {
        "id": "R6",
        "text": "Verify all 8 scenarios from the LADR decision table",
    }
    blocks = generate_blocks("MSC-TEST", [req], [])
    assert len(blocks) == 24  # 8 x 3


def test_parse_gap_ids_from_testplan_cache(tmp_path: Path):
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    (cache / "MSC-GAP-testplan.json").write_text(
        json.dumps(
            {
                "coverage": {
                    "uncoveredRequirements": ["R4"],
                    "uncoveredLadrRequirements": ["L5"],
                }
            }
        ),
        encoding="utf-8",
    )
    from generate_testcases_from_requirements import uncovered_from_testplan

    ids = uncovered_from_testplan("MSC-GAP", tmp_path)
    assert ids == ["R4", "L5"]


def test_run_coverage_validator_needs_testcase_writer_exit_when_auto_off(tmp_path: Path, monkeypatch):
    """Exit 2 when no testplan, no xlsx, and auto-generate disabled (default)."""
    key = "MSC-NOTP"
    import run_coverage_validator as rcv
    import argparse

    monkeypatch.setattr(rcv, "_testcase_xlsx_path", lambda k: tmp_path / "missing.xlsx")
    monkeypatch.setattr(
        rcv,
        "_load_testplan_cache",
        lambda k: {"status": "no_testplan"},
    )
    args = argparse.Namespace(skip_testplan=False, no_auto_generate_testplan=True)
    defaults = {"generateTestPlanIfMissing": False}
    assert rcv._should_invoke_testcase_writer(key, defaults, {}, args) is True
    assert rcv._auto_generate_enabled(defaults, {}, args) is False


def test_should_fill_gaps_only_when_attached_cases_present(tmp_path: Path, monkeypatch):
    import argparse
    import json
    import run_coverage_validator as rcv

    key = "MSC-GAPFILL"
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    monkeypatch.setattr(rcv, "_cache_dir", lambda k: cache)

    args = argparse.Namespace(skip_testplan=False, no_fill_testplan_gaps=False)
    defaults: dict = {}
    manifest: dict = {}
    no_attached = {"status": "ok", "coverage": {"attachedTestCaseCount": 0, "uncoveredRequirements": ["R1"]}}
    with_attached = {"status": "ok", "coverage": {"attachedTestCaseCount": 5, "uncoveredRequirements": ["R4"]}}

    assert rcv._should_fill_testplan_gaps(key, no_attached, defaults, manifest, args) is False
    assert rcv._should_fill_testplan_gaps(key, with_attached, defaults, manifest, args) is False

    (cache / f"{key}-testplan.json").write_text(
        json.dumps({"coverage": {"uncoveredRequirements": ["R4"], "attachedTestCaseCount": 5}}),
        encoding="utf-8",
    )
    assert rcv._should_fill_testplan_gaps(key, with_attached, defaults, manifest, args) is True


def test_msc213475_context_loads_when_cache_present():
    cache_path = ROOT / "reports" / ".cache" / "MSC-213475-jira.json"
    if not cache_path.exists():
        return
    ctx = load_requirement_context("MSC-213475", ROOT)
    assert len(ctx["jiraRequirements"]) == 10
    assert len(ctx["ladrRequirements"]) == 12


def test_generate_cli_writes_tsv(tmp_path: Path, monkeypatch):
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    key = "MSC-CLI"
    (cache / f"{key}-jira.json").write_text(
        json.dumps(
            {
                "requirements": [{"id": "R1", "text": "Accept criterion one for validation"}],
            }
        ),
        encoding="utf-8",
    )
    (cache / f"{key}-confluence.json").write_text(json.dumps({"ladrRequirements": []}), encoding="utf-8")

    import generate_testcases_from_requirements as gen

    monkeypatch.setattr(gen, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "prepare_testcase_writer_context.repo_root",
        lambda: tmp_path,
        raising=False,
    )
    monkeypatch.setattr(sys, "argv", ["generate_testcases_from_requirements.py", key])
    rc = gen.main()
    assert rc == 0
    tsv = cache / f"{key}-testcases-source.tsv"
    assert tsv.exists()
    assert "(maps R1)" in tsv.read_text(encoding="utf-8")


def test_parse_subprocess_json_pretty_printed_multiline():
    import run_coverage_validator as rcv

    stdout = json.dumps(
        {"issueKey": "MSC-TEST", "generatedCases": 13, "mode": "gap_only"},
        indent=2,
    )
    parsed = rcv._parse_subprocess_json(stdout)
    assert parsed["generatedCases"] == 13


def test_parse_subprocess_json_trailing_single_line():
    import run_coverage_validator as rcv

    stdout = "Building cases...\n" + json.dumps({"generatedCases": 2})
    parsed = rcv._parse_subprocess_json(stdout)
    assert parsed["generatedCases"] == 2


def test_generated_case_count_accepts_legacy_generated_key():
    import run_coverage_validator as rcv

    assert rcv._generated_case_count({"generated": 0, "reason": "already covered"}) == 0
    assert rcv._generated_case_count({"generatedCases": 5}) == 5


def test_should_refetch_after_gap_fill_when_supplement_exists(tmp_path: Path, monkeypatch):
    import run_coverage_validator as rcv

    key = "MSC-GAP"
    gap_xlsx = tmp_path / "testcases" / f"{key}-gap-supplement.xlsx"
    gap_xlsx.parent.mkdir(parents=True)
    gap_xlsx.write_bytes(b"xlsx")

    monkeypatch.setattr(rcv, "ROOT", tmp_path)
    # Pretty-print JSON parse failed in old _run — generatedCases missing from fallback dict
    gen_result = {"stdout": json.dumps({"generatedCases": 13}, indent=2)}
    assert rcv._should_refetch_after_generate(key, gen_result, gap_only=True) is True

    gen_result_empty = {"generated": 0, "reason": "gaps already covered in TSV"}
    assert rcv._should_refetch_after_generate(key, gen_result_empty, gap_only=True) is True
