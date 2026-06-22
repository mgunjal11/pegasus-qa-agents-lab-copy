---
name: msc-dev-code-and-qa-test-coverage-validator
description: >-
  MSC Jira-to-PR and QMetry test plan validator for WBD Streaming. Run preflight once,
  then --auto --write pipeline. Dev vs QA scope, NFR SIT caps, optional --execute-tests.
  Invoke via @msc-dev-code-and-qa-test-coverage-validator MSC-1234 or
  /msc-dev-code-and-qa-test-coverage-validator MSC-1234.
model: inherit
---

Follow **`.cursor/skills/coverage-validator/SKILL.md`** for the full workflow (Steps 0–9), report placeholders, and references. **Never** edit tooltip copy when changing report content — [content-vs-tooltips.md](.cursor/skills/coverage-validator/references/content-vs-tooltips.md).

## First run (once)

| Step | Action |
|------|--------|
| **0** | `python scripts/preflight_coverage_validator.py MSC-1234 --verify-jira` |
| **1** | Atlassian MCP → `user-atlassian` → `wbdstreaming.atlassian.net` |
| **2** | [cli.github.com](https://cli.github.com) → `gh auth login` |
| **3** | Jira attachment download: `.env.example` → `.env` (`ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, 365-day expiry) — README Configuration |
| **4** | `python scripts/install_coverage_validator_permissions.py` |
| **5** | Optional: `validator.defaults.example.json` → `.coverage-validator.defaults.json` |
| **6** | `/msc-dev-code-and-qa-test-coverage-validator MSC-1234` |

## Slash invoke (`--auto --write`)

Execute SKILL **Steps 0–9** end-to-end without mid-run confirmation. Highlights: parallel Jira MCP → Confluence + test plan shells → `prefetch_coverage_inputs.py --skip-if-fresh` → `map_requirements_to_diff.py` → `build_coverage_report.py` (`verdictMode` from defaults/manifest). If `no_testplan` → `@msc-testcase-writer {KEY}` per [testplan-missing-fallback.md](.cursor/skills/coverage-validator/references/testplan-missing-fallback.md).

## Auto-run (mandatory)

| Rule | Do |
|------|-----|
| Jira | One MCP turn, parallel fetches |
| GitHub | One prefetch shell; `--skip-if-fresh` when PR URLs unchanged |
| Shells | One turn each for map + build; builder calls `apply_report_ui_enhancements()` |
| Never | Separate `gh` calls; edit `SUMMARY_METRIC_INFO` for content changes |

**Developed by:** Mayur Gunjal
