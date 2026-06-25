"""Tests for full Scenario text in §3 Attached test plan validation."""

from report_helpers.common import format_testplan_scenario
from report_helpers.sections import render_testplan_rows

JIRA_REQS = [
    {
        "id": "R3",
        "text": "CAFE uses instructions.forensicWatermark.enabled to decide whether to perform audio watermarking",
    },
    {
        "id": "R5",
        "text": (
            "SNAP XML watermark logs include content identifiers when contentId is present "
            "in MediaRequestEvent (logs incomplete without it)"
        ),
    },
]


def test_format_testplan_scenario_resolves_truncated_auto_generated_summary():
    tc = {
        "id": "TC3",
        "summary": "MSC-208859_CAFE_uses_instructionsforensicWatermarkenabled_to_decid (maps R3)",
        "mapped_requirements": ["R3", "R4"],
    }
    scenario = format_testplan_scenario(tc, JIRA_REQS)
    assert scenario == JIRA_REQS[0]["text"]
    assert "forensicWatermarkenabled_to_decid" not in scenario


def test_format_testplan_scenario_keeps_domino_section_and_summary():
    tc = {
        "id": "TC1",
        "section": "Incremental as Full",
        "summary": "Demand ACK V2 ESS",
    }
    assert format_testplan_scenario(tc, JIRA_REQS) == "Incremental as Full · Demand ACK V2 ESS"


def test_format_testplan_scenario_keeps_attached_summary_without_auto_prefix():
    tc = {
        "id": "TC9",
        "summary": "Verify passport incremental-as-full on PICK",
        "mapped_requirements": ["R1"],
    }
    assert format_testplan_scenario(tc, JIRA_REQS) == "Verify passport incremental-as-full on PICK"


def test_render_testplan_rows_shows_full_scenario_text():
    html = render_testplan_rows(
        [
            {
                "id": "TC5",
                "summary": "MSC-208859_SNAP_XML_watermark_logs_include_content_identifiers_whe (maps R5)",
                "mapped_requirements": ["R5"],
                "steps": {"given": "Given: x", "when": "When: y", "then": "Then: z"},
            }
        ],
        JIRA_REQS,
    )
    assert JIRA_REQS[1]["text"] in html
    assert "identifiers_whe" not in html
