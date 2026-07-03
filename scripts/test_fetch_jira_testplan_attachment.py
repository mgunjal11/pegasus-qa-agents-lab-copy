"""Tests for Jira test plan attachment recognition (referenced Excel filenames)."""

from __future__ import annotations

from fetch_jira_testplan import (
    is_testplan_attachment,
    referenced_testplan_filenames,
)


def test_ff_race_condition_xlsx_referenced_in_comment():
    refs = [
        {
            "filename": "FF Race Condition.xlsx",
            "sheet": "Scenario",
            "type": "sharepoint",
            "source": "jira_comment",
        }
    ]
    attachments = [{"filename": "FF Race Condition.xlsx", "content": "https://example/793299"}]
    referenced = referenced_testplan_filenames(refs, attachments)
    assert is_testplan_attachment("FF Race Condition.xlsx", referenced_filenames=referenced) is True


def test_ff_race_condition_not_recognized_without_reference():
    assert is_testplan_attachment("FF Race Condition.xlsx") is False


def test_domino_test_plan_still_recognized():
    assert is_testplan_attachment("Domino Test Plan.xlsx") is True


def test_msc_keyed_xlsx_still_recognized():
    assert is_testplan_attachment("MSC-195138-testcases.xlsx") is True
