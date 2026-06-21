"""§5 Requirements traceability — compact + expandable Evidence column."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coverage_report_helpers import (  # noqa: E402
    _render_trace_evidence_cell,
    _summarize_trace_evidence,
)


def test_summarize_drops_fixtures_from_visible_keeps_in_extra():
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
    visible, extra = _summarize_trace_evidence(files, tests)
    assert len(visible) <= 3
    assert all("samples/" not in label and not label.endswith(".json") for label, kind, _ in visible if kind == "file")
    assert len(extra) >= 3


def test_render_trace_evidence_compact_with_expandable_more():
    html = _render_trace_evidence_cell(
        [
            "src/utils/passport_manager.py",
            "tests/unit/utils/test_passport_manager.py",
            "tests/unit/foo/test_incrementals.py",
            "tests/data/fixture.json",
        ],
        "high",
        matched_tests=[
            "test_scenario_4_fmam_when_passport_not_in_fulfillment_history",
            "test_other_name",
        ],
    )
    assert "evidence-list" in html
    assert "evidence-expand" in html
    assert "<details" in html
    assert "<summary" in html
    assert "+2 more" in html or "+3 more" in html or "+4 more" in html
    assert "evidence-list-extra" in html
    assert "utils/passport_manager.py" in html
    assert "conf-badge" in html
    assert "high" in html


def test_render_trace_evidence_note_only_when_empty():
    html = _render_trace_evidence_cell([], "medium", evidence_note="SIT validation AC — QA manual.")
    assert "evidence-note" in html
    assert "SIT validation" in html
    assert "evidence-list" not in html
    assert "evidence-expand" not in html
