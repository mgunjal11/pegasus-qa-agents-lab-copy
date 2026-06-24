# Pegasus QA Agents Lab

Three Cursor agents for MSC QA on [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net).

| Agent | Invoke | Output |
|-------|--------|--------|
| **Spec2Test** | `@Spec2Test MSC-1234` | `testcases/{KEY}-testcases.xlsx` (QMetry FF2.0) |
| **Req2Release** | `@Req2Release MSC-1234` | HTML report; PR-gated §5; attached vs effective test plan %; exit **2** → Spec2Test |
| **msc-jira-bug** | `@msc-jira-bug` + defect description | MSC Bug in Jira (after explicit approval) |

## Skills (workflow docs — not duplicate slash commands)

| Skill folder | Path |
|--------------|------|
| QMetry test cases | `.cursor/skills/jira-story-testcases/SKILL.md` |
| Coverage validator | `.cursor/skills/coverage-validator/SKILL.md` |
| MSC Bug filing | `.cursor/skills/bug-filing/SKILL.md` |

Full teammate setup: [README.md](README.md)
