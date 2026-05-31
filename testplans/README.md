# Local test plans

Place QMetry / Domino Excel files here when a Jira story **references** a test plan in comments or SharePoint but does not attach the file (or you prefer a local copy).

## Example

Jira comment: *"Refer Inc as full sheet for Test plan and evidence"* → `Domino Test Plan.xlsx`, sheet **Inc as full**.

1. Copy the workbook to `testplans/Domino Test Plan.xlsx`
2. Optionally set `testPlanPath` / `testPlanSheet` in `.coverage-validator.defaults.json`
3. Re-run `/msc-dev-code-and-qa-test-coverage-validator {KEY}`

## Jira attachment

If the Excel is on the issue, set `.env` from `.env.example` so `fetch_jira_testplan.py` can download it automatically.
