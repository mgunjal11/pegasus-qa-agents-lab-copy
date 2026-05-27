# Local test plans

Place QMetry / Domino Excel files here when a Jira story **references** a test plan in comments or SharePoint but does not attach the file (or you prefer a local copy).

## Example

Jira comment: *“Refer Inc as full sheet for Test plan and evidence”* → `Domino Test Plan.xlsx`, sheet **Inc as full**.

1. Download or copy the workbook to this folder:
   ```
   testplans/Domino Test Plan.xlsx
   ```
2. Optionally set in `.coverage-validator.defaults.json` (repo root, gitignored):
   ```json
   {
     "testPlanPath": "testplans/Domino Test Plan.xlsx",
     "testPlanSheet": "Inc as full"
   }
   ```
3. Re-run `/msc-code-coverage-validator {KEY}` or:
   ```bash
   python scripts/fetch_jira_testplan.py {KEY} --attachment testplans/Domino\ Test\ Plan.xlsx --sheet "Inc as full"
   ```

## Jira attachment (preferred when available)

If the Excel is attached to the issue, set `.env` (see `.env.example`) so `fetch_jira_testplan.py` can download it automatically — no manual copy needed.
