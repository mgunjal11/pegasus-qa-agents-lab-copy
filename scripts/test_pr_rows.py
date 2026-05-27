#!/usr/bin/env python3
"""Tests for Linked PR(s) table helpers."""
from coverage_report_helpers import ci_status_html, render_pr_row, render_pr_rows


def test_ci_na_empty():
    assert "badge-na" in ci_status_html(None)
    assert "badge-na" in ci_status_html("")
    assert "badge-na" in ci_status_html("gh: checks unavailable")


def test_ci_passed():
    assert "badge-covered" in ci_status_html("build\tpass\nlint\tpass")


def test_ci_failed():
    assert "badge-missing" in ci_status_html("build\tfail")


def test_render_six_columns():
    row = render_pr_row(
        url="https://github.com/wbd-msc/pegasus-pick-genie/pull/161",
        number=161,
        repo="wbd-msc/pegasus-pick-genie",
        state="MERGED",
        title="Passport routing for incremental-as-full PFT Clear",
        dev_tests="TestDominoPassportRouting, passport_manager unit tests",
        checks=None,
    )
    assert row.count("<td>") == 6
    assert "pegasus-pick-genie" in row
    assert "Passport routing" in row
    assert "TestDominoPassportRouting" in row
    assert "badge-na" in row
    assert "Passport routing" not in row.split("<td>")[-1]  # not in CI cell


def test_render_pr_rows():
    html = render_pr_rows(
        [
            {
                "url": "https://github.com/o/r/pull/1",
                "number": 1,
                "repo": "o/r",
                "state": "open",
                "title": "Fix bug",
                "dev_tests": "test_x",
                "checks": "ci\tpass",
            }
        ]
    )
    assert "#1" in html
    assert "badge-covered" in html


if __name__ == "__main__":
    test_ci_na_empty()
    test_ci_passed()
    test_ci_failed()
    test_render_six_columns()
    test_render_pr_rows()
    print("ok")
