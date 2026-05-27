# TestCursor — agent instructions

## Purpose

Generate **QMetry-format test cases** as downloadable Excel from Jira stories on `wbdstreaming.atlassian.net`.

## QMetry format (matches QMetry FF2.0.xlsx)

**Sheet name:** `QMetry Template`

**11 columns:**

```
Summary | Automatable | Automation Status | Priority | Folders | Step Summary | Test Type | Status | Regression Test (Y/N) | Story | TestData Dependent
```

**3 rows per test case** — Given/When/Then in **Step Summary** only. Excel merges all metadata columns vertically (including **Status**); Step Summary is not merged.

**Summary:** `{ISSUE-KEY}_{descriptive scenario and verification}`

## Output

```bash
python scripts/generate_qmetry_excel.py testcases/<KEY>-testcases.tsv
```

Primary file: `testcases/<KEY>-testcases.xlsx`

Subagents:

| Agent | Purpose |
|-------|---------|
| **msc-testcase-writer** | QMetry test cases from Jira stories |
| **msc-code-coverage-validator** | `/msc-code-coverage-validator KEY` — validates Jira AC + attached QMetry test plan vs linked PR; auto-run with permissions allowlist |

Skill: `.cursor/skills/msc-code-coverage-validator/SKILL.md`

Auto-approve: `.cursor/skills/msc-code-coverage-validator/references/auto-approve-setup.md`

Install once: `python scripts/install_coverage_validator_permissions.py`

Report output: `reports/<ISSUE-KEY>-<MM-DD-YYYY-HH-MM-SS>-<TZ>.html` (local timezone — IST, EST, etc.)
