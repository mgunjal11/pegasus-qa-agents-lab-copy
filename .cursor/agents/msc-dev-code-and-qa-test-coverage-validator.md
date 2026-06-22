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

**Step 1 — orchestrator** (Jira REST fetch unless `--no-fetch-jira`):

```bash
python scripts/run_coverage_validator.py {KEY} --auto --write --skip-if-fresh --verify-jira
```

Runs preflight → **fetch_jira_story** → confluence → test plan → prefetch → map → build.

**Step 5a (mandatory when test plan missing):** If orchestrator exits **2** or JSON has `"status": "needs_testcase_writer"` (Jira has no QMetry attachment and no `testcases/{KEY}-testcases.xlsx`), **do not** treat the run as complete. Invoke **`@msc-testcase-writer {KEY}`** per [testplan-missing-fallback.md](.cursor/skills/coverage-validator/references/testplan-missing-fallback.md) — in `--auto --write`, skip testcase-writer approval and write Excel immediately — then **re-run Step 1**.

The shell script cannot draft Given/When/Then cases; Step 5a is **agent-only** and was omitted when earlier runs used only `run_coverage_validator.py` without checking exit code 2.

**MCP fallback:** `python scripts/fetch_jira_story.py {KEY} --from-mcp-json /tmp/issue.json` then orchestrator with `--no-fetch-jira`.

## Auto-run (mandatory)

| Rule | Do |
|------|-----|
| Pipeline | Run `run_coverage_validator.py`; on `needs_testcase_writer` → `@msc-testcase-writer` → re-run orchestrator |
| Preflight | Auto on invoke; on auth errors → `preflight_coverage_validator.py {KEY} --verify-jira` |
| GitHub | One prefetch in orchestrator; `--skip-if-fresh` when PR URLs unchanged |
| Never | Stop after `no_testplan` without testcase writer; separate ad-hoc `gh` calls; edit `SUMMARY_METRIC_INFO` for content changes |

**Developed by:** Mayur Gunjal
