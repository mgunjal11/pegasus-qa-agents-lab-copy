# Coverage validation report template

**Primary output:** HTML — use [report-template.html](report-template.html).  
This markdown file is an optional reference for structure only.

```markdown
## Coverage validation: {ISSUE-KEY} — {story title}

**Jira**: [{ISSUE-KEY}](https://wbdstreaming.atlassian.net/browse/{ISSUE-KEY})  
**Status**: {issue status} | **Type**: {issuetype}

### Linked PR(s)

| PR | Author | State | CI |
|----|--------|-------|-----|
| [{org}/{repo}#{number}]({pr_url}) | @{author} | {open|merged|closed} | {passed|failed|pending} |

### Coverage summary

| Metric | Value | Notes |
|--------|-------|-------|
| Dev code coverage | **{pct}%** ({implemented}/{total} scored) | Jira AC → production code |
| Dev unit/integration test coverage | **{pct}%** ({covered}/{dev-owned} dev-owned) | Unit & integration tests in PR |
| QA scope remaining | **{count} items** | E2E, manual, regression, or partial dev gaps |
| CI line coverage | **{pct}%** or **NA** | Source or `No PR for {KEY}; develop branch only` |
| CI branch coverage | **{pct}%** or **NA** | Same note when no PR |

**Verdict**: {Pass | Pass with gaps | Fail} — {one-line rationale}

### Dev vs QA test ownership

#### Covered by dev tests (unit / integration)
- **R{n}** {requirement summary} — {Unit|Integration}: `{test file}::{test name}`

#### QA handoff
- **R{n}** {requirement summary} — **{Spot-check|E2E|Manual|Regression}**: {why QA must verify}

### Requirements traceability

| ID | Requirement (from Jira) | Code | Dev tests | Owner | QA scope | Evidence |
|----|-------------------------|------|-----------|-------|----------|----------|
| R1 | {AC text} | Implemented / Partial / Missing / N/A | Covered / Partial / Missing / N/A + tier | Dev / Shared / QA | None / Spot-check / E2E / Manual / Regression | `{file}:{symbol}` or test name |

### Implementation review

#### Correctly implemented
- {requirement}: {brief note with file reference}

#### Gaps and concerns
- 🔴 **Critical**: {missing AC or incorrect behavior}
- 🟡 **High**: {partial implementation or missing dev tests}
- 🟢 **Medium**: {style, edge case, doc gap}

### Assumptions and open questions
- {assumption or TBD from thin Jira description}

### Recommended actions
1. **Dev**: {unit/integration test to add}
2. **QA**: {E2E or manual scenario}
```

## Verdict rules

| Verdict | When |
|---------|------|
| **Pass** | Dev code coverage ≥ 95%, dev unit/integration test coverage ≥ 80% for dev-owned AC, no critical gaps, CI green (if run) |
| **Pass with gaps** | Dev code coverage ≥ 70% or minor dev test / QA handoff gaps without critical missing AC |
| **Fail** | Any critical AC missing, requirement coverage < 70%, or implementation contradicts Jira |

Adjust thresholds if the user specifies stricter gates for their team.

## Dev vs QA classification

See [references/dev-qa-test-scope.md](references/dev-qa-test-scope.md) for full rules.
