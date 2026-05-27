#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from testplan_gwt import has_complete_gwt, normalize_steps, parse_gwt_from_text  # noqa: E402

SAMPLE = (
    "Given: An MVP is acquired for having audio and SDR video\n"
    "When: An Multiple MR is ingested for the same asset at the same time\n"
    "Then: The workflow should get completed in Mascot"
)

SAMPLE_NO_COLON = (
    "Given a CAT demand is received\n"
    "When the system acknowledges the demand\n"
    "Then demandAcknowledgment milestone is marked Completed"
)


def test_parse_combined_test_steps() -> None:
    parsed = parse_gwt_from_text(SAMPLE)
    assert "given" in parsed and "when" in parsed and "then" in parsed
    assert has_complete_gwt({"when": SAMPLE})


def test_normalize_single_blob() -> None:
    norm = normalize_steps({"when": SAMPLE})
    assert has_complete_gwt(norm)
    assert all(norm.get(k) for k in ("given", "when", "then"))


def test_parse_without_colons() -> None:
    from testplan_gwt import normalize_steps  # noqa: E402

    assert has_complete_gwt({"given": "Given a CAT demand is received", "when": "When the system acknowledges the demand", "then": "Then demandAcknowledgment milestone is marked Completed"})
    norm = normalize_steps({"given": SAMPLE_NO_COLON})
    assert has_complete_gwt(norm)


def test_caption_monitoring_sheet() -> None:
    from fetch_jira_testplan import parse_testplan_file  # noqa: E402

    path = ROOT / "reports/.cache/MSC-204417-testplan-files/Promo Caption Monitoring.xlsx"
    if not path.exists():
        return
    cases = parse_testplan_file(path, "Caption Monitoring", "MSC-204417")
    assert len(cases) == 12
    complete = sum(1 for tc in cases if has_complete_gwt(tc.steps))
    assert complete == 12, f"expected 12/12 full GWT, got {complete}"


def test_ff_race_condition_file() -> None:
    from fetch_jira_testplan import parse_testplan_file  # noqa: E402

    path = ROOT / "reports/.cache/MSC-195138-testplan-files/FF Race Condition.xlsx"
    if not path.exists():
        return
    cases = parse_testplan_file(path, "Scenarios", "MSC-195138")
    complete = sum(1 for tc in cases if has_complete_gwt(tc.steps))
    assert complete >= 9, f"expected most scenarios to have full GWT, got {complete}/{len(cases)}"


if __name__ == "__main__":
    test_parse_combined_test_steps()
    test_normalize_single_blob()
    test_parse_without_colons()
    test_caption_monitoring_sheet()
    test_ff_race_condition_file()
    print("ok")
