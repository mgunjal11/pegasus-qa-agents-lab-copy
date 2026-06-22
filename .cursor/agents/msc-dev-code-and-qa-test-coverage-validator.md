---
name: msc-dev-code-and-qa-test-coverage-validator
description: >-
  MSC Jira-to-PR and QMetry test plan validator for WBD Streaming. Run preflight once,
  then --auto --write pipeline. Dev vs QA scope, NFR SIT caps, optional --execute-tests.
  Invoke via @msc-dev-code-and-qa-test-coverage-validator MSC-1234 or
  /msc-dev-code-and-qa-test-coverage-validator MSC-1234.
model: inherit
---

**Pipeline:** preflight (once) → Jira/Confluence → test plan → GitHub prefetch (`--skip-if-fresh`) → map → build report. Full workflow: `.cursor/skills/coverage-validator/SKILL.md`. **Never** edit tooltip copy when changing report content.

## First run (5 min)

| Step | Action |
|------|--------|
| **0** | **Preflight** — `python scripts/preflight_coverage_validator.py MSC-1234 --verify-jira` (fixes missing `gh`, `.env`, allowlist before first report) |
| **1** | **Atlassian MCP** — Cursor Settings → MCP → `user-atlassian` → sign in for `wbdstreaming.atlassian.net` |
| **2** | **GitHub CLI** — install [cli.github.com](https://cli.github.com) → `gh auth login` |
| **3** | **Jira REST `.env`** — when test plan is a **Jira attachment**: copy `.env.example` → `.env`; set `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, token expiry (365 days). See README Configuration |
| **4** | **Allowlist** — `python scripts/install_coverage_validator_permissions.py` |
| **5** | **Defaults** (optional) — copy `validator.defaults.example.json` → `.coverage-validator.defaults.json`; set `testPlanPath`, `timezone`, `verdictMode`, optional `testRepoRoot` |
| **6** | **Run** — `/msc-dev-code-and-qa-test-coverage-validator MSC-1234` |

Optional: `testRepoRoot` + `build_coverage_report.py {KEY} --execute-tests`. NFR SIT AC stays capped at **medium**.

## Slash command pipeline (`--auto --write`)

| Step | Action |
|------|--------|
| **0** | Merge flags → manifest → `.coverage-validator.defaults.json` |
| **1** | Resolve `{KEY}` |
| **2** | **Parallel MCP:** `getJiraIssue` + `getJiraIssueRemoteIssueLinks` (+ Confluence when linked) → `{KEY}-jira.json` |
| **3** | `fetch_confluence_requirements.py {KEY} --from-jira-cache` |
| **4** | `fetch_jira_testplan.py {KEY} --from-jira-cache` |
| **4b** | `no_testplan` → `@msc-testcase-writer {KEY}` + `write_testcase_excel.py` + re-fetch ([testplan-missing-fallback.md](.cursor/skills/coverage-validator/references/testplan-missing-fallback.md)) |
| **5** | `prefetch_coverage_inputs.py {KEY} --pr URL … --skip-if-fresh` (one shell; all PRs) |
| **6** | `map_requirements_to_diff.py {KEY}` |
| **7** | `build_coverage_report.py {KEY}` [`--rerun`] [`--execute-tests`] — uses `verdictMode` from manifest/defaults |
| **8** | Manifest `lastReportFile` updated |

## Auto-run rules

| Rule | Do this |
|------|---------|
| Preflight | Run step 0 on first setup or after auth errors |
| Jira | One MCP turn, parallel fetches |
| GitHub | One prefetch shell; `--skip-if-fresh` when cache matches PR URLs |
| Mapping / report | One shell each; `apply_report_ui_enhancements()` in builder |
| Never | Edit `SUMMARY_METRIC_INFO` tooltip strings for content changes ([content-vs-tooltips.md](.cursor/skills/coverage-validator/references/content-vs-tooltips.md)) |

## Report content (builders only — tooltips unchanged)

§3 honest test plan note · §4 Dev vs QA · §5 FR/NFR + expandable Evidence · §6 review · §7 assumptions (max 3) · §8 Dev/QA actions · NFR SIT capped at medium · `verdictMode`: **pragmatic** (default) or **strict** (Pass only at 100% + zero Med gaps)

## Key scripts

| Script | Role |
|--------|------|
| `preflight_coverage_validator.py` | One-shot setup validation |
| `prefetch_coverage_inputs.py` | Batch gh fetch; `--skip-if-fresh` |
| `map_requirements_to_diff.py` | Requirement → PR mapping |
| `build_coverage_report.py` | HTML report + UI enhancements |
| `coverage_validator_config.py` | Defaults + `verdictMode` |

**Developed by:** Mayur Gunjal
