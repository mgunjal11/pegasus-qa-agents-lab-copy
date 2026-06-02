#!/usr/bin/env python3
"""One-time patcher for report-template.html enhancements."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / ".cursor/skills/msc-dev-code-and-qa-test-coverage-validator/report-template.html"
t = p.read_text(encoding="utf-8")

if "{{CACHE_META}}" not in t:
    css = """
    .cache-meta { font-size: 0.82rem; color: var(--muted); margin-top: 0.5rem; }
    .quick-links { margin-top: 0.5rem; font-size: 0.88rem; }
    .jira-readiness-block { background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
    .testplan-split-metrics { font-size: 0.85rem; color: var(--muted); margin-bottom: 0.75rem; }
    .release-score-row { margin-bottom: 1rem; }
    .conf-badge { font-size: 0.75rem; color: var(--muted); }
"""
    t = t.replace("    footer { text-align: center;", css + "    footer { text-align: center;}")
    t = t.replace(
        "<strong>Generated:</strong> {{GENERATED_DATE}}\n      </div>\n      <div class=\"verdict",
        "<strong>Generated:</strong> {{GENERATED_DATE}}\n      </div>\n      <div class=\"cache-meta\">{{CACHE_META}}</div>\n      {{QUICK_LINKS}}\n      {{JIRA_READINESS_BLOCK}}\n      <div class=\"verdict",
    )
    t = t.replace(
        '<div class="section-body">\n        <div class="summary-groups">',
        '<div class="section-body">\n        <div class="release-score-row">{{RELEASE_SCORE_BLOCK}}</div>\n        <div class="summary-groups">',
    )
    t = t.replace(
        "{{TESTPLAN_COVERAGE_DETAIL}} — attached test plan</div>\n              </div>",
        "{{TESTPLAN_COVERAGE_DETAIL}} — attached test plan</div>\n                {{TESTPLAN_SPLIT_METRICS}}\n              </div>",
    )
    t = t.replace("<th>Title</th><th>Dev tests</th>", "<th>Title</th><th>Files</th><th>Dev tests</th>")
    t = t.replace("<th>Mapped req</th><th>Given When Then</th>", "<th>Mapped req</th><th>GWT</th><th>Given When Then</th>")
    t = t.replace(
        "{{LADR_TRACEABILITY_BLOCK}}\n        <div class=\"review-panel review-gaps\"",
        "{{LADR_TRACEABILITY_BLOCK}}\n        {{UNMAPPED_TC_BLOCK}}\n        {{SUGGESTED_MAPPING_BLOCK}}\n        <div class=\"review-panel review-gaps\"",
    )
    p.write_text(t, encoding="utf-8")
    print("patched", p)
else:
    print("already patched")
