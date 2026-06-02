#!/usr/bin/env python3
"""Tests for Linked PR(s) table helpers."""
from coverage_report_helpers import (
    ci_status_html,
    inject_pr_table_header_tooltips,
    render_pr_row,
    render_pr_rows,
    render_pr_table_header_row,
)


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
    assert row.count("<td>") == 7
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


def test_pr_table_header_has_info_icons():
    header = render_pr_table_header_row()
    assert header.count('class="metric-info-tip"') == 6
    assert "Dev tests" in header
    assert "CI status" in header


def test_inject_pr_table_header_tooltips():
    html = """
    <style></style>
    <section class="report-section section-pr">
      <table><thead><tr><th>PR</th><th>Repo</th></tr></thead><tbody></tbody></table>
    </section>
    """
    out = inject_pr_table_header_tooltips(html)
    assert "th-label-row" in out
    assert 'aria-label="About PR"' in out
    twice = inject_pr_table_header_tooltips(out)
    assert twice.count('class="metric-info-tip"') == out.count('class="metric-info-tip"')


if __name__ == "__main__":
    test_ci_na_empty()
    test_ci_passed()
    test_ci_failed()
    test_render_six_columns()
    test_render_pr_rows()
    print("ok")
