"""Tests for merging Jira test plans with gap-supplement Excel files."""

from fetch_jira_testplan import TestCase as PlanCase, renumber_gap_supplement_cases


def _tc(tc_id: str, source_file: str, *, mapped: list[str] | None = None) -> PlanCase:
    return PlanCase(
        id=tc_id,
        summary=f"case {tc_id}",
        story="MSC-TEST",
        priority="P0",
        test_type="End to End",
        automatable="Yes",
        regression="Yes",
        source_file=source_file,
        mapped_requirements=mapped or [],
    )


def test_renumber_gap_supplement_continues_after_jira_plan():
    cases = [
        _tc("TC1", "Domino Test Plan.xlsx"),
        _tc("TC2", "Domino Test Plan.xlsx"),
        _tc("TC3", "Domino Test Plan.xlsx"),
        _tc("TC4", "Domino Test Plan.xlsx"),
        _tc("TC5", "Domino Test Plan.xlsx"),
        _tc("TC1", "MSC-205625-gap-supplement.xlsx", mapped=["R4"]),
        _tc("TC2", "MSC-205625-gap-supplement.xlsx", mapped=["L5"]),
    ]
    renumber_gap_supplement_cases(cases)
    assert [tc.id for tc in cases] == [
        "TC1",
        "TC2",
        "TC3",
        "TC4",
        "TC5",
        "TC6",
        "TC7",
    ]
    assert cases[-2].mapped_requirements == ["R4"]
    assert cases[-1].mapped_requirements == ["L5"]
    assert cases[-2].gap_supplement is True
    assert cases[-1].gap_supplement is True


def test_renumber_skipped_when_only_gap_supplement():
    cases = [
        _tc("TC1", "MSC-205625-gap-supplement.xlsx", mapped=["R4"]),
        _tc("TC2", "MSC-205625-gap-supplement.xlsx", mapped=["L5"]),
    ]
    renumber_gap_supplement_cases(cases)
    assert [tc.id for tc in cases] == ["TC1", "TC2"]


def test_renumber_skipped_when_no_gap_supplement():
    cases = [_tc("TC1", "Domino Test Plan.xlsx"), _tc("TC2", "Domino Test Plan.xlsx")]
    renumber_gap_supplement_cases(cases)
    assert [tc.id for tc in cases] == ["TC1", "TC2"]
