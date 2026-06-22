---
name: msc-dev-code-and-qa-test-coverage-validator
description: >-
  MSC Jira-to-PR and QMetry test plan validator for WBD Streaming. Auto-preflight on invoke,
  run_coverage_validator.py orchestrates shell pipeline. Dev vs QA scope, NFR SIT caps,
  optional --execute-tests. Invoke via @msc-dev-code-and-qa-test-coverage-validator MSC-1234
  or /msc-dev-code-and-qa-test-coverage-validator MSC-1234.
model: inherit
---

Follow **`.cursor/skills/coverage-validator/SKILL.md`** for the full workflow (Steps 0–9), report placeholders, and references. **Never** edit tooltip copy when changing report content — [content-vs-tooltips.md](.cursor/skills/coverage-validator/references/content-vs-tooltips.md).

## First run (once)

| Step | Action |
|------|--------|
| **0** | Atlassian MCP → `user-atlassian` → `wbdstreaming.atlassian.net` |
| **1** | [cli.github.com](https://cli.github.com) → `gh auth login` |
| **2** | Jira attachment download: `.env.example` → `.env` (`ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, 365-day expiry) — README Configuration |
| **3** | `python scripts/install_coverage_validator_permissions.py` |
| **4** | Optional: `validator.defaults.example.json` → `.coverage-validator.defaults.json` |
| **5** | `/msc-dev-code-and-qa-test-coverage-validator MSC-1234` |

Preflight runs **automatically** on every invoke (via `run_coverage_validator.py` or explicit preflight on auth failure).

## Slash invoke (`--auto --write`)

1. **Jira MCP** — one parallel turn (story + remote links + attachment metadata).
2. **Shell pipeline** (one turn when possible):

```bash
python scripts/run_coverage_validator.py {KEY} --auto --write --skip-if-fresh --verify-jira
```

Runs preflight → confluence → test plan → prefetch → map (`--semantic-boost`) → build. If `no_testplan` → `@msc-testcase-writer {KEY}` per [testplan-missing-fallback.md](.cursor/skills/coverage-validator/references/testplan-missing-fallback.md), then re-run orchestrator.

## Auto-run (mandatory)

| Rule | Do |
|------|-----|
| Preflight | Auto on invoke; on `gh`/Jira auth errors, re-run `preflight_coverage_validator.py {KEY} --verify-jira` |
| Jira | One MCP turn, parallel fetches |
| GitHub | One prefetch shell; `--skip-if-fresh` when PR URLs unchanged |
| Shells | Prefer `run_coverage_validator.py` over ad-hoc map/build; builder calls `apply_report_ui_enhancements()` |
| Never | Separate `gh` calls; edit `SUMMARY_METRIC_INFO` for content changes |

**Developed by:** Mayur Gunjal
