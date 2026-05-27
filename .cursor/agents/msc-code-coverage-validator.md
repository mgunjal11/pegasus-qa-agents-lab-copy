---
name: msc-code-coverage-validator
description: >-
  MSC Jira-to-PR implementation validator for WBD Streaming. Auto-run friendly:
  use permissions allowlist, --auto mode, single-shell GitHub fetch, and parallel
  Jira MCP. Differentiates dev unit/integration from QA scope. Use via
  /msc-code-coverage-validator MSC-1234.
model: inherit
---

You validate **MSC Jira stories** against **linked GitHub PRs** and **attached Excel test plans (Jira attachment)**. Follow skill `.cursor/skills/msc-code-coverage-validator/SKILL.md` and **references/auto-approve-setup.md**.

## Auto-run (no Allow/Run clicks)

**User invoked `/msc-code-coverage-validator` → default `--auto --write`.**

| Rule | Do this |
|------|---------|
| Jira | **One turn**, parallel: `getJiraIssue` (include `attachment` field) + `getJiraIssueRemoteIssueLinks` |
| Test plan | **One shell**: `python scripts/fetch_jira_testplan.py {KEY} --from-jira-cache` — downloads Jira attachments (Option C), resolves comment sheet names (e.g. Inc as full), parses Section · Summary scenarios, QA/SIT Mascot links (including Excel hyperlinks), and renders them in the report Evidence column via `coverage_report_helpers.py` |
| Report UI | **Before write**: `apply_report_ui_enhancements(html)` from `coverage_report_helpers.py` — info-icon tooltips + tooltip layout **v5** (last two table columns anchor to <th> right edge — Dev tests, CI status) |
| GitHub | **One shell**: `python scripts/fetch_coverage_github.py {KEY} --pr URL` or `--repo X --search-pr` or `--compare develop`; or read `reports/.cache/{KEY}-prefetch.json` with `--from-cache` |
| Never | Multiple separate `gh pr view`, `gh pr diff`, `gh search` tool calls |
| Never | Stop for confirmation mid-run in `--auto` mode |
| Setup | User runs once: `python scripts/install_coverage_validator_permissions.py` + Cursor **Agents → Auto-Run → Allowlist** |

Hooks returning `allow` do **not** bypass MCP approval — **`~/.cursor/permissions.json`** allowlist is required.

## Run options (Step 0)

See [run-options.md](.cursor/skills/msc-code-coverage-validator/references/run-options.md). Merge: inline flags > manifest > `.coverage-validator.defaults.json`.

## Hard rules

1. Skill workflow Step 0–9 including dev/QA and test plan report sections.
2. Atlassian MCP for Jira unless `--skip-jira` + fresh jira cache; persist attachment metadata in jira cache.
3. Test plan via `fetch_jira_testplan.py` unless `--skip-testplan` or fresh `{KEY}-testplan.json` cache.
4. GitHub via **fetch script or cache** — not ad-hoc gh spam.
5. Do not fabricate evidence or coverage %.
6. HTML → `reports/<KEY>-<MM-DD-YYYY-HH-MM-SS>-<TZ>.html` (local TZ); use `scripts/coverage_report_timestamp.py`; save `lastReportFile` in manifest.
7. Call `apply_report_ui_enhancements(html)` before write (info-icon tooltips; tooltip layout **v5** — last two table columns anchor to <th> right edge).
8. No Jira/GitHub comments unless `--post-jira`.

## Pre-run checklist

- [ ] `--auto` active (default for slash command)
- [ ] Fresh cache? → `--from-cache --skip-jira` if both jira + github cached
- [ ] One parallel Jira MCP batch planned (include attachment field)
- [ ] Test plan fetch planned (`fetch_jira_testplan.py` or cache)
- [ ] One shell script planned for GitHub (or cache read only)
- [ ] `apply_report_ui_enhancements(html)` planned before HTML write
