"""Tests for Gap fill marker on gap-supplement test cases in reports."""

from report_helpers.sections import (
    format_tc_ids_plain,
    render_testplan_tc_id_cell,
    render_testplan_rows,
)


def test_render_testplan_tc_id_cell_shows_gap_fill_badge():
    primary = {"id": "TC1", "source_file": "Domino Test Plan.xlsx"}
    gap = {"id": "TC6", "source_file": "MSC-205625-gap-supplement.xlsx", "gap_supplement": True}
    assert render_testplan_tc_id_cell(primary) == "TC1"
    assert "TC6" in render_testplan_tc_id_cell(gap)
    assert "badge-gap-fill" in render_testplan_tc_id_cell(gap)
    assert "Gap fill" in render_testplan_tc_id_cell(gap)


def test_format_tc_ids_plain_marks_gap_supplement():
    cases = [
        {"id": "TC5", "source_file": "Domino Test Plan.xlsx"},
        {"id": "TC6", "gap_supplement": True, "source_file": "MSC-205625-gap-supplement.xlsx"},
    ]
    assert format_tc_ids_plain(["TC5", "TC6"], cases) == "TC5, TC6 (Gap fill)"


def test_render_testplan_rows_includes_gap_badge_in_tc_column():
    html = render_testplan_rows(
        [
            {
                "id": "TC6",
                "summary": "MSC-205625_gap case (maps R4)",
                "gap_supplement": True,
                "source_file": "MSC-205625-gap-supplement.xlsx",
                "mapped_requirements": ["R4"],
                "steps": {
                    "given": "Given: x",
                    "when": "When: y",
                    "then": "Then: z",
                },
            }
        ]
    )
    assert "badge-gap-fill" in html
    assert "TC6" in html
