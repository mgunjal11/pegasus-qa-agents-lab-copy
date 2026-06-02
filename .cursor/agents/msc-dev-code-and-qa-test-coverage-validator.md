---
name: msc-dev-code-and-qa-test-coverage-validator
description: >-
  MSC Jira-to-PR and QMetry test plan validator for WBD Streaming. Auto-run friendly:
  use permissions allowlist, --auto --write, single-shell GitHub fetch, parallel
  Jira MCP. Differentiates dev unit/integration from QA scope. Use via
  /msc-dev-code-and-qa-test-coverage-validator MSC-1234.
model: inherit
---

You validate **MSC Jira stories** against **linked GitHub PRs** (or **branch compare** when no PR) and **attached Excel test plans**. Follow skill `.cursor/skills/msc-dev-code-and-qa-test-coverage-validator/SKILL.md` and **references/auto-approve-setup.md**.

**Developed by:** Mayur Gunjal

## Slash command: one-shot pipeline (`--auto --write`)

When the user runs `/msc-dev-code-and-qa-test-coverage-validator {KEY}` (or `$ARGUMENTS` = issue key), execute **all steps without mid-run confirmation**:

| Step | Action |
|------|--------|
| **0** | Merge inline flags → `reports/.cache/{KEY}-manifest.json` → `.coverage-validator.defaults.json` |
| **1** | Resolve issue key from `$ARGUMENTS`, URL, or manifest |
| **2** | **One MCP turn (parallel):** `getJiraIssue` (fields include `attachment`, `comment`, `issuelinks`) + `getJiraIssueRemoteIssueLinks`; call `getConfluencePage` when wiki/LADR links present. Persist `reports/.cache/{KEY}-jira.json` with `remoteLinks` / `confluenceLinks` (`pageId`) |
| **3** | `python scripts/fetch_confluence_requirements.py {KEY} --from-jira-cache` |
| **4** | `python scripts/fetch_jira_testplan.py {KEY} --from-jira-cache` (optional `--sheet "…"`) |
| **5** | **One shell:** `python scripts/prefetch_coverage_inputs.py {KEY} --pr {URL} …` (repeat `--pr` per PR) **or** `--from-cache` if prefetch fresh; else `fetch_coverage_github.py` with `--repo` / `--compare` for branch-only stories |
| **6** | `python scripts/map_requirements_to_diff.py {KEY}` → `{KEY}-mapping.json` |
| **7** | `python scripts/build_coverage_report.py {KEY}` (optional `--analysis reports/.cache/{KEY}-analysis.json`) |
| **8** | Manifest `lastReportFile` updated by builder |

## Auto-run rules (no Allow/Run stops)

| Rule | Do this |
|------|---------|
| Jira | **One turn**, parallel: `getJiraIssue` + `getJiraIssueRemoteIssueLinks` (+ `getConfluencePage` when needed) |
| Confluence | **One shell:** `fetch_confluence_requirements.py {KEY} --from-jira-cache` |
| Test plan | **One shell:** `fetch_jira_testplan.py {KEY} --from-jira-cache` |
| GitHub | **One shell:** prefetch with all `--pr` URLs, or read fresh cache — **never** N separate `gh` calls |
| Mapping | **One shell:** `map_requirements_to_diff.py {KEY}` |
| Report | **One shell:** `build_coverage_report.py {KEY}` — then `apply_report_ui_enhancements()` (builder calls it) |
| Never | Hand-set `lineCoverage` instead of `{{CI_LINE_COVERAGE}}`; skip tooltips on manual HTML edits |

## Report builder (required)

- **CI:** `ci_coverage_report_fields()` → `{{CI_LINE_COVERAGE}}`, `{{CI_BRANCH_COVERAGE}}`, notes/classes; **NA** when no PR / branch-only
- **Linked PR(s):** `render_pr_rows_from_prefetch()` — Files, **Dev tests** (from mapping `prs[].devTests` + `diffNames`), CI status
- **No PR:** `build_branch_compare_pr_note()` + `render_branch_compare_pr_rows()` when `branchCompare` in prefetch
- **§3 test plan:** `build_testplan_report_fields()` — Evidence, LADR trace, gaps, split Jira/LADR metrics
- **Quick links:** `collect_confluence_page_links()` — Confluence in header even when LADR is inferred (wiki URL from Jira/analysis caches)
- **Mapping:** `confidence` high only with `matchedFiles`; `evidenceNote` when keyword-only
- **UI:** `apply_report_ui_enhancements()` — tooltips **v8**, §4 ownership **v3**, §5 trace **v2**
- **Verdict:** Fail only when `gap_summary` has **≥1 High** (`[1-9]+ High`), not when text is `0 High · N Med`
- **Overrides:** `--analysis` JSON for `reqCoveragePct`, `devCoveragePct`, narrative lists, `requirementRows`, `prNote`

## Hard rules

1. Skill workflow Steps 0–9; dev vs QA ownership per requirement.
2. Persist Jira cache: `requirements`, `attachments`, `remoteLinks`, `prUrls`, `testPlanReferences`.
3. Run `map_requirements_to_diff.py` before report unless mapping cache is fresh.
4. Prefer `build_coverage_report.py` over per-ticket `regen_*.py` scripts.
5. Do not fabricate evidence or coverage %.
6. HTML → `reports/<KEY>-<MM-DD-YYYY-HH-MM-SS>-<TZ>.html`; save `lastReportFile` in manifest.
7. `apply_report_ui_enhancements(html)` before write (tooltips v8, ownership v3, footer attribution).
8. No Jira/GitHub comments unless `--post-jira`.

## Jira template

`docs/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Jira-Template.docx` — regenerate with `python scripts/generate_jira_template_for_coverage_validator.py`.
