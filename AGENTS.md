# Pegasus QA Agents Lab

Three Cursor agents for MSC QA on [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net).

| Agent | Invoke | Output |
|-------|--------|--------|
| **msc-testcase-writer** | `@msc-testcase-writer MSC-1234` | `testcases/{KEY}-testcases.xlsx` (QMetry FF2.0) |
| **msc-dev-code-and-qa-test-coverage-validator** | `@msc-dev-code-and-qa-test-coverage-validator MSC-1234` | HTML report; §3/§4/§5/§8; LADR trace; QA/Open gaps card detail; §4 dev-covered omits None badge; tooltips v22 |
| **msc-jira-bug** | `@msc-jira-bug` + defect description | MSC Bug in Jira (after explicit approval) |

## Skills (workflow docs — not duplicate slash commands)

| Skill folder | Path |
|--------------|------|
| QMetry test cases | `.cursor/skills/jira-story-testcases/SKILL.md` |
| Coverage validator | `.cursor/skills/coverage-validator/SKILL.md` |
| MSC Bug filing | `.cursor/skills/bug-filing/SKILL.md` |

Full teammate setup: [README.md](README.md)
