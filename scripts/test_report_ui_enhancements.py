#!/usr/bin/env python3
import re

from coverage_report_helpers import (
    SECTION_HEADER_INFO,
    TESTPLAN_TABLE_COLUMN_INFO,
    TRACE_TABLE_COLUMN_INFO,
    _readiness_item,
    apply_report_ui_enhancements,
)


MINIMAL_REPORT = """
<style></style>
<header>
  <h1>Coverage validation: MSC-000000 — Example story</h1>
  <div class="meta">
    <strong>Jira:</strong> <a href="#">MSC-000000</a> &nbsp;|&nbsp;
    <strong>Status:</strong> Open &nbsp;|&nbsp;
    <strong>Type:</strong> Story &nbsp;|&nbsp;
    <strong>Generated:</strong> 2026-01-01
  </div>
  <div class="cache-meta">GitHub cache 2026-01-01</div>
  <div class="quick-links"><a href="#">Jira</a></div>
  <div class="jira-readiness-block"><h3>Jira input readiness</h3><ul><li><strong>Acceptance criteria</strong> — ok</li></ul></div>
  <div class="verdict verdict-pass-gaps">Pass with gaps — example rationale.</div>
</header>
<section class="report-section section-summary">
  <div class="section-head"><span class="section-num">1</span><h2>Coverage summary</h2></div>
  <div class="section-body">
    <div class="release-score-row"><div class="metric-card"><div class="label">Release readiness score</div></div></div>
    <div class="summary-group-title">Implementation &amp; tests</div>
    <div class="label">Dev code coverage</div>
  </div>
</section>
<section class="report-section section-pr">
  <table><thead><tr><th>PR</th></tr></thead><tbody></tbody></table>
</section>
<section class="report-section section-testplan">
  <div class="note-box">Test plan from Jira attachment.</div>
  <table><thead><tr><th>TC</th><th>Scenario</th></tr></thead><tbody></tbody></table>
  <div class="testplan-split-metrics"><span class="split-metric">Jira acceptance criteria: <strong>1/2</strong></span></div>
  <div class="review-panel review-gaps"><h3>Test plan gaps</h3></div>
  <div class="review-panel"><h3>Unmapped test cases</h3></div>
</section>
<section class="report-section section-ownership">
  <p class="section-lead">Dev-owned items should be proven by unit or integration tests in the PR.</p>
  <div class="label">QA handoff</div>
</section>
<section class="report-section section-trace">
  <table><thead><tr><th>ID</th><th>Requirement</th></tr></thead><tbody></tbody></table>
</section>
<section class="report-section section-review">
  <div class="review-panel review-positive"><h3>✓ Correctly implemented</h3></div>
</section>
<section class="report-section section-assumptions">
  <div class="section-head"><h2>Assumptions and open questions</h2></div>
</section>
<section class="report-section section-actions">
  <div class="section-head"><h2>Recommended actions</h2></div>
</section>
"""


def test_normalize_legacy_readiness_warn_to_red_x():
    legacy = (
        '<div class="jira-readiness-block"><ul>'
        '<li class="readiness-item ready-warn"><span class="readiness-icon">!</span>'
        "<strong>GitHub PR</strong> — missing</li></ul></div>"
    )
    out = apply_report_ui_enhancements(f"<style></style>{legacy}")
    assert 'class="readiness-item ready-missing"' in out
    assert 'class="readiness-item ready-warn"' not in out
    assert '<span class="readiness-icon" aria-hidden="true">✗</span>' in out


def test_jira_readiness_icons_green_red():
    block = (
        '<div class="jira-readiness-block"><h3>Jira input readiness</h3><ul>'
        + _readiness_item("Acceptance criteria", True, "4 requirement(s) extracted")
        + _readiness_item("GitHub PR", False, "Add PR URL in description or comment")
        + "</ul></div>"
    )
    out = apply_report_ui_enhancements(f"<style></style>{block}")
    assert 'class="readiness-item ready-ok"' in out
    assert 'class="readiness-item ready-missing"' in out
    assert '<span class="readiness-icon" aria-hidden="true">✓</span>' in out
    assert '<span class="readiness-icon" aria-hidden="true">✗</span>' in out
    assert ".readiness-item.ready-ok .readiness-icon" in out
    assert ".readiness-item.ready-missing .readiness-icon" in out
    assert "var(--pass)" in out
    assert "var(--fail)" in out


def test_apply_report_ui_enhancements_covers_all_sections():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert 'aria-label="About verdict"' in out
    assert 'aria-label="About Report title"' in out
    assert 'aria-label="About Jira"' in out
    assert 'aria-label="About Cache freshness"' in out
    assert 'aria-label="About Quick links"' in out
    assert "About Jira input readiness" in out
    assert "About Acceptance criteria" in out
    assert "About Release readiness score" in out
    assert "About Test plan source" in out
    assert "About Dev vs QA ownership" in out
    assert "ownership section tooltips v3" in out
    assert "section-ownership" in out and "section-lead-with-tip" in out
    assert "About Unmapped test cases" in out
    assert "About Coverage summary" in out
    assert "About Linked PR(s)" not in out or "section-pr" in out
    assert "group-title-row" in out
    assert "About TC" in out
    assert "About ID" in out
    assert "About QA handoff" in out
    assert "About Test plan gaps" in out
    assert "tooltip layout fix v8" in out
    assert "right: calc(100% + 10px)" in out
    assert "section-head .heading-label-row .metric-info-tooltip" in out
    assert "th:nth-last-child(2) .metric-info-tooltip" in out
    twice = apply_report_ui_enhancements(out)
    assert twice.count('class="metric-info-tip"') == out.count('class="metric-info-tip"')


def test_table_column_counts():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert out.count("About TC") >= 1
    assert len(TESTPLAN_TABLE_COLUMN_INFO) == 7
    assert len(TRACE_TABLE_COLUMN_INFO) == 7


def test_report_footer_attribution():
    legacy = MINIMAL_REPORT.replace(
        "</section>",
        "</section>\n<footer>Generated by msc-dev-code-and-qa-test-coverage-validator</footer>",
        1,
    )
    out = apply_report_ui_enhancements(legacy)
    assert "Developed by Mayur Gunjal" in out
    twice = apply_report_ui_enhancements(out)
    assert twice.count("Developed by Mayur Gunjal") == 1


def test_tooltip_layout_fix_upgrades_legacy_css():
    legacy = MINIMAL_REPORT.replace(
        "</style>",
        """
    /* tooltip layout fix — prevent clipping in panels and sections */
    .report-section,
    .report-section .section-body,
    .review-panel { overflow: visible !important; }
    th .metric-info-tooltip { left: 50% !important; }
    th:last-child .metric-info-tooltip { left: auto !important; right: 0 !important; }
  </style>""",
        1,
    )
    out = apply_report_ui_enhancements(legacy)
    assert "tooltip layout fix v8" in out
    assert "right: calc(100% + 10px)" in out
    assert "th .metric-info-tooltip { left: 50%" not in out.replace(" ", "")
    assert "th:nth-last-child(2) .metric-info-tooltip" in out
    assert "section-head .heading-label-row .metric-info-tooltip" in out


def test_tooltip_layout_fix_upgrades_v2_css():
    v2 = MINIMAL_REPORT.replace(
        "</style>",
        """
    /* tooltip layout fix v2 — prevent clipping in panels and sections */
    th .metric-info-tooltip { left: auto !important; right: 0 !important; }
  </style>""",
        1,
    )
    out = apply_report_ui_enhancements(v2)
    assert "tooltip layout fix v8" in out
    assert "right: calc(100% + 10px)" in out
    assert "tooltip layout fix v2" not in out
    assert "th:nth-last-child(2) .metric-info-tooltip" in out


def test_ownership_section_tooltip_layout():
    """§4 tooltips: header/lead/cards open below icon; QA card aligns tooltip left."""
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert "ownership section tooltips v3" in out
    assert ".section-ownership .section-head:has(.metric-info-tip:hover)" in out
    assert ".section-ownership .metric-card.metric-qa .label-row .metric-info-tooltip" in out
    block = out.split("ownership section tooltips v3")[1].split("/* trace section visibility")[0]
    assert ".section-ownership .metric-card .label-row .metric-info-tooltip" in block
    assert "top: calc(100% + 8px)" in block
    assert "bottom: calc(100% + 8px)" not in block
    assert "isolation: isolate" in block
    # Lead icon at end of paragraph, not before body text
    m = re.search(
        r'<section class="report-section section-ownership">[\s\S]*?'
        r'<p class="section-lead section-lead-with-tip">([\s\S]*?)</p>',
        out,
    )
    assert m is not None
    assert m.group(1).strip().endswith('</span>')
    assert 'aria-label="About Dev vs QA ownership"' in m.group(1)
    upgraded = apply_report_ui_enhancements(
        MINIMAL_REPORT.replace(
            "</style>",
            """
    /* ownership section tooltips v2 */
    .section-ownership .metric-card .label-row .metric-info-tooltip {
      bottom: calc(100% + 8px) !important;
    }
  </style>""",
            1,
        ).replace(
            '<p class="section-lead">Dev-owned items',
            '<p class="section-lead section-lead-with-tip">'
            '<span class="metric-info-tip" tabindex="0" role="button" '
            'aria-label="About Dev vs QA ownership">'
            '<span class="metric-info-icon" aria-hidden="true">i</span>'
            '<span class="metric-info-tooltip">old</span></span> Dev-owned items',
            1,
        )
    )
    assert "ownership section tooltips v3" in upgraded
    assert "ownership section tooltips v2" not in upgraded
    assert "bottom: calc(100% + 8px)" not in upgraded.split("ownership section tooltips v3")[1].split(
        "/* trace section visibility"
    )[0]


def test_pr_table_dev_tests_tooltip_right_aligned_to_th():
    html = """
    <style></style>
    <section class="report-section section-pr">
      <table><thead><tr><th>PR</th><th>Repo</th><th>State</th><th>Title</th><th>Dev tests</th><th>CI status</th></tr></thead><tbody></tbody></table>
    </section>
    """
    out = apply_report_ui_enhancements(html)
    assert "th:nth-last-child(2) .metric-info-tooltip" in out
    assert "th:nth-last-child(-n+2)" in out
    assert "translateX(-50%)" not in out
    assert 'aria-label="About Dev tests"' in out
    assert "Key unit or integration test classes or files added or changed in the PR" in out
    assert "dev-owned acceptance criteria" in out


def test_metric_info_click_toggle_script():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert "metric-info-tip click toggle" in out
    assert ".metric-info-tip.is-open .metric-info-tooltip" in out
    assert "classList.toggle('is-open')" in out
    assert "</script>" in out
