# Pegasus QA Agents Lab

Three Cursor agents for MSC QA on [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net).

| Agent | Invoke | Output |
|-------|--------|--------|
| **msc-testcase-writer** | `@msc-testcase-writer MSC-1234` | `testcases/{KEY}-testcases.xlsx` (QMetry FF2.0) |
| **msc-dev-code-and-qa-test-coverage-validator** | `/msc-dev-code-and-qa-test-coverage-validator MSC-1234` | `build_coverage_report.py`; QA scope None when dev tests cover AC (no redundant QA execute); Confluence quick links; CI + Dev tests; tooltips v8 / §4 v3 |
| **msc-jira-bug** | `@msc-jira-bug` + defect description | MSC Bug in Jira (after explicit approval) |

## Skills

| Skill | Path |
|-------|------|
| QMetry test cases from Jira | `.cursor/skills/jira-story-testcases/SKILL.md` |
| Coverage vs PR + test plan | `.cursor/skills/msc-dev-code-and-qa-test-coverage-validator/SKILL.md` |
| MSC Bug filing | `.cursor/skills/jira-msc-bug/SKILL.md` |

Full teammate setup: [README.md](README.md)
