"""Tests for semantic_mapping_boost and run_coverage_validator preflight wiring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from semantic_mapping_boost import apply_semantic_boost  # noqa: E402


def test_semantic_boost_raises_code_score_from_comments():
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
