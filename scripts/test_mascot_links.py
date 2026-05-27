#!/usr/bin/env python3
"""Tests for Mascot link extraction in fetch_jira_testplan."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_jira_testplan import extract_mascot_links, parse_testplan_file  # noqa: E402

QA_URL = "https://int.foundry.wbdapps.com/mascot/fulfill-details/84ab2ef9-1786-49e4-bddc-bbab75551755"
SIT_URL = "https://stg.foundry.wbdapps.com/mascot/fulfill-details/a99988b2-e472-4317-89c3-75fdda01dc58"


def test_extract_mascot_links_from_columns() -> None:
    header = ["Summary", "QA Mascot link", "SIT MAscot link"]
    row = ["scenario", QA_URL, SIT_URL]
    links = extract_mascot_links(header, row)
    urls = {lnk["url"] for lnk in links}
    assert QA_URL in urls
    assert SIT_URL in urls
    labels = {lnk["label"] for lnk in links}
    assert "QA Mascot link" in labels or any("QA" in lb for lb in labels)


def test_ff_race_condition_scenarios_sheet() -> None:
    path = ROOT / "reports/.cache/MSC-195138-testplan-files/FF Race Condition.xlsx"
    if not path.exists():
        return
    cases = parse_testplan_file(path, "Scenarios", "MSC-195138")
    assert cases
    with_links = [tc for tc in cases if tc.mascot_links]
    assert with_links, "expected mascot_links on Scenarios sheet rows"
    assert any(
        "foundry.wbdapps.com/mascot" in lnk["url"]
        for tc in with_links
        for lnk in tc.mascot_links
    )


if __name__ == "__main__":
    test_extract_mascot_links_from_columns()
    test_ff_race_condition_scenarios_sheet()
    print("ok")
