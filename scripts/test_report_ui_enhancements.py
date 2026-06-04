#!/usr/bin/env python3
import re

from coverage_report_helpers import (
    SECTION_HEADER_INFO,
    TESTPLAN_TABLE_COLUMN_INFO,
    TRACE_TABLE_COLUMN_INFO,
    _readiness_item,
    apply_report_ui_enhancements,
    strip_report_tooltips,
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


def test_tooltips_on_all_major_labels():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert out.count('class="metric-info-tip"') >= 15
    assert "tooltip layout fix v22" in out
    assert "translateX(-50%)" in out
    assert 'aria-label="About Coverage summary"' in out
    assert 'aria-label="About Release readiness score"' in out
    assert 'aria-label="About Dev code coverage"' in out
    assert 'aria-label="About TC"' in out
    assert 'aria-label="About ID"' in out
    assert 'aria-label="About QA handoff"' in out
    assert "About Assumptions and open questions" in out
    assert "tooltip-title" in out and "tooltip-body" in out


def test_tooltip_description_spacing_css():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert ".metric-info-tooltip .tooltip-title" in out
    assert "line-height: 1.55" in out
    assert "padding: 0.75rem 0.85rem" in out
    assert "margin-bottom: 0.55rem" in out or "margin: 0 0 0.55rem" in out


def test_summary_metrics_flip_up():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    block = out.split(".metric-card .label-row .metric-info-tip > .metric-info-tooltip")[1][:450]
    assert "bottom: calc(100% + 10px)" in block


def test_tooltip_shows_on_hover():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert ".metric-info-tip:hover .metric-info-tooltip" in out
    assert "metric-info-tip click toggle" not in out
    assert 'title="Hover for description"' not in out
    assert ".metric-info-tip > .metric-info-tooltip" in out


def test_release_readiness_tooltip_full_box_left_of_icon():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    block = out.split(".metric-card .label-row .metric-info-tip > .metric-info-tooltip")[1][:500]
    assert "bottom: calc(100% + 10px)" in block
    assert "left: 0 !important" in block
    assert "transform: none !important" in block
    rel = out.split(".release-score-card .label-row .metric-info-tip > .metric-info-tooltip")[1][:200]
    assert "z-index: 1200" in rel
    assert "section-summary:has(.release-score-card .metric-info-tip:hover) .section-body" in out
    assert 'aria-label="About Release readiness score"' in out
    assert "open-gap severity from the review" in out


def test_cache_meta_tooltip_anchors_left():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert "header .cache-meta-with-tip .metric-info-tip," in out
    assert "position: static !important" in out.split("header .cache-meta-with-tip .metric-info-tip,")[1][:400]
    idx = out.index("header .cache-meta-with-tip .metric-info-tip > .metric-info-tooltip")
    block = out[idx : idx + 700]
    assert "left: 0 !important" in block
    assert "transform: none !important" in block


def test_metric_grid_tooltips_row_anchored_not_centered():
    """First grid column cards must not use translateX(-50%) on label-row tooltips."""
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    block = out.split(".metric-card .label-row .metric-info-tip > .metric-info-tooltip")[1][:450]
    assert "bottom: calc(100% + 10px)" in block
    assert "left: 0 !important" in block
    assert "transform: none !important" in block
    assert "translateX(-50%)" not in block.split("/* Release readiness")[0]


def test_group_title_tooltip_opens_below_right_aligned():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert ".summary-group-title .group-title-row .metric-info-tip > .metric-info-tooltip" in out
    block = out.split(".summary-group-title .group-title-row .metric-info-tip > .metric-info-tooltip")[1][:400]
    assert "top: calc(100% + 10px)" in block
    assert "right: 0 !important" in block
    assert "bottom: auto !important" in block
    assert "transform: none !important" in block
    assert 'aria-label="About Implementation &amp; tests"' in out or "Implementation" in out


def test_first_table_column_tooltip_left_anchored():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    idx = out.index("th:first-child .metric-info-tip > .metric-info-tooltip")
    block = out[idx : idx + 700]
    assert "left: 0 !important" in block
    assert "transform: none !important" in block


def test_section_h2_tooltip_flips_up_above_banner():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert ".report-section .section-head .heading-label-row .metric-info-tip > .metric-info-tooltip" in out
    block = out.split(".report-section .section-head .heading-label-row .metric-info-tip > .metric-info-tooltip")[1][:350]
    assert "bottom: calc(100% + 10px)" in block
    assert "left: 0 !important" in block
    assert 'aria-label="About Coverage summary"' in out


def test_header_quick_links_tooltip_centered():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert ".quick-links-with-tip" in out or "quick-links-with-tip" in out
    assert "header .quick-links" in out
    assert ".metric-info-tip > .metric-info-tooltip" in out


def test_normalize_legacy_readiness_warn_to_red_x():
    legacy = (
        '<div class="jira-readiness-block"><ul>'
        '<li class="readiness-item ready-warn"><span class="readiness-icon">!</span>'
        "<strong>GitHub PR</strong> — missing</li></ul></div>"
    )
    out = apply_report_ui_enhancements(f"<style></style>{legacy}")
    assert 'class="readiness-item ready-missing"' in out
    assert '<span class="readiness-icon" aria-hidden="true">✗</span>' in out


def test_report_h1_and_jira_readiness_heading_have_no_tooltip():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert 'aria-label="About Report title"' not in out
    assert "About Jira input readiness" not in out
    assert "<h3>Jira input readiness</h3>" in out or "Jira input readiness</h3>" in out
    assert 'aria-label="About Acceptance criteria"' in out


def test_jira_readiness_icons_green_red():
    block = (
        '<div class="jira-readiness-block"><h3>Jira input readiness</h3><ul>'
        + _readiness_item("Acceptance criteria", True, "4 requirement(s) extracted")
        + _readiness_item("GitHub PR", False, "Add PR URL in description or comment")
        + "</ul></div>"
    )
    out = apply_report_ui_enhancements(f"<style></style>{block}")
    assert 'class="readiness-item ready-ok"' in out
    assert ".readiness-item.ready-ok .readiness-icon" in out


def test_report_footer_attribution():
    legacy = MINIMAL_REPORT.replace(
        "</section>",
        "</section>\n<footer>Generated by msc-dev-code-and-qa-test-coverage-validator</footer>",
        1,
    )
    out = apply_report_ui_enhancements(legacy)
    assert "Developed by Mayur Gunjal" in out


def test_apply_report_ui_enhancements_idempotent():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    twice = apply_report_ui_enhancements(out)
    assert twice.count('aria-label="About Coverage summary"') == 1
    assert twice.count('aria-label="About Release readiness score"') == 1
    assert "tooltip layout fix v22" in twice


def test_table_column_tooltips():
    out = apply_report_ui_enhancements(MINIMAL_REPORT)
    assert len(TESTPLAN_TABLE_COLUMN_INFO) == 7
    assert len(TRACE_TABLE_COLUMN_INFO) == 7
    assert len(SECTION_HEADER_INFO) >= 6


def test_trace_section_lead_tooltip():
    legacy = MINIMAL_REPORT.replace(
        '<section class="report-section section-trace">',
        '<section class="report-section section-trace">'
        '<p class="trace-section-lead">Per-requirement mapping.</p>',
        1,
    )
    out = apply_report_ui_enhancements(legacy)
    assert "trace-section-lead-with-tip" in out
    assert 'aria-label="About Requirements traceability intro"' in out


def test_strip_then_reapply_tooltips():
    with_tips = apply_report_ui_enhancements(MINIMAL_REPORT)
    stripped = strip_report_tooltips(with_tips)
    assert '<span class="metric-info-tip"' not in stripped
    restored = apply_report_ui_enhancements(stripped)
    assert '<span class="metric-info-tip"' in restored
    assert "tooltip-body" in restored
