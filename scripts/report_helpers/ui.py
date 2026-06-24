"""Report UI: tooltips, CSS, apply_report_ui_enhancements (do not edit for content)."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from report_helpers.common import REPORT_AGENT_NAME, REPORT_DEVELOPER, esc

SUMMARY_METRIC_INFO: dict[str, str] = {
    "Dev code coverage": (
        "Share of Jira acceptance criteria that have matching production code "
        "changes in the linked PR. Green ≥85%, amber 70–84.9%, red below 70%."
    ),
    "Dev unit / integration test coverage": (
        "Share of dev-owned acceptance criteria covered by unit or integration "
        "tests added or updated in the PR (not E2E or manual QA)."
    ),
    "Requirements mapped": (
        "How many Jira acceptance criteria were extracted from the story and "
        "scored in this report (e.g. R1–R4)."
    ),
    "Test plan acceptance criteria coverage": (
        "Share of Jira acceptance criteria and linked LADR/Confluence ESS scenarios "
        "that have at least one mapped test case in the attached test plan with Given/When/Then steps."
    ),
    "QA scope remaining": (
        "Count of requirements still needing QA verification—E2E, manual, "
        "regression, or spot-check—because dev tests do not fully cover them."
    ),
    "Open gaps": (
        "Implementation or test-plan concerns from the review, summarized by "
        "severity (e.g. High, Medium)."
    ),
    "CI line coverage": (
        "Percentage of code lines executed by automated tests in CI, from "
        "Codecov, SonarQube, or pytest-cov on the linked PR."
    ),
    "CI branch coverage": (
        "Percentage of code branches (if/else paths) covered by automated tests "
        "in CI, from Codecov, SonarQube, or pytest-cov on the linked PR."
    ),
    "Release readiness score": (
        "Weighted composite (0–100%): dev code 30%, dev tests 25%, attached test plan "
        "25%, open-gap penalty 10% (15 pts per High, 7 per Med), CI line coverage 10% "
        "when reported. Drives the final verdict: ≥85% Pass (no High/Med gaps), "
        "50–84% Pass with gaps, below 50% Fail. Also Fail on any High gap or dev code below 50%."
    ),
}

HEADER_H1_INFO = (
    "MSC coverage validation report comparing the Jira story to linked GitHub PRs, "
    "attached QMetry test plan, and CI pipeline metrics."
)

CACHE_META_INFO = (
    "UTC timestamps when GitHub (PR diff), test plan, and Jira story caches were last "
    "prefetched for this report run."
)

QUICK_LINKS_INFO = (
    "Quick navigation to the Jira story, SharePoint test plan, linked pull requests, "
    "and LADR Confluence (only when a LADR or design-requirements page is linked)."
)

META_FIELD_INFO: dict[str, str] = {
    "Jira": "Link to the Jira story on wbdstreaming.atlassian.net.",
    "Status": "Current Jira workflow status of the story (e.g. In Progress, Done).",
    "Type": "Jira issue type (Story, Bug, Task, etc.).",
    "Generated": "Date and time this HTML report was generated (local timezone).",
}

READINESS_PANEL_INFO: dict[str, str] = {
    "Jira input readiness": (
        "Pre-flight checklist: whether Jira acceptance criteria, PR links, test plan, "
        "and optional Confluence LADR are available for accurate scoring."
    ),
}

READINESS_ITEM_INFO: dict[str, str] = {
    "Acceptance criteria": (
        "Numbered requirements (R1, R2, …) extracted from the Jira description for traceability."
    ),
    "GitHub PR": (
        "Pull requests linked in Jira or discovered during prefetch — source of code and dev tests."
    ),
    "Test plan": (
        "QMetry Excel attachment parsed for scenarios, Given/When/Then steps, and requirement mapping."
    ),
    "Confluence / LADR": (
        "Optional Confluence design page for LADR (L1, L2, …) traceability; optional when story has no LADR."
    ),
}

NOTE_BOX_INFO = (
    "Source of the attached QMetry test plan: Jira attachment file, Excel sheet/tab, and scenario count."
)

SPLIT_METRIC_INFO: dict[str, str] = {
    "Jira acceptance criteria:": (
        "How many Jira acceptance criteria (R-items) have at least one mapped test case in the plan."
    ),
    "LADR scenarios:": (
        "How many Confluence LADR requirements (L-items) have at least one mapped test case in the plan."
    ),
}

SECTION_LEAD_INFO = (
    "Dev-owned acceptance criteria should be proven by unit or integration tests in the linked PR; "
    "QA-owned items need functional, E2E, or manual verification outside the PR test suite."
)

TRACE_SECTION_LEAD_INFO = (
    "Per-requirement mapping from Jira acceptance criteria (R1, R2, …) to branch/PR code, "
    "dev unit/integration tests, Dev vs QA ownership, QA scope, and file-level evidence."
)

LADR_SECTION_LEAD_INFO = (
    "Summary of how many Confluence LADR requirements (L1, L2, …) are covered by test cases "
    "in the attached Excel plan, with links to the source design page when available."
)

LEAD_PARAGRAPH_INFO: dict[str, tuple[str, str]] = {
    "trace-section-lead": ("Requirements traceability intro", TRACE_SECTION_LEAD_INFO),
    "ladr-section-lead": ("LADR traceability summary", LADR_SECTION_LEAD_INFO),
}

METRIC_INFO_CSS = """
    .label-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.35rem; margin-bottom: 0.3rem; }
    .label-row .label { margin-bottom: 0; flex: 1; min-width: 0; }
    .metric-info-tip { position: relative; display: inline-flex; flex-shrink: 0; margin-top: 0.05rem; margin-left: 0.2rem; z-index: 1; }
    .metric-info-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 1rem; height: 1rem; border-radius: 50%;
      font-size: 0.62rem; font-weight: 700; font-style: italic; font-family: Georgia, serif;
      color: #475569; background: #e2e8f0; border: 1px solid #cbd5e1;
      cursor: pointer; line-height: 1;
    }
    .metric-info-tip:hover .metric-info-icon,
    .metric-info-tip:focus .metric-info-icon,
    .metric-info-tip:focus-within .metric-info-icon { background: #2563eb; color: #fff; border-color: #2563eb; outline: none; }
    .metric-info-tooltip {
      visibility: hidden; opacity: 0;
      position: absolute; z-index: 200;
      left: 50%; right: auto; top: calc(100% + 10px);
      transform: translateX(-50%);
      width: min(340px, calc(100vw - 2.5rem));
      max-width: 340px;
      min-width: 12rem;
      height: auto;
      max-height: none;
      overflow: visible;
      padding: 0.75rem 0.85rem;
      background: #0f172a; color: #e2e8f0;
      font-size: 0.72rem; font-weight: 400;
      text-transform: none; letter-spacing: normal;
      border-radius: 8px; box-shadow: 0 8px 20px rgba(15,23,42,0.32);
      transition: opacity 0.15s ease, visibility 0.15s ease;
      pointer-events: none;
      white-space: normal;
      text-align: left;
      box-sizing: border-box;
    }
    .metric-info-tooltip .tooltip-title {
      display: block;
      font-weight: 600;
      font-size: 0.75rem;
      color: #f8fafc;
      margin: 0 0 0.55rem;
      padding: 0 0 0.55rem 0;
      border-bottom: 1px solid rgba(248,250,252,0.22);
      line-height: 1.35;
    }
    .metric-info-tooltip .tooltip-body {
      display: block;
      color: #cbd5e1;
      line-height: 1.55;
      margin: 0;
      padding: 0.1rem 0 0;
    }
    th:last-child .metric-info-tooltip,
    th:nth-last-child(2) .metric-info-tooltip {
      left: auto;
      right: calc(100% + 10px);
      top: 50%;
      bottom: auto;
      transform: translateY(-50%);
    }
    th:nth-last-child(-n+2) .metric-info-tip {
      position: relative;
    }
    /* Description on hover (or keyboard focus) */
    .metric-info-tip:hover .metric-info-tooltip,
    .metric-info-tip:focus .metric-info-tooltip,
    .metric-info-tip:focus-within .metric-info-tooltip {
      visibility: visible; opacity: 1; pointer-events: auto;
    }
    .trace-section-lead-with-tip,
    .ladr-section-lead-with-tip {
      position: relative;
      padding-right: 2rem;
      margin-bottom: 0.75rem;
    }
    .trace-section-lead-with-tip .metric-info-tip,
    .ladr-section-lead-with-tip .metric-info-tip {
      position: absolute;
      top: 0.1rem;
      right: 0;
    }
    .trace-section-lead-with-tip .metric-info-tip > .metric-info-tooltip,
    .ladr-section-lead-with-tip .metric-info-tip > .metric-info-tooltip {
      left: 50%;
      right: auto;
      transform: translateX(-50%);
      top: calc(100% + 10px);
    }
"""

METRIC_INFO_CLICK_JS_MARKER = "/* metric-info-tip click toggle */"
METRIC_INFO_CLICK_JS = """
    """ + METRIC_INFO_CLICK_JS_MARKER + """
    (function () {
      function closeAll(except) {
        document.querySelectorAll('.metric-info-tip.is-open').forEach(function (t) {
          if (t !== except) {
            t.classList.remove('is-open');
            t.setAttribute('aria-expanded', 'false');
          }
        });
      }
      document.querySelectorAll('.metric-info-tip').forEach(function (tip) {
        if (!tip.getAttribute('aria-expanded')) tip.setAttribute('aria-expanded', 'false');
        tip.addEventListener('click', function (e) {
          e.stopPropagation();
          var open = tip.classList.toggle('is-open');
          tip.setAttribute('aria-expanded', open ? 'true' : 'false');
          closeAll(open ? tip : null);
          if (open) tip.focus();
        });
        tip.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            var open = tip.classList.toggle('is-open');
            tip.setAttribute('aria-expanded', open ? 'true' : 'false');
            closeAll(open ? tip : null);
          }
          if (e.key === 'Escape') {
            tip.classList.remove('is-open');
            tip.setAttribute('aria-expanded', 'false');
          }
        });
      });
      document.addEventListener('click', function (e) {
        if (!e.target.closest('.metric-info-tip')) closeAll(null);
      });
    })();
"""

TOOLTIP_LAYOUT_FIX_MARKER = "/* tooltip layout fix v22 — group titles open below, right-aligned to icon */"

TOOLTIP_LAYOUT_FIX_CSS = """
    """ + TOOLTIP_LAYOUT_FIX_MARKER + """
    .container,
    .report-section,
    .report-section .section-head,
    .report-section .section-body,
    .review-panel,
    .metric-card,
    .metric-grid,
    .summary-grid,
    header,
    table,
    thead,
    tbody,
    tr,
    th {
      overflow: visible !important;
    }
    .table-wrap { overflow-x: auto; overflow-y: visible !important; }
    .review-panel h3,
    .heading-label-row,
    .label-row,
    .group-title-row,
    th .th-label-row {
      position: relative;
      z-index: 1;
    }
    th:nth-last-child(-n+2) {
      position: relative !important;
    }
    th:nth-last-child(-n+2) .th-label-row {
      position: static !important;
    }
    th:nth-last-child(-n+2) .metric-info-tip {
      position: relative !important;
    }
    th:nth-last-child(-n+2):has(.metric-info-tip:hover),
    th:nth-last-child(-n+2):has(.metric-info-tip:focus-within),
    .metric-info-tip:hover,
    .metric-info-tip:focus-within {
      z-index: 250;
    }
    .metric-info-icon,
    .metric-info-tip {
      cursor: pointer !important;
    }
    header,
    header .meta,
    header .cache-meta,
    header .quick-links,
    header .jira-readiness-block,
    header .verdict {
      overflow: visible !important;
      position: relative;
    }
    .metric-info-tip {
      position: relative !important;
      vertical-align: middle;
    }
    .metric-info-tip > .metric-info-tooltip {
      z-index: 500 !important;
      left: 50% !important;
      right: auto !important;
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      transform: translateX(-50%) !important;
      width: min(300px, calc(100vw - 2rem)) !important;
      max-width: 300px !important;
      min-width: 12rem;
      padding: 0.75rem 0.85rem !important;
      white-space: normal !important;
      word-wrap: break-word !important;
      overflow-wrap: break-word !important;
      box-sizing: border-box !important;
    }
    .metric-info-tooltip .tooltip-title {
      margin-bottom: 0.55rem !important;
      padding-bottom: 0.55rem !important;
      line-height: 1.35 !important;
    }
    .metric-info-tooltip .tooltip-body {
      line-height: 1.55 !important;
      padding-top: 0.1rem !important;
    }
    .metric-info-tip:hover,
    .metric-info-tip:focus-within {
      z-index: 600 !important;
    }
    .heading-label-row,
    .group-title-row,
    .label-row,
    .th-label-row,
    .split-metric-with-tip {
      position: relative;
      overflow: visible !important;
    }
    .section-head .heading-label-row,
    header h1 .heading-label-row {
      display: inline-flex !important;
      align-items: center !important;
      gap: 0.35rem !important;
      flex-wrap: wrap !important;
    }
    /* Header / meta lines: icon at line start — center transform clips text off the left */
    header .cache-meta-with-tip,
    header .quick-links-with-tip,
    header .meta,
    header .verdict,
    .jira-readiness-block .readiness-item,
    .split-metric-with-tip,
    .note-box-with-tip {
      overflow: visible !important;
      position: relative;
    }
    header .cache-meta-with-tip .metric-info-tip,
    header .quick-links-with-tip .metric-info-tip,
    header .meta .metric-info-tip,
    header .verdict .metric-info-tip,
    .jira-readiness-block .readiness-item .metric-info-tip,
    .split-metric-with-tip .metric-info-tip,
    .note-box-with-tip .metric-info-tip {
      position: static !important;
    }
    header .cache-meta-with-tip .metric-info-tip > .metric-info-tooltip,
    header .quick-links-with-tip .metric-info-tip > .metric-info-tooltip,
    header .meta .metric-info-tip > .metric-info-tooltip,
    header .verdict .metric-info-tip > .metric-info-tooltip,
    .jira-readiness-block .readiness-item .metric-info-tip > .metric-info-tooltip,
    .split-metric-with-tip .metric-info-tip > .metric-info-tooltip,
    .note-box-with-tip .metric-info-tip > .metric-info-tooltip {
      left: 0 !important;
      right: auto !important;
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      transform: none !important;
      z-index: 850 !important;
      width: min(360px, calc(100vw - 2rem)) !important;
      max-width: 360px !important;
    }
    header .cache-meta-with-tip:has(.metric-info-tip:hover),
    header .quick-links-with-tip:has(.metric-info-tip:hover),
    header .meta:has(.metric-info-tip:hover),
    header:has(.cache-meta-with-tip .metric-info-tip:hover),
    header:has(.quick-links-with-tip .metric-info-tip:hover) {
      z-index: 400 !important;
      overflow: visible !important;
    }
    /* §1–§8 section banners: tooltip above h2 (below was hidden under section-body) */
    .report-section .section-head {
      position: relative !important;
      z-index: 8 !important;
      overflow: visible !important;
    }
    .report-section .section-head h2 {
      overflow: visible !important;
      position: relative !important;
    }
    .report-section .section-body {
      position: relative !important;
      z-index: 1 !important;
    }
    .report-section .section-head:has(.metric-info-tip:hover),
    .report-section .section-head:has(.metric-info-tip:focus-within) {
      z-index: 900 !important;
      overflow: visible !important;
    }
    .report-section .section-head .heading-label-row {
      position: relative !important;
      overflow: visible !important;
    }
    .report-section .section-head .heading-label-row .metric-info-tip {
      position: static !important;
    }
    .report-section .section-head .heading-label-row .metric-info-tip > .metric-info-tooltip {
      top: auto !important;
      bottom: calc(100% + 10px) !important;
      left: 0 !important;
      right: auto !important;
      transform: none !important;
      z-index: 950 !important;
    }
    .report-section .section-head .metric-info-tip:hover,
    .report-section .section-head .metric-info-tip:focus-within {
      z-index: 960 !important;
    }
    /* Last two columns (e.g. QA scope + Evidence): open to the left of header */
    /* First table column: centered tooltip clips off the left edge of the grid */
    thead th:first-child .th-label-row,
    th:first-child .th-label-row {
      position: relative !important;
      overflow: visible !important;
    }
    thead th:first-child .metric-info-tip,
    th:first-child .metric-info-tip {
      position: static !important;
    }
    thead th:first-child .metric-info-tip > .metric-info-tooltip,
    th:first-child .metric-info-tip > .metric-info-tooltip {
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      left: 0 !important;
      right: auto !important;
      transform: none !important;
      z-index: 600 !important;
    }
    th:nth-last-child(-n+2) .metric-info-tip > .metric-info-tooltip {
      top: 50% !important;
      bottom: auto !important;
      left: auto !important;
      right: calc(100% + 10px) !important;
      transform: translateY(-50%) !important;
      max-width: min(320px, calc(100vw - 2rem)) !important;
      width: min(320px, calc(100vw - 2rem)) !important;
    }
    th:last-child .metric-info-tip:hover,
    th:nth-last-child(2) .metric-info-tip:hover,
    th:last-child .metric-info-tip:focus-within,
    th:nth-last-child(2) .metric-info-tip:focus-within {
      z-index: 350 !important;
    }
    .section-testplan .table-wrap,
    .section-trace .table-wrap {
      overflow-x: auto !important;
      overflow-y: visible !important;
      padding-top: 0.75rem;
      margin-bottom: 1rem;
    }
    .section-testplan table,
    .section-trace table.trace-table,
    .section-trace .table-wrap > table {
      overflow: visible !important;
    }
    .section-trace thead,
    .section-testplan thead {
      position: relative;
      z-index: 2;
    }
    .section-trace .section-head h2,
    .section-trace .section-head .heading-label-row {
      color: #fff !important;
      text-shadow: 0 1px 2px rgba(0,0,0,0.15);
    }
    /* Metric cards: label-row tooltips must paint above .metric-value / .note (sibling below in DOM) */
    .metric-card {
      overflow: visible !important;
    }
    .metric-card .metric-value,
    .metric-card .note {
      position: relative;
      z-index: 0;
    }
    .metric-card .label-row {
      position: relative;
      z-index: 2;
    }
    .metric-card:has(.label-row .metric-info-tip:hover) .label-row,
    .metric-card:has(.label-row .metric-info-tip:focus-within) .label-row {
      z-index: 100 !important;
    }
    /* Metric / summary grids: row-anchored tooltips (fixes first grid column left clip) */
    .metric-grid,
    .summary-grid,
    .summary-groups {
      overflow: visible !important;
    }
    .metric-card .label-row {
      position: relative !important;
      overflow: visible !important;
      z-index: 2;
    }
    .metric-card:has(.label-row .metric-info-tip:hover),
    .metric-card:has(.label-row .metric-info-tip:focus-within) {
      z-index: 50 !important;
    }
    .metric-card .label-row .metric-info-tip {
      position: static !important;
      flex-shrink: 0;
    }
    .metric-card .label-row .metric-info-tip > .metric-info-tooltip {
      top: auto !important;
      bottom: calc(100% + 10px) !important;
      left: 0 !important;
      right: auto !important;
      transform: none !important;
      z-index: 800 !important;
      width: min(340px, calc(100vw - 2rem)) !important;
      max-width: 340px !important;
      min-width: 12rem;
      height: auto !important;
      max-height: none !important;
      overflow: visible !important;
    }
    .metric-card .label-row .metric-info-tip:hover,
    .metric-card .label-row .metric-info-tip:focus-within {
      z-index: 850 !important;
    }
    /* Summary group titles (Implementation & tests, …): open below — flip-up was clipped under release score */
    .summary-group-title {
      overflow: visible !important;
      position: relative;
    }
    .summary-group-title .group-title-row {
      position: relative !important;
      overflow: visible !important;
      z-index: 2;
    }
    .summary-group-title:has(.metric-info-tip:hover),
    .summary-group-title:has(.metric-info-tip:focus-within) {
      z-index: 120 !important;
    }
    .summary-group-title .group-title-row .metric-info-tip {
      position: static !important;
      flex-shrink: 0;
    }
    .summary-group-title .group-title-row .metric-info-tip > .metric-info-tooltip {
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      left: auto !important;
      right: 0 !important;
      transform: none !important;
      z-index: 900 !important;
      width: min(340px, calc(100vw - 2rem)) !important;
      max-width: 340px !important;
      min-width: 12rem;
      height: auto !important;
      max-height: none !important;
      overflow: visible !important;
    }
    .summary-group-title .group-title-row .metric-info-tip:hover,
    .summary-group-title .group-title-row .metric-info-tip:focus-within {
      z-index: 910 !important;
    }
    .summary-groups > div:first-child .summary-group-title:has(.metric-info-tip:hover),
    .summary-groups > div:first-child .summary-group-title:has(.metric-info-tip:focus-within) {
      z-index: 200 !important;
    }
    /* Review panel h3 titles — open below icon (upward was clipped under §6 section-head banner) */
    .review-panel h3 .heading-label-row {
      position: relative !important;
      overflow: visible !important;
    }
    .review-panel h3 .heading-label-row .metric-info-tip {
      position: static !important;
    }
    .review-panel h3 .heading-label-row .metric-info-tip > .metric-info-tooltip {
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      left: 0 !important;
      right: auto !important;
      transform: none !important;
      z-index: 700 !important;
    }
    .section-review .review-panel:has(h3 .metric-info-tip:hover),
    .section-review .review-panel:has(h3 .metric-info-tip:focus-within) {
      z-index: 920 !important;
      position: relative;
    }
    .section-review .section-body:has(.review-panel h3 .metric-info-tip:hover),
    .section-review .section-body:has(.review-panel h3 .metric-info-tip:focus-within) {
      z-index: 910 !important;
      position: relative;
      overflow: visible !important;
    }
    .review-panel h3 .heading-label-row .metric-info-tip:hover,
    .review-panel h3 .heading-label-row .metric-info-tip:focus-within {
      z-index: 930 !important;
    }
    /* Release readiness: wider tooltip + stack above §1 body */
    .release-score-row,
    .release-score-card {
      overflow: visible !important;
      position: relative;
    }
    .release-score-row {
      margin-bottom: 1.5rem;
      z-index: 12 !important;
    }
    .section-summary:has(.release-score-card .metric-info-tip:hover) .section-body,
    .section-summary:has(.release-score-card .metric-info-tip:focus-within) .section-body {
      z-index: 30 !important;
    }
    .release-score-card .label-row .metric-info-tip > .metric-info-tooltip {
      width: min(360px, calc(100vw - 2.5rem)) !important;
      max-width: 360px !important;
      min-width: 18rem;
      z-index: 1200 !important;
    }
    .release-score-card:has(.metric-info-tip:hover),
    .release-score-card:has(.metric-info-tip:focus-within),
    .release-score-row:has(.metric-info-tip:hover),
    .release-score-row:has(.metric-info-tip:focus-within) {
      z-index: 995 !important;
    }
"""

OWNERSHIP_TOOLTIP_CSS_MARKER = "/* ownership section tooltips v3 */"

OWNERSHIP_TOOLTIP_CSS = """
    """ + OWNERSHIP_TOOLTIP_CSS_MARKER + """
    .section-ownership,
    .section-ownership .section-head,
    .section-ownership .section-body,
    .section-ownership .metric-grid,
    .section-ownership .metric-card {
      overflow: visible !important;
    }
    .section-ownership .section-head {
      position: relative;
      z-index: 5;
    }
    .section-ownership .section-head:has(.metric-info-tip:hover),
    .section-ownership .section-head:has(.metric-info-tip:focus-within) {
      z-index: 500 !important;
    }
    .section-ownership .section-head .metric-info-tip > .metric-info-tooltip {
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      left: 50% !important;
      right: auto !important;
      transform: translateX(-50%) !important;
      z-index: 501 !important;
    }
    .section-ownership .section-body {
      position: relative;
      z-index: 1;
    }
    .section-ownership .section-lead-with-tip {
      display: block !important;
      position: relative;
      overflow: visible !important;
      padding-right: 2.25rem;
      margin-bottom: 1.25rem;
    }
    .section-ownership .section-lead-with-tip .metric-info-tip {
      position: absolute;
      top: 0.65rem;
      right: 0.75rem;
      margin: 0;
    }
    .section-ownership .section-lead-with-tip .metric-info-tip > .metric-info-tooltip {
      top: calc(100% + 10px) !important;
      bottom: auto !important;
      left: 50% !important;
      right: auto !important;
      transform: translateX(-50%) !important;
      z-index: 400 !important;
    }
    .section-ownership .section-lead-with-tip .metric-info-tip:hover,
    .section-ownership .section-lead-with-tip .metric-info-tip:focus-within {
      z-index: 450 !important;
    }
    .section-ownership .metric-grid {
      padding-top: 0.25rem;
      position: relative;
      align-items: start;
    }
    .section-ownership .metric-card {
      position: relative;
      isolation: isolate;
    }
    .section-ownership .metric-card:has(.label-row .metric-info-tip:hover),
    .section-ownership .metric-card:has(.label-row .metric-info-tip:focus-within) {
      z-index: 40 !important;
    }
    /* §4 metric cards use global row-anchored tooltips (v21) */
    .ladr-section-lead {
      color: #475569;
      font-size: 0.875rem;
      margin: 0 0 0.75rem;
      line-height: 1.45;
    }
"""

OWNERSHIP_TOOLTIP_CSS_BLOCK_RE = re.compile(
    r"\s*/\* ownership section tooltips v\d+ \*/[\s\S]*?"
    r"(?=\n\s*(?:/\* trace section visibility|\s*</style>))",
    re.MULTILINE,
)

TOOLTIP_LAYOUT_FIX_BLOCK_RE = re.compile(
    r"\s*/\* tooltip layout fix(?: v\d+)? — prevent clipping in panels and sections \*/[\s\S]*?"
    r"(?=\n\s*</style>)",
    re.MULTILINE,
)

TRACE_SECTION_CSS_MARKER = "/* trace section visibility v4 — expandable evidence */"

TRACE_SECTION_CSS = """
    """ + TRACE_SECTION_CSS_MARKER + """
    .section-trace { border: 2px solid #8b5cf6 !important; }
    .section-trace .section-head { background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 100%) !important; }
    .section-trace .section-head h2,
    .section-trace .section-head .heading-label-row { color: #fff !important; text-shadow: 0 1px 2px rgba(0,0,0,0.12); }
    .section-trace .section-body {
      padding: 1.25rem 1.5rem 1.5rem !important;
      background: linear-gradient(180deg, #faf5ff 0%, #fff 100%) !important;
    }
    .section-trace .trace-section-lead {
      color: #4c1d95;
      font-size: 0.875rem;
      margin-bottom: 1rem;
      padding: 0.65rem 0.9rem;
      background: #ede9fe;
      border-left: 3px solid #7c3aed;
      border-radius: 0 6px 6px 0;
      line-height: 1.5;
    }
    .section-trace .table-wrap {
      padding: 0.5rem 0 0 !important;
      overflow-y: visible !important;
      margin-bottom: 1rem;
    }
    .section-trace table.trace-table,
    .section-trace .table-wrap > table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      border: 1px solid #c4b5fd;
      border-radius: 8px;
      overflow: visible;
      font-size: 0.9rem;
      background: #fff;
    }
    .section-trace table th {
      background: #ede9fe !important;
      color: #4c1d95 !important;
      font-weight: 700;
      padding: 0.7rem 0.75rem !important;
      border-bottom: 2px solid #c4b5fd !important;
    }
    .section-trace table td {
      color: #1e293b !important;
      vertical-align: top;
      padding: 0.7rem 0.75rem !important;
      border-bottom: 1px solid #ede9fe !important;
      line-height: 1.45;
    }
    .section-trace tbody tr:nth-child(even) td { background: #faf5ff; }
    .section-trace tbody tr:hover td { background: #f5f3ff; }
    .section-trace td:first-child { font-weight: 700; color: #6d28d9 !important; white-space: nowrap; }
    .section-trace td:nth-child(2) { min-width: 200px; max-width: 340px; }
    .section-trace td.evidence-cell { min-width: 180px; max-width: 320px; }
    .section-trace .evidence-list {
      margin: 0.25rem 0 0.35rem;
      padding-left: 1.15rem;
      font-size: 0.8rem;
      list-style: disc;
    }
    .section-trace .evidence-list code {
      font-size: 0.78rem;
      word-break: break-word;
      white-space: normal;
      background: #f1f5f9;
      padding: 0.1rem 0.25rem;
      border-radius: 3px;
    }
    .section-trace .evidence-empty { color: #94a3b8; }
    .section-trace .evidence-note {
      font-size: 0.78rem;
      color: #475569;
      margin: 0 0 0.35rem;
      line-height: 1.4;
    }
    .section-trace .conf-badge {
      font-size: 0.72rem;
      color: #64748b;
      font-style: italic;
    }
    .badge-nfr { background: #fef3c7; color: #92400e; }
    .badge-fr { background: #ecfdf5; color: #047857; }
    .badge-gap-fill { background: #ede9fe; color: #5b21b6; border: 1px solid #c4b5fd; }
    .section-trace .evidence-tag {
      font-size: 0.68rem;
      color: #6366f1;
      font-weight: 600;
      margin-left: 0.15rem;
    }
    .section-trace .evidence-expand {
      margin: 0.2rem 0 0.35rem;
    }
    .section-trace .evidence-expand > summary.evidence-more {
      font-size: 0.75rem;
      color: #6366f1;
      cursor: pointer;
      list-style: none;
      font-weight: 600;
      padding: 0.15rem 0;
      user-select: none;
    }
    .section-trace .evidence-expand > summary.evidence-more::-webkit-details-marker {
      display: none;
    }
    .section-trace .evidence-expand > summary.evidence-more::before {
      content: "▸ ";
      display: inline-block;
      transition: transform 0.15s ease;
    }
    .section-trace .evidence-expand[open] > summary.evidence-more::before {
      transform: rotate(90deg);
    }
    .section-trace .evidence-list-extra {
      margin-top: 0.25rem;
      padding-left: 1.15rem;
    }
    .section-trace .evidence-list-extra code {
      opacity: 0.92;
    }
"""

PR_TABLE_INFO_CSS = """
    .section-pr th .th-label-row,
    .section-testplan th .th-label-row,
    .section-trace th .th-label-row {
      display: inline-flex; align-items: center; gap: 0.25rem; vertical-align: middle; white-space: nowrap;
    }
    .section-pr th .metric-info-icon,
    .section-testplan th .metric-info-icon,
    .section-trace th .metric-info-icon { width: 0.9rem; height: 0.9rem; font-size: 0.58rem; }
    .section-pr th .metric-info-tooltip,
    .section-testplan th .metric-info-tooltip,
    .section-trace th .metric-info-tooltip { text-transform: none; font-weight: 400; letter-spacing: normal; }
    .section-head .heading-label-row { display: inline-flex; align-items: center; gap: 0.35rem; }
    .section-head .metric-info-icon {
      color: #fff; background: rgba(255,255,255,0.22); border-color: rgba(255,255,255,0.4);
    }
    .section-head .metric-info-tip:hover .metric-info-icon,
    .section-head .metric-info-tip:focus-within .metric-info-icon { background: #fff; color: #1e3a8a; }
    .summary-group-title .group-title-row {
      display: flex; align-items: center; justify-content: space-between; gap: 0.35rem;
    }
    .summary-group-title .group-title-text { flex: 1; }
    .review-panel h3 .heading-label-row { display: inline-flex; align-items: center; gap: 0.35rem; }
    header .verdict { display: flex; align-items: flex-start; gap: 0.45rem; }
    header .verdict .metric-info-tip { margin-top: 0.15rem; flex-shrink: 0; }
    header h1 .heading-label-row { display: inline-flex; align-items: flex-start; gap: 0.35rem; flex-wrap: wrap; }
    header .meta .metric-info-tip { vertical-align: middle; margin-left: 0.15rem; }
    .cache-meta-with-tip, .quick-links-with-tip, .note-box-with-tip, .section-lead-with-tip {
      display: flex; align-items: flex-start; gap: 0.35rem; flex-wrap: wrap;
    }
    .jira-readiness-block .readiness-item .metric-info-tip { margin-left: 0.2rem; vertical-align: middle; }
    .jira-readiness-block ul { list-style: none; padding: 0; margin: 0.5rem 0 0; }
    .jira-readiness-block .readiness-item {
      display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.4rem 0; line-height: 1.45;
    }
    .jira-readiness-block .readiness-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 1.4rem; height: 1.4rem; border-radius: 50%;
      font-weight: 700; font-size: 0.8rem; line-height: 1; flex-shrink: 0; margin-top: 0.05rem;
    }
    .readiness-item.ready-ok .readiness-icon {
      color: var(--pass); background: var(--pass-bg); border: 1px solid var(--pass-border);
    }
    .readiness-item.ready-missing .readiness-icon,
    .readiness-item.ready-warn .readiness-icon {
      color: var(--fail); background: var(--fail-bg); border: 1px solid var(--fail-border);
    }
    .split-metric-with-tip { display: inline-flex; align-items: center; gap: 0.2rem; vertical-align: middle; }
"""

JIRA_READINESS_UI_MARKER = "/* jira readiness status icons */"

JIRA_READINESS_UI_CSS = """
    """ + JIRA_READINESS_UI_MARKER + """
    .jira-readiness-block ul { list-style: none; padding: 0; margin: 0.5rem 0 0; }
    .jira-readiness-block .readiness-item {
      display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.4rem 0; line-height: 1.45;
    }
    .jira-readiness-block .readiness-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 1.4rem; height: 1.4rem; border-radius: 50%;
      font-weight: 700; font-size: 0.8rem; line-height: 1; flex-shrink: 0; margin-top: 0.05rem;
    }
    .readiness-item.ready-ok .readiness-icon {
      color: var(--pass); background: var(--pass-bg); border: 1px solid var(--pass-border);
    }
    .readiness-item.ready-missing .readiness-icon,
    .readiness-item.ready-warn .readiness-icon {
      color: var(--fail); background: var(--fail-bg); border: 1px solid var(--fail-border);
    }
"""

PR_TABLE_COLUMN_INFO: dict[str, str] = {
    "PR": "GitHub pull request number with a link to the PR page.",
    "Repo": "GitHub organization and repository (org/repo) that contains the pull request.",
    "State": "Pull request lifecycle state from GitHub (open, merged, or closed).",
    "Title": "Pull request title as shown on GitHub.",
    "Files": "Count of changed files in the PR diff, including test files.",
    "Dev tests": (
        "Key unit or integration test classes or files added or changed in the PR "
        "that cover dev-owned acceptance criteria."
    ),
    "CI status": (
        "Overall CI check result from gh pr checks — passed, failed, mixed, "
        "or N/A when checks could not be fetched."
    ),
}

SECTION_HEADER_INFO: dict[str, str] = {
    "Coverage summary": (
        "High-level readiness metrics from Jira acceptance criteria, linked PR code "
        "and tests, attached test plan, and CI pipeline coverage."
    ),
    "Linked PR(s)": (
        "GitHub pull requests linked to the Jira story, with CI status and dev test "
        "evidence from the PR diff."
    ),
    "Attached test plan validation": (
        "QMetry test plan from Jira mapped to Jira acceptance criteria and Confluence LADR "
        "requirements (when linked), with LADR ↔ test case traceability and PR alignment checks."
    ),
    "Dev vs QA test ownership": (
        "Which requirements are proven by dev unit/integration tests in the PR versus "
        "handed off to QA for E2E, manual, or regression verification."
    ),
    "Requirements traceability": (
        "Per-requirement view of implementation status, dev test coverage, ownership, "
        "and evidence citations."
    ),
    "Implementation review": (
        "Summary of what is correctly implemented in the PR and remaining gaps or "
        "concerns from the code and test-plan review."
    ),
    "Assumptions and open questions": (
        "Scoring assumptions, mapping rules, and unresolved questions used when "
        "generating this report."
    ),
    "Recommended actions": (
        "Suggested next steps for dev or QA before release based on open gaps."
    ),
}

SUMMARY_GROUP_INFO: dict[str, str] = {
    "Implementation & tests": (
        "Production code and automated test evidence from the linked PR against "
        "Jira acceptance criteria."
    ),
    "QA & release risk": (
        "Test plan coverage, remaining QA verification scope, and open review gaps."
    ),
    "CI pipeline coverage": (
        "Line and branch coverage percentages reported by CI tools on the linked PR."
    ),
}

TESTPLAN_TABLE_COLUMN_INFO: dict[str, str] = {
    "TC": "Test case ID from the attached QMetry test plan.",
    "Scenario": "Section and summary describing the test scenario.",
    "Mapped req": "Jira acceptance criteria (R1, R2, …) and Confluence LADR items (L1, L2, …) mapped to this test case.",
    "GWT": "Whether the test case has full Given, When, and Then steps in the plan.",
    "Given When Then": "Test steps from the QMetry plan in Given/When/Then form.",
    "PR alignment": "Whether the linked PR implementation aligns with this test case.",
    "Evidence": "Mascot fulfillment links when present; otherwise Edit ID, Job ID, Media Request, or other UUIDs from the test plan or mapped Jira acceptance criteria.",
}

LADR_TRACE_TABLE_COLUMN_INFO: dict[str, str] = {
    "LADR ID": "Confluence LADR requirement identifier (L1, L2, …) parsed from the linked design doc.",
    "Requirement": "LADR ESS milestone or status-code text from Confluence.",
    "Test case(s)": "Excel test plan case IDs that semantically cover this LADR requirement.",
    "Status": "Covered when at least one test case maps to this LADR item; Gap when none.",
}

TRACE_TABLE_COLUMN_INFO: dict[str, str] = {
    "ID": "Requirement identifier extracted from the Jira story (R1, R2, …).",
    "Requirement": "Acceptance criteria or requirement text from Jira.",
    "Code": "Whether production code in the PR implements this requirement.",
    "Dev tests": "Whether unit or integration tests in the PR cover this requirement.",
    "Owner": "Who owns verification: Dev, Shared (dev + QA), or QA.",
    "QA scope": "Type of QA verification still needed, if any (E2E, Manual, Regression, etc.).",
    "Evidence": (
        "Changed file paths (or commit message) supporting the code/dev-test assessment. "
        "Confidence: high = matched files; medium/low = keyword-only in diff/commits with no path hit."
    ),
}

OWNERSHIP_LABEL_INFO: dict[str, str] = {
    "Covered by dev tests (unit / integration)": (
        "Requirements already proven by unit or integration tests in the linked PR."
    ),
    "QA handoff": (
        "Requirements QA must still verify in functional, E2E, or manual testing."
    ),
}

REVIEW_PANEL_INFO: dict[str, str] = {
    "Test plan gaps": (
        "Uncovered Jira acceptance criteria or Confluence LADR requirements with no mapped "
        "test case, plus Given/When/Then or PR alignment issues."
    ),
    "LADR ↔ test plan traceability": (
        "Each Confluence LADR requirement (L1…Ln) tied to test case IDs from the Excel "
        "attachment — shows which design scenarios QA validates."
    ),
    "Unmapped test cases": (
        "Test plan scenarios with no mapped Jira R-item or LADR L-item — may indicate missing "
        "requirement tags or orphan scenarios."
    ),
    "Suggested test plan ↔ acceptance criteria mappings": (
        "Low-confidence keyword overlaps between uncovered requirements and test cases — "
        "consider adding explicit R/L tags in the test plan."
    ),
    "✓ Correctly implemented": (
        "Requirements and behaviors that match the Jira story and are supported by PR evidence."
    ),
    "⚠ Gaps and concerns": (
        "Missing implementation, weak test coverage, or contradictions flagged in the review."
    ),
}

VERDICT_INFO = (
    "Overall readiness: Pass when requirements are met; Pass with gaps when minor items "
    "remain; Fail when critical gaps or contradictions exist."
)


def metric_info_icon_html(label: str, tip: str | None = None) -> str:
    text = tip if tip is not None else SUMMARY_METRIC_INFO.get(label, "")
    if not text:
        return ""
    title = f"About {label}"
    return (
        f'<span class="metric-info-tip" tabindex="0" role="button" '
        f'aria-label="{esc(title)}">'
        f'<span class="metric-info-icon" aria-hidden="true">i</span>'
        f'<span class="metric-info-tooltip" role="tooltip">'
        f'<span class="tooltip-title">{esc(title)}</span>'
        f'<span class="tooltip-body">{esc(text)}</span></span></span>'
    )


def render_table_header_row(columns: dict[str, str]) -> str:
    """Table thead row with info-icon tooltips on each column."""
    cells = []
    for col, tip in columns.items():
        icon = metric_info_icon_html(col, tip)
        cells.append(f'<th><span class="th-label-row">{esc(col)}{icon}</span></th>')
    return "<tr>" + "".join(cells) + "</tr>"


def render_pr_table_header_row() -> str:
    """§2 Linked PR(s) thead row with info-icon tooltips on each column."""
    return render_table_header_row(PR_TABLE_COLUMN_INFO)


def _inject_heading_tooltip(html: str, tag: str, title: str, tip: str) -> str:
    if f'aria-label="About {esc(title)}"' in html:
        return html
    if f'<span class="heading-label-row">{esc(title)}' in html:
        return html
    if f'<span class="heading-label-row">{title}' in html:
        return html
    icon = metric_info_icon_html(title, tip)
    inner = f'<span class="heading-label-row">{title}{icon}</span>'
    wrapped = f"<{tag}>{inner}</{tag}>"
    for plain in (f"<{tag}>{title}</{tag}>", f"<{tag}>{esc(title)}</{tag}>"):
        if plain in html:
            return html.replace(plain, wrapped, 1)
    pattern = (
        rf'(<div class="section-head">[\s\S]*?<{tag}>)\s*'
        rf'{re.escape(title)}\s*'
        rf'(</{tag}>)'
    )
    if re.search(pattern, html):
        return re.sub(pattern, rf"\1{inner}\2", html, count=1)
    return html


def _inject_label_row(html: str, label: str, tip: str) -> str:
    if f'<div class="label-row"><div class="label">{label}</div>' in html:
        return html
    plain = f'<div class="label">{label}</div>'
    wrapped = (
        f'<div class="label-row"><div class="label">{label}</div>'
        f"{metric_info_icon_html(label, tip)}</div>"
    )
    if plain in html:
        return html.replace(plain, wrapped, 1)
    return html


def _replace_section_thead(html: str, section_class: str, header_row: str) -> str:
    pattern = (
        rf'(<section class="report-section {section_class}">.*?<thead>\s*)'
        r"<tr>.*?</tr>"
        r"(\s*</thead>)"
    )
    return re.sub(pattern, rf"\1{header_row}\2", html, count=1, flags=re.DOTALL)


def _ensure_info_icon_styles(html: str) -> str:
    bundle = METRIC_INFO_CSS + PR_TABLE_INFO_CSS
    if "metric-info-tip" not in html:
        html = html.replace("</style>", bundle + "\n  </style>", 1)
    elif ".section-head .heading-label-row" not in html:
        html = html.replace("</style>", PR_TABLE_INFO_CSS + "\n  </style>", 1)
    return html


def inject_section_header_tooltips(html: str) -> str:
    for title, tip in SECTION_HEADER_INFO.items():
        html = _inject_heading_tooltip(html, "h2", title, tip)
    return html


def inject_summary_group_tooltips(html: str) -> str:
    for title, tip in SUMMARY_GROUP_INFO.items():
        if f'group-title-text">{esc(title)}' in html:
            continue
        plain = f'<div class="summary-group-title">{esc(title)}</div>'
        wrapped = (
            f'<div class="summary-group-title"><span class="group-title-row">'
            f'<span class="group-title-text">{esc(title)}</span>'
            f"{metric_info_icon_html(title, tip)}</span></div>"
        )
        if plain in html:
            html = html.replace(plain, wrapped, 1)
    return html


def inject_verdict_tooltip(html: str) -> str:
    if "verdict" not in html or 'aria-label="About verdict"' in html:
        return html
    icon = metric_info_icon_html("Verdict", VERDICT_INFO).replace(
        'aria-label="About Verdict"', 'aria-label="About verdict"'
    )
    return re.sub(
        r'(<div class="verdict verdict-[^"]+">)',
        rf"\1{icon}",
        html,
        count=1,
    )


def inject_pr_table_header_tooltips(html: str) -> str:
    if "section-pr" not in html:
        return html
    return _replace_section_thead(html, "section-pr", render_pr_table_header_row())


def inject_testplan_table_header_tooltips(html: str) -> str:
    if "section-testplan" not in html:
        return html
    html = _replace_section_thead(
        html, "section-testplan", render_table_header_row(TESTPLAN_TABLE_COLUMN_INFO)
    )
    if "ladr-trace-table" not in html:
        return html
    pattern = (
        r'(<table class="ladr-trace-table">\s*<thead>\s*)'
        r"<tr>.*?</tr>"
        r"(\s*</thead>)"
    )
    return re.sub(
        pattern,
        rf"\1{render_table_header_row(LADR_TRACE_TABLE_COLUMN_INFO)}\2",
        html,
        count=1,
        flags=re.DOTALL,
    )


def inject_trace_table_header_tooltips(html: str) -> str:
    if "section-trace" not in html:
        return html
    return _replace_section_thead(
        html, "section-trace", render_table_header_row(TRACE_TABLE_COLUMN_INFO)
    )


def inject_ownership_card_tooltips(html: str) -> str:
    if "section-ownership" not in html:
        return html
    for label, tip in OWNERSHIP_LABEL_INFO.items():
        html = _inject_label_row(html, label, tip)
    return html


def inject_review_panel_tooltips(html: str) -> str:
    for title, tip in REVIEW_PANEL_INFO.items():
        html = _inject_heading_tooltip(html, "h3", title, tip)
    return html


def inject_report_h1_tooltip(html: str) -> str:
    """Report h1 title is intentionally without an info tooltip."""
    if 'aria-label="About Report title"' in html:
        html = re.sub(
            r"<h1><span class=\"heading-label-row\">([\s\S]*?)"
            r"<span class=\"metric-info-tip\"[\s\S]*?</span></span></h1>",
            r"<h1>\1</h1>",
            html,
            count=1,
        )
    return html


def inject_meta_field_tooltips(html: str) -> str:
    for label, tip in META_FIELD_INFO.items():
        key = f"About {label}"
        if key in html:
            continue
        plain = f"<strong>{label}:</strong>"
        if plain not in html:
            continue
        html = html.replace(plain, plain + metric_info_icon_html(label, tip), 1)
    return html


def inject_cache_meta_tooltip(html: str) -> str:
    if 'aria-label="About Cache freshness"' in html:
        return html
    plain = '<div class="cache-meta">'
    if plain not in html:
        return html
    icon = metric_info_icon_html("Cache freshness", CACHE_META_INFO)
    return html.replace(plain, f'<div class="cache-meta cache-meta-with-tip">{icon} ', 1)


def inject_quick_links_tooltip(html: str) -> str:
    if 'aria-label="About Quick links"' in html:
        return html
    plain = '<div class="quick-links">'
    if plain not in html:
        return html
    icon = metric_info_icon_html("Quick links", QUICK_LINKS_INFO)
    return html.replace(plain, f'<div class="quick-links quick-links-with-tip">{icon} ', 1)


def inject_readiness_block_tooltips(html: str) -> str:
    """Checklist item tooltips only; Jira input readiness h3 heading has no tooltip."""
    for title in READINESS_PANEL_INFO:
        if f'aria-label="About {title}"' in html:
            html = re.sub(
                rf"<h3><span class=\"heading-label-row\">{re.escape(title)}"
                r"<span class=\"metric-info-tip\"[\s\S]*?</span></span></h3>",
                f"<h3>{title}</h3>",
                html,
                count=1,
            )
    for label, tip in READINESS_ITEM_INFO.items():
        marker = f'<strong>{label}</strong>{metric_info_icon_html(label, tip)}'
        if marker in html:
            continue
        plain = f"<strong>{label}</strong>"
        if plain in html:
            html = html.replace(plain, marker, 1)
    return html


def inject_note_box_tooltip(html: str) -> str:
    if 'aria-label="About Test plan source"' in html:
        return html
    plain = '<div class="note-box">'
    if plain not in html:
        return html
    icon = metric_info_icon_html("Test plan source", NOTE_BOX_INFO)
    return html.replace(
        plain,
        f'<div class="note-box note-box-with-tip">{icon} ',
        1,
    )


def inject_split_metric_tooltips(html: str) -> str:
    for prefix, tip in SPLIT_METRIC_INFO.items():
        if f'aria-label="About {prefix.rstrip(":")}' in html:
            continue
        needle = f'<span class="split-metric">{prefix}'
        if needle not in html:
            continue
        icon = metric_info_icon_html(prefix.rstrip(":"), tip)
        html = html.replace(
            f'<span class="split-metric">{prefix}',
            f'<span class="split-metric split-metric-with-tip">{icon} {prefix}',
            1,
        )
    return html


def _normalize_ladr_section_lead(html: str) -> str:
    """LADR block in §3 must not use section-lead (reserved for §4 ownership intro)."""
    html = re.sub(
        r'(<div class="review-panel review-info ladr-trace-block"[\s\S]*?<h3>[^<]*</h3>\s*)'
        r'<p class="section-lead section-lead-with-tip">'
        r'<span class="metric-info-tip" tabindex="0" role="button" aria-label="About Dev vs QA ownership">'
        r'<span class="metric-info-icon" aria-hidden="true">i</span>'
        r'<span class="metric-info-tooltip">[^<]*</span></span>\s*',
        r'\1<p class="ladr-section-lead">',
        html,
        count=1,
    )
    return re.sub(
        r'(<div class="review-panel review-info ladr-trace-block"[\s\S]*?<h3>[^<]*</h3>\s*)'
        r'<p class="section-lead">',
        r'\1<p class="ladr-section-lead">',
        html,
        count=1,
    )


def _normalize_ownership_section_lead_icon(html: str) -> str:
    """Move §4 lead info icon to end of callout (v1 injected it at the start)."""
    icon = metric_info_icon_html("Dev vs QA ownership", SECTION_LEAD_INFO)
    lead_tip_re = (
        r'<span class="metric-info-tip" tabindex="0" role="button" '
        r'aria-label="About Dev vs QA ownership">'
        r'<span class="metric-info-icon" aria-hidden="true">i</span>'
        r'<span class="metric-info-tooltip">[^<]*</span></span>'
    )
    pattern = (
        r'(<section class="report-section section-ownership">[\s\S]*?)'
        r'<p class="section-lead section-lead-with-tip">\s*'
        + lead_tip_re
        + r'\s*([\s\S]*?)</p>'
    )

    def _repl(m: re.Match[str]) -> str:
        body = re.sub(r"\s+", " ", m.group(2).strip())
        return f'{m.group(1)}<p class="section-lead section-lead-with-tip">{body} {icon}</p>'

    return re.sub(pattern, _repl, html, count=1, flags=re.DOTALL)


def inject_lead_paragraph_tooltips(html: str) -> str:
    """Standard info icon on §3 LADR and §5 trace intro paragraphs."""
    for css_class, (label, tip) in LEAD_PARAGRAPH_INFO.items():
        aria = f'aria-label="About {esc(label)}"'
        if aria in html:
            continue
        pattern = rf'(<p class="{re.escape(css_class)}">)([\s\S]*?)(</p>)'
        match = re.search(pattern, html)
        if not match:
            continue
        body = match.group(2).strip()
        icon = metric_info_icon_html(label, tip)
        replacement = (
            f'<p class="{css_class} {css_class}-with-tip">{body} {icon}</p>'
        )
        html = html[: match.start()] + replacement + html[match.end() :]
    return html


def inject_section_lead_tooltip(html: str) -> str:
    """Tooltip on §4 ownership intro only (not LADR lead in §3)."""
    html = _normalize_ownership_section_lead_icon(html)
    if re.search(
        r'<section class="report-section section-ownership">[\s\S]*?'
        r'<p class="section-lead section-lead-with-tip">',
        html,
    ):
        return html
    icon = metric_info_icon_html("Dev vs QA ownership", SECTION_LEAD_INFO)
    pattern = (
        r'(<section class="report-section section-ownership">[\s\S]*?)'
        r'<p class="section-lead">([\s\S]*?)</p>'
    )
    if not re.search(pattern, html, flags=re.DOTALL):
        return html
    return re.sub(
        pattern,
        rf'\1<p class="section-lead section-lead-with-tip">\2 {icon}</p>',
        html,
        count=1,
        flags=re.DOTALL,
    )


def inject_ownership_tooltip_styles(html: str) -> str:
    """§4 Dev vs QA ownership tooltip layout (idempotent; upgrades v1 → v2)."""
    if OWNERSHIP_TOOLTIP_CSS_MARKER in html:
        return html
    html = OWNERSHIP_TOOLTIP_CSS_BLOCK_RE.sub("", html)
    return html.replace("</style>", OWNERSHIP_TOOLTIP_CSS + "\n  </style>", 1)


def inject_all_metric_label_tooltips(html: str) -> str:
    """Wrap summary, ownership, and release-score metric labels with info icons."""
    merged: dict[str, str] = {}
    merged.update(SUMMARY_METRIC_INFO)
    merged.update(OWNERSHIP_LABEL_INFO)
    for label, tip in merged.items():
        html = _inject_label_row(html, label, tip)
    return html


def _strip_legacy_tooltip_layout_fix(html: str) -> str:
    """Remove v1 tooltip-layout CSS (comment optional; body ends at th:last-child rule)."""
    return re.sub(
        r"\s*(?:/\* tooltip layout fix(?: v\d+)? — prevent clipping[^*]*\*/\s*)?"
        r"\.report-section,\s*\n\s*\.report-section \.section-body,.*?"
        r"th:last-child \.metric-info-tooltip \{[^}]+\}\s*",
        "\n",
        html,
        count=1,
        flags=re.DOTALL,
    )


TRACE_SECTION_CSS_BLOCK_RE = re.compile(
    r"\s*/\* trace section visibility v\d+ \*/[\s\S]*?"
    r"(?=\n\s*(?:/\* tooltip layout fix|\s*</style>))",
    re.MULTILINE,
)


def inject_trace_section_styles(html: str) -> str:
    """Stronger §5 Requirements traceability layout (idempotent; upgrades v1 → v2)."""
    if TRACE_SECTION_CSS_MARKER in html:
        return html
    html = TRACE_SECTION_CSS_BLOCK_RE.sub("", html)
    return html.replace("</style>", TRACE_SECTION_CSS + "\n  </style>", 1)


def inject_trace_section_markup(html: str) -> str:
    """Add section lead and trace-table class when template is legacy."""
    if "trace-section-lead" not in html and 'class="report-section section-trace"' in html:
        html = re.sub(
            r'(<section class="report-section section-trace">.*?<div class="section-body">)\s*'
            r'(<div class="table-wrap">)',
            r'\1\n        <p class="trace-section-lead">Per-requirement mapping from Jira acceptance criteria '
            r"and linked Confluence LADR (when present) to branch/PR code, dev tests, ownership, "
            r"and file-level evidence.</p>\n        \2",
            html,
            count=1,
            flags=re.DOTALL,
        )
    if 'class="trace-table"' not in html:
        html = re.sub(
            r'(<section class="report-section section-trace">.*?<div class="table-wrap">\s*)<table>',
            r'\1<table class="trace-table">',
            html,
            count=1,
            flags=re.DOTALL,
        )
    return html


def _strip_modern_tooltip_layout_fix(html: str) -> str:
    """Remove tooltip layout fix v4+ block so v20 can replace v19."""
    return re.sub(
        r"\s*/\* tooltip layout fix v\d+[^*]*\*/[\s\S]*?"
        r"(?=\n\s*/\* ownership section tooltips|\n\s*/\* trace section visibility|\n\s*</style>)",
        "\n",
        html,
        count=1,
    )


def inject_tooltip_layout_fix(html: str) -> str:
    """Ensure tooltip CSS avoids overflow clipping (idempotent; upgrades v1–v19 → v20)."""
    html = html.replace("cursor: help;", "cursor: pointer;")
    html = _strip_legacy_tooltip_layout_fix(html)
    html = TOOLTIP_LAYOUT_FIX_BLOCK_RE.sub("", html)
    html = _strip_modern_tooltip_layout_fix(html)
    if TOOLTIP_LAYOUT_FIX_MARKER in html:
        return html
    return html.replace("</style>", TOOLTIP_LAYOUT_FIX_CSS + "\n  </style>", 1)


def render_report_footer() -> str:
    """Report footer with agent name and developer credit."""
    return (
        f"<footer>Generated by {REPORT_AGENT_NAME} · "
        f"Developed by {esc(REPORT_DEVELOPER)}</footer>"
    )


def inject_report_footer(html: str) -> str:
    """Ensure report footer includes agent and developer attribution (idempotent)."""
    footer = render_report_footer()
    if footer in html:
        return html
    if re.search(r"<footer>\s*Generated by Req2Release\s*</footer>", html):
        return re.sub(
            r"<footer>\s*Generated by Req2Release\s*</footer>",
            footer,
            html,
            count=1,
        )
    if "<footer>" in html:
        return re.sub(r"<footer>.*?</footer>", footer, html, count=1, flags=re.DOTALL)
    if "</body>" in html:
        return html.replace("</body>", f"    {footer}\n  </body>", 1)
    return html


def inject_metric_info_click_script(html: str) -> str:
    """Click (or tap) the i icon toggles the definition callout; Escape / outside click closes."""
    if METRIC_INFO_CLICK_JS_MARKER in html:
        return html
    script = f"  <script>{METRIC_INFO_CLICK_JS}\n  </script>"
    if "</body>" in html:
        return html.replace("</body>", f"{script}\n  </body>", 1)
    return html + script


def normalize_jira_readiness_icons(html: str) -> str:
    """Green ✓ when input present; red ✗ when missing (upgrades legacy ! / ready-warn)."""
    if "jira-readiness-block" not in html:
        return html
    html = html.replace('class="readiness-item ready-warn"', 'class="readiness-item ready-missing"')
    html = re.sub(
        r'(<li class="readiness-item ready-missing">)\s*'
        r'<span class="readiness-icon"[^>]*>!</span>',
        r'\1<span class="readiness-icon" aria-hidden="true">✗</span>',
        html,
        flags=re.I,
    )
    html = re.sub(
        r'(<li class="readiness-item ready-ok">)\s*'
        r'<span class="readiness-icon"(?![^>]*aria-hidden)[^>]*>',
        r'\1<span class="readiness-icon" aria-hidden="true">',
        html,
        flags=re.I,
    )
    return html


METRIC_INFO_CSS_BLOCK_RE = re.compile(
    r"\s*\.label-row \{ display: flex[\s\S]*?"
    r"\.ladr-section-lead-with-tip \.metric-info-tip \{[\s\S]*?\}\s*",
    re.MULTILINE,
)

PR_TABLE_INFO_CSS_BLOCK_RE = re.compile(
    r"\s*\.section-pr th \.th-label-row[\s\S]*?"
    r"\.split-metric-with-tip \{[\s\S]*?\}\s*",
    re.MULTILINE,
)

METRIC_INFO_SCRIPT_RE = re.compile(
    r"\s*<script>\s*/\* metric-info-tip click toggle \*/[\s\S]*?</script>",
    re.IGNORECASE,
)


def _remove_metric_info_tip_spans(html: str) -> str:
    """Remove nested metric-info-tip markup (one span tree per iteration)."""
    marker = '<span class="metric-info-tip"'
    while marker in html:
        start = html.find(marker)
        if start < 0:
            break
        depth = 0
        i = start
        end = -1
        while i < len(html):
            if html.startswith("<span", i):
                depth += 1
                close = html.find(">", i)
                if close < 0:
                    break
                i = close + 1
            elif html.startswith("</span>", i):
                depth -= 1
                i += len("</span>")
                if depth == 0:
                    end = i
                    break
            else:
                i += 1
        if end < 0:
            break
        html = html[:start] + html[end:]
    return html


def strip_report_tooltips(html: str) -> str:
    """Remove info-icon tooltips, related CSS, and click script (idempotent)."""
    html = _remove_metric_info_tip_spans(html)
    html = METRIC_INFO_CSS_BLOCK_RE.sub("", html)
    html = PR_TABLE_INFO_CSS_BLOCK_RE.sub("", html)
    html = TOOLTIP_LAYOUT_FIX_BLOCK_RE.sub("", html)
    html = _strip_modern_tooltip_layout_fix(html)
    html = OWNERSHIP_TOOLTIP_CSS_BLOCK_RE.sub("", html)
    html = METRIC_INFO_SCRIPT_RE.sub("", html)
    html = _strip_legacy_tooltip_layout_fix(html)
    for tag in ("h1", "h2", "h3"):
        html = re.sub(
            rf"<{tag}><span class=\"heading-label-row\">([\s\S]*?)</span></{tag}>",
            rf"<{tag}>\1</{tag}>",
            html,
            flags=re.IGNORECASE,
        )
    html = re.sub(
        r'<div class="summary-group-title"><span class="group-title-row">'
        r'<span class="group-title-text">([^<]*)</span></span></div>',
        r'<div class="summary-group-title">\1</div>',
        html,
    )
    html = re.sub(
        r'<div class="label-row"><div class="label">([^<]*)</div>\s*</div>',
        r'<div class="label">\1</div>',
        html,
    )
    html = re.sub(
        r"<th><span class=\"th-label-row\">([^<]*)</span></th>",
        r"<th>\1</th>",
        html,
    )
    html = html.replace("cache-meta-with-tip", "cache-meta")
    html = html.replace("quick-links-with-tip", "quick-links")
    html = html.replace("note-box-with-tip", "note-box")
    html = html.replace("split-metric-with-tip", "split-metric")
    html = re.sub(r'\bsection-lead-with-tip\b', "section-lead", html)
    html = re.sub(r'\btrace-section-lead-with-tip\b', "trace-section-lead", html)
    html = re.sub(r'\bladr-section-lead-with-tip\b', "ladr-section-lead", html)
    html = re.sub(
        r'<p class="section-lead">\s*([\s\S]*?)\s*</p>',
        lambda m: f'<p class="section-lead">{m.group(1).strip()}</p>',
        html,
        count=1,
    )
    return html


def inject_jira_readiness_styles(html: str) -> str:
    """Green ✓ / red ✗ readiness row styling (no tooltips)."""
    if JIRA_READINESS_UI_MARKER in html or "jira-readiness-block" not in html:
        return html
    return html.replace("</style>", JIRA_READINESS_UI_CSS + "\n  </style>", 1)


RECOMMENDED_ACTIONS_UI_MARKER = "recommended-actions-groups v1"
RECOMMENDED_ACTIONS_UI_CSS = f"""
    /* {RECOMMENDED_ACTIONS_UI_MARKER} */
    .section-actions .actions-group-title {{
      font-size: 0.95rem;
      font-weight: 700;
      color: #9a3412;
      margin: 1rem 0 0.5rem;
      padding-bottom: 0.25rem;
      border-bottom: 1px solid #fed7aa;
    }}
    .section-actions .recommended-actions-groups .actions-group-title:first-child {{
      margin-top: 0;
    }}
    .section-actions .actions-group-list {{
      list-style: none;
      padding-left: 0;
      counter-reset: action;
      margin-bottom: 0.25rem;
    }}
"""


def inject_recommended_actions_styles(html: str) -> str:
    """§8 Dev/QA action group layout (no tooltip changes)."""
    if RECOMMENDED_ACTIONS_UI_MARKER in html or "recommended-actions-groups" not in html:
        return html
    return html.replace("</style>", RECOMMENDED_ACTIONS_UI_CSS + "\n  </style>", 1)


def inject_recommended_actions_markup(html: str) -> str:
    """Unwrap legacy <ol> around Dev/QA action groups (template-safe)."""
    if "recommended-actions-groups" not in html:
        return html
    return re.sub(
        r"(<div class=\"section-body\">\s*)<ol>\s*(<div class=\"recommended-actions-groups\">.*?</div>)\s*</ol>",
        r"\1\2",
        html,
        count=1,
        flags=re.DOTALL,
    )


def apply_report_ui_enhancements(html: str) -> str:
    """Info-icon tooltips on all labels, readiness icons, trace layout, footer."""
    html = strip_report_tooltips(html)
    html = _ensure_info_icon_styles(html)
    html = inject_jira_readiness_styles(html)
    html = normalize_jira_readiness_icons(html)
    html = inject_tooltip_layout_fix(html)
    html = inject_report_h1_tooltip(html)
    html = inject_meta_field_tooltips(html)
    html = inject_cache_meta_tooltip(html)
    html = inject_quick_links_tooltip(html)
    html = inject_readiness_block_tooltips(html)
    html = inject_verdict_tooltip(html)
    html = inject_section_header_tooltips(html)
    html = inject_all_metric_label_tooltips(html)
    html = inject_summary_group_tooltips(html)
    html = inject_pr_table_header_tooltips(html)
    html = inject_testplan_table_header_tooltips(html)
    html = inject_note_box_tooltip(html)
    html = inject_split_metric_tooltips(html)
    html = _normalize_ladr_section_lead(html)
    html = inject_lead_paragraph_tooltips(html)
    html = inject_section_lead_tooltip(html)
    html = inject_ownership_card_tooltips(html)
    html = inject_ownership_tooltip_styles(html)
    html = inject_review_panel_tooltips(html)
    html = inject_trace_table_header_tooltips(html)
    html = inject_trace_section_styles(html)
    html = inject_trace_section_markup(html)
    html = inject_lead_paragraph_tooltips(html)
    html = inject_recommended_actions_styles(html)
    html = inject_recommended_actions_markup(html)
    html = inject_report_footer(html)
    return html


def wrap_summary_metric_labels(html: str) -> str:
    """Add info-icon tooltips to §1 coverage summary metric labels (legacy alias)."""
    return inject_all_metric_label_tooltips(html)
