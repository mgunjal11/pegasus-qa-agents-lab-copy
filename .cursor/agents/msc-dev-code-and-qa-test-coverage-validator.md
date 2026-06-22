---
name: msc-dev-code-and-qa-test-coverage-validator
description: >-
  MSC Jira-to-PR and QMetry test plan validator for WBD Streaming. One-command pipeline via
  run_coverage_validator.py (auto Jira fetch, preflight, semantic mapping). Dev vs QA scope,
  NFR SIT caps, optional --execute-tests. Invoke via @msc-dev-code-and-qa-test-coverage-validator
  MSC-1234 or /msc-dev-code-and-qa-test-coverage-validator MSC-1234.
model: inherit
---

Follow **`.cursor/skills/coverage-validator/SKILL.md`** for the full workflow (Steps 0–9), report placeholders, and references. **Never** edit tooltip copy when changing report content — [content-vs-tooltips.md](.cursor/skills/coverage-validator/references/content-vs-tooltips.md).

## First run (once)

| Step | Action |
|------|--------|
| **0** | [cli.github.com](https://cli.github.com) → `gh auth login` |
| **1** | Jira REST: `.env.example` → `.env` (`ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, 365-day expiry) |
| **2** | `python scripts/install_coverage_validator_permissions.py` |
| **3** | Optional: `validator.defaults.example.json` → `.coverage-validator.defaults.json` |
| **4** | `/msc-dev-code-and-qa-test-coverage-validator MSC-1234` |

Preflight and Jira fetch run **automatically** inside `run_coverage_validator.py`.

## Slash invoke (`--auto --write`)

**One shell turn** (after optional MCP if REST credentials unavailable):

```bash
python scripts/run_coverage_validator.py {KEY} --auto --write --skip-if-fresh --verify-jira
```

Runs preflight → **fetch_jira_story** → confluence → test plan → prefetch → map (enhanced evidence) → build.

If `no_testplan` → `@msc-testcase-writer {KEY}` per [testplan-missing-fallback.md](.cursor/skills/coverage-validator/references/testplan-missing-fallback.md), then re-run orchestrator.

**MCP fallback:** `python scripts/fetch_jira_story.py {KEY} --from-mcp-json /tmp/issue.json` then orchestrator with `--no-fetch-jira`.

## Auto-run (mandatory)

| Rule | Do |
|------|-----|
| Pipeline | Prefer single `run_coverage_validator.py` call |
| Preflight | Auto on invoke; on auth errors → `preflight_coverage_validator.py {KEY} --verify-jira` |
| GitHub | One prefetch in orchestrator; `--skip-if-fresh` when PR URLs unchanged |
| Never | Separate ad-hoc `gh` calls; edit `SUMMARY_METRIC_INFO` for content changes |

**Developed by:** Mayur Gunjal
