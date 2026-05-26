# Pegasus QA Agents Lab

Three Cursor agents for MSC QA on `wbdstreaming.atlassian.net`.

| Agent | Slash command | Output |
|-------|---------------|--------|
| **msc-testcase-writer** | `@msc-testcase-writer MSC-1234` | QMetry Excel `testcases/{KEY}-testcases.xlsx` |
| **msc-code-coverage-validator** | `/msc-code-coverage-validator MSC-1234` | HTML report `reports/{KEY}-{timestamp}-{TZ}.html` |
| **msc-jira-bug** | `@msc-jira-bug` (describe defect) | MSC Bug in Jira (after approval) |

## Skills

- `.cursor/skills/jira-story-testcases/SKILL.md`
- `.cursor/skills/msc-code-coverage-validator/SKILL.md`
- `.cursor/skills/jira-msc-bug/SKILL.md`

See [README.md](README.md) for setup.
