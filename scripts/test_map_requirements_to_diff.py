"""Tests for requirement-to-diff mapping."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from map_requirements_to_diff import (  # noqa: E402
    _collect_requirements,
    _overlap_score,
    _status_from_score,
    _tokens,
    map_requirements,
)
from coverage_report_helpers import build_req_coverage_detail, render_requirement_rows_from_mapping  # noqa: E402


def test_overlap_score():
    tokens = _tokens("passport re-fetch from FMAM when fulfillmentType full")
    score = _overlap_score(tokens, "passport_manager fulfillmentType full incremental")
    assert score > 0.2


def test_status_from_score():
    assert _status_from_score(0.4) == "implemented"
    assert _status_from_score(0.2) == "partial"


def test_collect_requirements_includes_ladr():
    jira, ladr = _collect_requirements(
        {"requirements": [{"id": "R1", "text": "Jira AC one"}]},
        {
            "jiraRequirements": [{"id": "R1", "text": "Jira AC one"}],
            "ladrRequirements": [{"id": "L1", "text": "MVP Full passport attached", "source": "ladr"}],
        },
    )
    assert len(jira) == 1
    assert jira[0]["id"] == "R1"
    assert len(ladr) == 1
    assert ladr[0]["id"] == "L1"


def test_map_requirements_includes_ladr_rows(tmp_path):
    key = "MSC-TEST"
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    (cache / f"{key}-jira.json").write_text(
        json.dumps({"requirements": [{"id": "R1", "text": "passport incremental full"}]}),
        encoding="utf-8",
    )
    (cache / f"{key}-testplan.json").write_text(
        json.dumps(
            {
                "jiraRequirements": [{"id": "R1", "text": "passport incremental full"}],
                "ladrRequirements": [
                    {"id": "L1", "text": "MVP Full passport always attached", "source": "ladr"},
                ],
                "coverage": {},
                "testCases": [],
            }
        ),
        encoding="utf-8",
    )
    (cache / f"{key}-prefetch.json").write_text(
        json.dumps(
            {
                "prs": [
                    {
                        "diff": "passport_manager incremental full fulfillment",
                        "diffNames": ["src/utils/passport_manager.py", "tests/unit/test_passport.py"],
                        "view": {"state": "MERGED", "title": "passport fix"},
                        "org": "wbd-msc",
                        "repo": "pegasus-pick-genie",
                        "number": 1,
                        "url": "https://github.com/wbd-msc/pegasus-pick-genie/pull/1",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = map_requirements(key, root=tmp_path)
    ids = [r["id"] for r in payload["requirements"]]
    assert ids == ["R1", "L1"]
    assert payload["jiraRequirementCount"] == 1
    assert payload["ladrRequirementCount"] == 1
    assert payload["requirements"][1]["source"] == "ladr"

    out = cache / f"{key}-mapping.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    rows = render_requirement_rows_from_mapping(key, root=tmp_path)
    assert "L1" in rows
    assert "LADR" in rows
    assert build_req_coverage_detail(payload) == "1 Jira + 1 LADR scored from PR diff mapping"
