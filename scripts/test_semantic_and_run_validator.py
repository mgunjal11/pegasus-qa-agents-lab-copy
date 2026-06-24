"""Tests for semantic_mapping_boost and run_coverage_validator preflight wiring."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from semantic_mapping_boost import apply_semantic_boost  # noqa: E402


def test_semantic_boost_raises_code_score_from_pr_comments_only():
    mapping = {
        "requirements": [
            {
                "id": "R1",
                "text": "Propagate caption statuses to Kafka spotlight ESS",
                "source": "jira",
                "codeScore": 0.1,
                "codeStatus": "missing",
                "devTestScore": 0.0,
                "devTestStatus": "missing",
                "owner": "dev",
                "matchedFiles": [],
                "matchedTests": [],
            }
        ]
    }
    diff = "+ # ESS caption kafka spotlight status propagation\n+ def publish_caption_event():\n"
    out = apply_semantic_boost(mapping, diff_blob=diff)
    req = out["requirements"][0]
    assert req["codeScore"] > 0.1
    assert req.get("semanticBoost") is True


def test_confluence_and_testplan_do_not_boost_code_or_dev_status():
    mapping = {
        "requirements": [
            {
                "id": "L5",
                "text": "MDU in Pick — passport not attached (expected)",
                "source": "ladr",
                "codeScore": 0.1,
                "codeStatus": "missing",
                "devTestScore": 0.05,
                "devTestStatus": "missing",
                "owner": "dev",
                "matchedFiles": [],
                "matchedTests": [],
            }
        ]
    }
    confluence = {
        "pages": [
            {
                "title": "Passport LADR",
                "essScenarios": [
                    {
                        "id": "L5",
                        "title": "MDU in Pick passport not attached expected",
                        "description": "pick phase passport not attached MDU",
                    }
                ],
            }
        ]
    }
    testplan = {
        "testCases": [
            {
                "id": "TC7",
                "summary": "MDU in Pick passport milestone",
                "mapped_requirements": ["L5"],
                "steps": {
                    "given": "Given MDU in Pick passport not attached expected",
                    "when": "When workflow runs",
                    "then": "Then milestone completed",
                },
            }
        ]
    }
    out = apply_semantic_boost(
        mapping,
        diff_blob="",
        confluence=confluence,
        testplan=testplan,
    )
    req = out["requirements"][0]
    assert req["codeStatus"] == "missing"
    assert req["devTestStatus"] == "missing"
    assert req["codeScore"] == 0.1
    assert req.get("semanticBoost") is not True
    assert req.get("designContextOverlap") == ["confluence", "testplan"]


def test_run_coverage_validator_preflight_only():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "run_coverage_validator.py"), "MSC-TEST", "--preflight-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode in (0, 1)
    assert "preflight" in result.stdout.lower() or "preflight" in result.stderr.lower()
