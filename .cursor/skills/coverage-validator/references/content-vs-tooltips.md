# Report content vs tooltips (mandatory for agents)

When enhancing the coverage validator or testcase writer, **change report data and section body HTML only** — never edit tooltip copy or layout unless the user explicitly requests a tooltip/UI change.

## Safe to change (content / metrics / § body)

| Area | Scripts / functions |
|------|---------------------|
| §3 test plan rows, note, gaps | `fetch_jira_testplan.py`, `build_testplan_report_fields()`, `build_testplan_summary_note()` |
| §3 Evidence column | `render_testplan_evidence()`, `testplan_evidence.py` (`testPlanSource: workspace_generated`) |
| §4 Dev vs QA handoff | `build_qa_ownership_fields()` |
| §6 Implementation review | `build_correctly_implemented_list()`, `build_implementation_gaps_list()` |
| §6 Open gaps summary card | `build_implementation_gaps_list()` (count) + `build_open_gaps_detail(gap_summary=…)` — condensed note with **see §6 for full list** when ≥5 gaps |
| §7 Assumptions | `build_assumptions_list()` |
| §8 Recommended actions | `build_recommended_actions_list()` — **Dev** and **QA** sub-lists |
| Summary QA scope cards | `_format_qa_scope_summary()`, `_format_qa_scope_detail()` |
| §5 trace rows | `render_requirement_rows_from_mapping()` |
| Verdict, coverage % | `build_coverage_report.py`, mapping cache |
| Testcase writer output | `write_testcase_excel.py`, cache TSV only |

## Do not change without explicit UI request

| Area | Where defined |
|------|----------------|
| Tooltip titles/bodies (`About …`) | `SUMMARY_METRIC_INFO`, `PR_TABLE_COLUMN_INFO`, `SECTION_HEADER_INFO`, `READINESS_ITEM_INFO`, etc. in `coverage_report_helpers.py` |
| `apply_report_ui_enhancements()` tooltip injection logic | Same module — layout v22 positioning |
| `report-template.html` h2 tooltip markup | Template (prefer `inject_*` helpers for new layout CSS only) |

## Allowed layout CSS (no tooltip text changes)

- `inject_recommended_actions_styles()` — §8 Dev/QA group headings
- `inject_recommended_actions_markup()` — unwrap legacy `<ol>` around action groups
- Metric card / readiness **icon** colors (not tooltip strings)

## Test plan honesty rules (content)

| Source | `testPlanSummaryNote` | Evidence column |
|--------|----------------------|-----------------|
| Jira attachment | Downloaded filename + sheet | Mascot / SIT Jobs IDs |
| SharePoint/Domino local | Referenced filename + sheet | Mascot / SIT Jobs |
| `workspace_generated` | Local QMetry + msc-testcase-writer note | **No execution evidence** (do not scrape step UUIDs) |
| `referenced_not_local` | Setup hint | Pending until file added |
