"""Tests for test plan summary note text (no Domino false positives)."""

from fetch_jira_testplan import build_testplan_summary_note, format_testplan_summary_note


def test_build_note_generated_local_qmetry():
    note = build_testplan_summary_note(
        "MSC-209330",
        9,
        None,
        [{"filename": "MSC-209330-testcases.xlsx", "local": True, "source": "workspace_fallback"}],
        [{"file": "MSC-209330-testcases.xlsx", "sheet": None}],
        ["QMetry Template"],
    )
    assert "Domino" not in note
    assert "Inc as full" not in note
    assert "MSC-209330-testcases.xlsx" in note
    assert "Spec2Test" in note
    assert "QMetry Template" in note


def test_format_note_domino_sharepoint_still_works():
    note = format_testplan_summary_note(
        "MSC-205625",
        "Domino Test Plan.xlsx",
        "Inc as full",
        "Inc as Fulll",
        5,
        "passport/incremental-as-full",
    )
    assert "Domino Test Plan.xlsx" in note
    assert "Inc as full" in note
    assert "passport/incremental-as-full" in note


def test_build_note_jira_attachment():
    note = build_testplan_summary_note(
        "MSC-205625",
        5,
        {"filename": "Domino Test Plan.xlsx", "sheet": "Inc as full", "type": "sharepoint"},
        [{"filename": "Domino Test Plan.xlsx", "source": "jira_attachment"}],
        [{"file": "Domino Test Plan.xlsx", "sheet": "Inc as Fulll"}],
        ["Inc as Fulll"],
        "passport/incremental-as-full",
    )
    assert "Downloaded Domino Test Plan.xlsx from Jira attachment" in note
    assert "Inc as Fulll" in note
