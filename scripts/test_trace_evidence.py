"""§5 Requirements traceability — compact Evidence column."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coverage_report_helpers import (  # noqa: E402
    _render_trace_evidence_cell,
    _summarize_trace_evidence,
)


def test_summarize_drops_fixtures_and_caps_display():
    files = [
        "src/utils/passport_manager.py",
        "tests/unit/utils/test_passport_manager.py",
        "tests/unit/qualified_manifest_evaluate_handler/controller/test_incrementals.py",
        "tests/data/incremental_merge/cumulative_container_map.json",
        "tests/samples/deliverables/foo.json",
    ]
    tests = [
        "test_passport_manager",
        "test_scenario_4_fmam_when_passport_not_in_fulfillment_history",
        "test_other_long_name",
    ]
    items, hidden = _summarize_trace_evidence(files, tests)
    assert len(items) <= 3
    assert all("samples/" not in label and not label.endswith(".json") for label, kind, _ in items if kind == "file")
    assert hidden >= 3


def test_render_trace_evidence_compact_html():
    html = _render_trace_evidence_cell(
        [
            "src/utils/passport_manager.py",
            "tests/unit/utils/test_passport_manager.py",
            "tests/unit/foo/test_incrementals.py",
        ],
        "high",
        matched_tests=["test_scenario_4_fmam_when_passport_not_in_fulfillment_history"],
    )
    assert "evidence-list" in html
    assert html.count("<li>") <= 4
    assert "utils/passport_manager.py" in html
    assert "conf-badge" in html
    assert "high" in html


def test_render_trace_evidence_note_only_when_empty():
    html = _render_trace_evidence_cell([], "medium", evidence_note="SIT validation AC — QA manual.")
    assert "evidence-note" in html
    assert "SIT validation" in html
    assert "evidence-list" not in html
