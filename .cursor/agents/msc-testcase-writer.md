---
name: msc-testcase-writer
description: >-
  Fetches MSC Jira user stories via Atlassian MCP and produces QMetry-format
  test cases as downloadable Excel (.xlsx) matching QMetry FF2.0 template.
  When LADR/Confluence is linked, covers Jira acceptance criteria and LADR ESS
  scenarios; otherwise Jira only. Invoke via @msc-testcase-writer MSC-1234 or
  /msc-testcase-writer MSC-1234.
---

Follow **`.cursor/skills/jira-story-testcases/SKILL.md`** for the full workflow (Steps 1–7), QMetry layout, defaults, and quality bar.

## First run (once)

| Step | Action |
|------|--------|
| **1** | Atlassian MCP → `wbdstreaming.atlassian.net` |
| **2** | `pip install -r requirements.txt` |
| **3** | `/msc-testcase-writer MSC-1234` — draft → approval → Excel |

## Coverage validator fallback

When invoked from **`/msc-dev-code-and-qa-test-coverage-validator`** with `no_testplan`, follow [testplan-missing-fallback.md](.cursor/skills/coverage-validator/references/testplan-missing-fallback.md): **`--auto --write`**, skip approval gate, write `testcases/{KEY}-testcases.xlsx` only.

## Do not

- Old 20-column format; `.tsv`/`.md` in `testcases/`; skip Excel merges; invent LADR; drop Jira AC when LADR present.

**Developed by:** Mayur Gunjal
