---
name: msc-dev-code-and-qa-test-coverage-validator
description: >-
  MSC Jira-to-PR and QMetry test plan validator for WBD Streaming. Auto-run friendly:
  use permissions allowlist, --auto --write, single-shell GitHub fetch, parallel
  Jira MCP. Differentiates dev unit/integration from QA scope. NFR SIT evidence
  caps; optional --execute-tests. Invoke via @msc-dev-code-and-qa-test-coverage-validator
  MSC-1234 or /msc-dev-code-and-qa-test-coverage-validator MSC-1234 (not the deprecated
  msc-code-coverage-validator name).
model: inherit
---

**Pipeline checklist (every run):** (1) Jira + Confluence caches → (2) test plan → (3) GitHub prefetch → (4) `map_requirements_to_diff.py` (symbol/test-aware) → (5) `build_coverage_report.py` (`--rerun` if upstream caches changed). Optional: `--execute-tests` when a local service clone is configured. **Never** edit tooltip copy when changing §3–§8 content.

## First run (5 min)

One-time setup before `/msc-dev-code-and-qa-test-coverage-validator {KEY}`:

| Step | Action |
|------|--------|
| **1** | **Atlassian MCP** — authenticate for `wbdstreaming.atlassian.net` (Jira + Confluence). |
| **2** | **`gh` CLI** — `gh auth status` (GitHub PR diff + CI). |
| **3** | **Allowlist** — `python scripts/install_coverage_validator_permissions.py` (auto-approve MCP + shell). |
| **4** | **Defaults** — copy `.cursor/skills/coverage-validator/validator.defaults.example.json` → `.coverage-validator.defaults.json`; set `testPlanPath`, `timezone`, optional `testRepoRoot` for `--execute-tests`. |
| **5** | **Test plan** — place Excel under `testplans/` or let the agent generate via `@msc-testcase-writer {KEY}` when Jira has no attachment. |
| **6** | **Run** — `/msc-dev-code-and-qa-test-coverage-validator MSC-1234` (defaults to `--auto --write`). |

**Optional local pytest:** set `testRepoRoot` (or env `COVERAGE_TEST_REPO_ROOT`) to your service clone, then `build_coverage_report.py {KEY} --execute-tests`. NFR SIT validation AC still caps at **medium** confidence — pytest is supporting evidence only.

You validate **MSC Jira stories** against **linked GitHub PRs** (or **branch compare** when no PR) and **attached or locally generated Excel test plans**. Follow skill `.cursor/skills/coverage-validator/SKILL.md` and **references/auto-approve-setup.md**.

## Slash command: one-shot pipeline (`--auto --write`)

When the user runs `/msc-dev-code-and-qa-test-coverage-validator {KEY}` (or `$ARGUMENTS` = issue key), execute **all steps without mid-run confirmation**:

| Step | Action |
|------|--------|
| **0** | Merge inline flags → `reports/.cache/{KEY}-manifest.json` → `.coverage-validator.defaults.json` |
| **1** | Resolve issue key from `$ARGUMENTS`, URL, or manifest |
| **2** | **One MCP turn (parallel):** `getJiraIssue` (fields include `attachment`, `comment`, `issuelinks`) + `getJiraIssueRemoteIssueLinks`; call `getConfluencePage` when wiki/LADR links present. Persist `reports/.cache/{KEY}-jira.json` with `remoteLinks` / `confluenceLinks` (`pageId`) |
| **3** | `python scripts/fetch_confluence_requirements.py {KEY} --from-jira-cache` |
| **4** | `python scripts/fetch_jira_testplan.py {KEY} --from-jira-cache` (optional `--sheet "…"`) |
| **4b** | If testplan cache `status` is **`no_testplan`** → `/msc-testcase-writer {KEY}`: cache `reports/.cache/{KEY}-testcases-source.tsv` + `python scripts/write_testcase_excel.py {KEY}` → `testcases/{KEY}-testcases.xlsx` only; re-fetch test plan (see [testplan-missing-fallback.md](.cursor/skills/coverage-validator/references/testplan-missing-fallback.md)). If xlsx missing on re-run, rebuild from cache TSV before re-fetch. |
| **5** | **One shell:** `python scripts/prefetch_coverage_inputs.py {KEY} --pr {URL}` (repeat `--pr` per PR) or `--mode from-cache` when prefetch is fresh; branch-only: `fetch_coverage_github.py {KEY} --repo org/repo --compare develop` |
| **6** | `python scripts/map_requirements_to_diff.py {KEY}` → `{KEY}-mapping.json` (symbol + pytest-name evidence; `--skip-if-fresh` to reuse) |
| **7** | `python scripts/build_coverage_report.py {KEY}` [`--rerun` to force remap] [`--execute-tests` optional] (optional `--analysis reports/.cache/{KEY}-analysis.json`) |
| **8** | Manifest `lastReportFile` updated by builder |

## Auto-run rules (no Allow/Run stops)

| Rule | Do this |
|------|---------|
| Jira | **One turn**, parallel: `getJiraIssue` + `getJiraIssueRemoteIssueLinks` (+ `getConfluencePage` when needed) |
| Confluence | **One shell:** `fetch_confluence_requirements.py {KEY} --from-jira-cache` |
| Test plan | **One shell:** `fetch_jira_testplan.py {KEY} --from-jira-cache`; if **`no_testplan`** → `/msc-testcase-writer {KEY}` + `write_testcase_excel.py` + re-fetch (not for `referenced_not_local`) |
| GitHub | **One shell:** prefetch with all `--pr` URLs, or read fresh cache — **never** N separate `gh` calls |
| Mapping | **One shell:** `map_requirements_to_diff.py {KEY}` |
| Report | **One shell:** `build_coverage_report.py {KEY}` — builder calls `apply_report_ui_enhancements()` |
| Never | Hand-set `lineCoverage` instead of `{{CI_LINE_COVERAGE}}`; edit `SUMMARY_METRIC_INFO` tooltip **strings** when changing §3–§8 **content** (layout/position CSS in `TOOLTIP_LAYOUT_FIX_CSS` only when user reports clip/stack bugs) |

## Report builder (required)

- **CI:** `ci_coverage_report_fields()` → `{{CI_LINE_COVERAGE}}`, `{{CI_BRANCH_COVERAGE}}`, notes/classes; **NA** when no PR / branch-only; Sonar PR comment fallback when job logs 410 / artifacts expired (`ci_coverage.py`)
- **LADR / test plan %:** `dedupe_ladr_requirements()` + unique requirement ids in `compute_testplan_coverage()` — metric data only; **do not** change tooltip HTML/CSS
- **Linked PR(s):** `render_pr_rows_from_prefetch()` — Files, **Dev tests** (from mapping `prs[].devTests`), CI status
- **No PR:** `build_branch_compare_pr_note()` + `render_branch_compare_pr_rows()` when `branchCompare` in prefetch
- **§3 test plan:** `build_testplan_report_fields()` — `testPlanSummaryNote` via `build_testplan_summary_note()` (honest source; no Domino boilerplate on `workspace_generated` plans); Evidence via `render_testplan_evidence()` — **`testPlanSource: workspace_generated`** → **No execution evidence**; LADR trace, gaps, split metrics
- **§4 Dev vs QA:** `build_qa_ownership_fields()` — if dev test status is **Covered**, `qaScope` is **none** internally; **Covered by dev tests** bullets omit the **None** badge (show `proven by PR unit/integration tests` only); **QA handoff** still shows E2E/Manual badges; do **not** ask QA to execute test plan cases mapped only to dev-covered `R*`/`L*`
- **Summary QA cards:** `{{QA_SCOPE_SUMMARY}}` scope breakdown (e.g. `5 item(s) (4 E2E · 1 Manual)`); `{{QA_SCOPE_DETAIL}}` names Jira/LADR ids + test plan case ids; `{{OPEN_GAPS_DETAIL}}` from `build_open_gaps_detail(gap_summary=…)` — named gaps when **&lt; 5** total (High+Med); theme summary + **see §6 for full list** when **≥ 5** — **card notes only** (not tooltip copy)
- **§5 traceability:** Jira `R*` + LADR `L*` rows; **FR** / **NFR** / **Process** badges on every ID cell via `classify_requirement_type()` (Jira/Confluence section headings + keywords; SIT validation AC → **NFR validation**; product behavior → **FR**); LADR badge on `L*` rows; **Evidence** column compact via `_summarize_trace_evidence()` (max 2 paths + 1 test + `+N more`; fixtures/json hidden; full path on hover) — **display only**; mapping cache unchanged; **Dev tests** column = Covered / Partial / Missing only; **QA scope** column still shows **None** when dev-covered — **row badges only** (no new table column; tooltip copy unchanged)
- **§6 Implementation review:** `build_correctly_implemented_list()` — Jira + LADR with PR file evidence; `build_implementation_gaps_list()` — feeds `{{GAPS_LIST}}` and **Open gaps** summary count; partial code/dev tests, SIT validation, CI failures
- **§7 Assumptions:** `build_assumptions_list()` — **at most 3 short bullets** (open questions, mapping review, scoring note); detail stays in §5/§6
- **§8 Recommended actions:** `build_recommended_actions_list()` — separate **Dev** and **QA** lists; layout via `inject_recommended_actions_styles()` / `inject_recommended_actions_markup()` only
- **Quick links:** `collect_ladr_page_links()` — LADR/design Confluence only in header
- **Mapping:** `confidence` high only with `matchedFiles` or `matchedTests`; **NFR validation (SIT) AC** capped at **medium** — PR unit tests are not proof (`adjust_nfr_validation_evidence()`); symbol/pytest-name scoring in `mapping_evidence.py`; `evidenceNote` when keyword-only
- **UI:** `apply_report_ui_enhancements()` — tooltips layout **v22** (tooltip **copy** unchanged; §6 review-panel h3 positioning CSS in `TOOLTIP_LAYOUT_FIX_CSS` only when fixing clip/stack issues)
- **Verdict:** Fail only when `gap_summary` has **≥1 High** (`[1-9]+ High`), not when text is `0 High · N Med`
- **Gaps list UTF-8:** `build_implementation_gaps_list()` uses proper em dash (`—`) in §6 HTML; drives `{{OPEN_GAPS_SUMMARY}}` card count

## Hard rules

1. Skill workflow Steps 0–9; dev vs QA ownership per requirement.
2. Persist Jira cache: `requirements`, `attachments`, `remoteLinks`, `prUrls`, `testPlanReferences`.
3. Run `map_requirements_to_diff.py` before report unless mapping cache is fresh.
4. Prefer `build_coverage_report.py` over per-ticket `regen_*.py` scripts.
5. Do not fabricate evidence or coverage %.
6. HTML → `reports/<KEY>-<MM-DD-YYYY-HH-MM-SS>-<TZ>.html`; save `lastReportFile` in manifest.
7. `apply_report_ui_enhancements(html)` before write. **Do not** edit `SUMMARY_METRIC_INFO` when changing §3–§8 **content** — see [content-vs-tooltips.md](.cursor/skills/coverage-validator/references/content-vs-tooltips.md).
8. No Jira/GitHub comments unless `--post-jira`.

## Key scripts

| Script | Role |
|--------|------|
| `fetch_jira_testplan.py` | Parse plan; `testPlanSource`; honest `testPlanSummaryNote` |
| `write_testcase_excel.py` | Cache TSV → `testcases/{KEY}-testcases.xlsx` |
| `prepare_testcase_writer_context.py` | `jira_and_ladr` vs `jira_only` for testcase writer |
| `map_requirements_to_diff.py` | Requirement → PR diff mapping; `classify_requirement_type()`; symbol/test evidence |
| `mapping_evidence.py` | Symbol + pytest-name scoring; `rank_matched_files()` for §5 Evidence |
| `_summarize_trace_evidence()` | Compact §5 Evidence display in `coverage_report_helpers.py` (content only) |
| `cache_freshness.py` | Stale mapping detection; used by `--rerun` |
| `execute_pr_tests.py` | Optional local pytest on PR test files (`--execute-tests`; needs `testRepoRoot`) |
| `build_coverage_report.py` | HTML report + `apply_report_ui_enhancements()`; `--rerun` remaps when stale; `--execute-tests` |
| `build_correctly_implemented_list()` | §6 Correctly implemented (in `coverage_report_helpers.py`) |
| `build_implementation_gaps_list()` | §6 Gaps + Open gaps summary count |
| `build_open_gaps_detail()` | Open gaps card note (condensed when ≥5 gaps) |
| `build_assumptions_list()` | §7 Assumptions |
| `build_recommended_actions_list()` | §8 Dev/QA actions (in `coverage_report_helpers.py`) |

**Developed by:** Mayur Gunjal
