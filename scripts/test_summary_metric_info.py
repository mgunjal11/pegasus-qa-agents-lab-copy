#!/usr/bin/env python3
from coverage_report_helpers import SUMMARY_METRIC_INFO, wrap_summary_metric_labels


def test_wrap_adds_info_icons_to_all_summary_metrics():
    html = """
    <style></style>
    <section class="section-summary">
      <div class="label">Dev code coverage</div>
      <div class="label">CI branch coverage</div>
    </section>
    """
    out = wrap_summary_metric_labels(html)
    assert "metric-info-tip" in out
    assert "metric-info-icon" in out
    assert len(SUMMARY_METRIC_INFO) == 8


def test_wrap_idempotent():
    html = '<style></style><div class="label">Open gaps</div>'
    once = wrap_summary_metric_labels(html)
    twice = wrap_summary_metric_labels(once)
    assert once == twice
    assert once.count('class="metric-info-tip"') == 1
