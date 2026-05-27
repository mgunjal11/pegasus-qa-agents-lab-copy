# Pegasus QA Agents Lab

Three Cursor agents for MSC QA on [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net).

| Agent | Invoke | Output |
|-------|--------|--------|
| **msc-testcase-writer** | `@msc-testcase-writer MSC-1234` | `testcases/{KEY}-testcases.xlsx` (QMetry FF2.0) |
| **msc-code-coverage-validator** | `/msc-code-coverage-validator MSC-1234` | `reports/{KEY}-{timestamp}-{TZ}.html` (8-card summary, dev vs QA) |
| **msc-jira-bug** | `@msc-jira-bug` + defect description | MSC Bug in Jira (after explicit approval) |

## Skills

| Skill | Path |
|-------|------|
| QMetry test cases from Jira | `.cursor/skills/jira-story-testcases/SKILL.md` |
| Coverage vs PR + test plan | `.cursor/skills/msc-code-coverage-validator/SKILL.md` |
| MSC Bug filing | `.cursor/skills/jira-msc-bug/SKILL.md` |

## Coverage validator extras (vs jira-bug)

- `gh` CLI + `.coverage-validator.defaults.json` (optional `repo`, timezone)
- `.env` — `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN` for Jira test plan attachments
- `testplans/` — local Excel when Jira references SharePoint sheets
- Auto-approve: `python scripts/install_coverage_validator_permissions.py` — see [auto-approve-setup.md](.cursor/skills/msc-code-coverage-validator/references/auto-approve-setup.md)

Full teammate setup: [README.md](README.md)
