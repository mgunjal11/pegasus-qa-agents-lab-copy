# QMetry test case template

Matches the import layout in `QMetry FF2.0.xlsx` (sheet: **QMetry Template**).

## Columns (exact order — 11 columns)

```
Summary	Automatable	Automation Status	Priority	Folders	Step Summary	Test Type	Status	Regression Test (Y/N)	Story	TestData Dependent
```

| # | Column | Row 1 (Given) | Rows 2–3 (When/Then) |
|---|--------|---------------|----------------------|
| 1 | Summary | `{STORY}_{descriptive test title}` | Empty (merged in Excel) |
| 2 | Automatable | `Yes` | Empty |
| 3 | Automation Status | `Not Started` | Empty |
| 4 | Priority | `P0` / `P1` / `P2` / `P3` | Empty |
| 5 | Folders | Optional folder path | Empty |
| 6 | Step Summary | `Given:…` | `When:…` / `Then:…` |
| 7 | Test Type | `End to End` | Empty |
| 8 | Status | Leave blank for new cases (merged in Excel) | Empty |
| 9 | Regression Test (Y/N) | `Yes` | Empty |
| 10 | Story | Jira issue key (e.g. `MSC-202222`) | Empty |
| 11 | TestData Dependent | `Yes` or `No` | Empty |

## Row structure (3 rows per test case)

Each test case = **3 rows**. In Excel, all columns except **Step Summary** are **vertically merged** across the 3 rows (including **Status**).

```
Row 1:  [Summary + metadata] | Given: <preconditions>
Row 2:  [empty]             | When: <action>
Row 3:  [empty]             | Then: <expected result>
```

### Summary naming

Use: `{ISSUE-KEY}_{concise scenario and verification}`

Example: `MSC-191511_Trigger FF-2.0 workflow of Acquired job with OPL audio 2.0 and SDR video and verify whether the workflow gets triggered for Domino - TMC`

### Step Summary rules

- Prefix: `Given:`, `When:`, `Then:` (colon required; space after colon optional per sample).
- **Given** — preconditions, test data, environment.
- **When** — action under test.
- **Then** — observable expected outcome.

---

## Defaults

| Field | Default |
|-------|---------|
| Automatable | Yes |
| Automation Status | Not Started |
| Priority | P0 (happy path), P1 (negative/edge) |
| Test Type | End to End |
| Status | Blank |
| Regression Test (Y/N) | Yes |
| TestData Dependent | Yes when data required; No otherwise |

---

## File output (after approval)

| File | Purpose |
|------|---------|
| `testcases/<ISSUE-KEY>-testcases.xlsx` | **Primary** — QMetry import (merged cells, sheet name `QMetry Template`) |
| `reports/.cache/<ISSUE-KEY>-testcases-source.tsv` | Internal source (not in `testcases/`) |
| `testcases/<ISSUE-KEY>-testcases.xlsx` | Deliverable |

```bash
pip install -r requirements.txt
python scripts/write_testcase_excel.py <ISSUE-KEY>
```

---

## TSV example

```
Summary	Automatable	Automation Status	Priority	Folders	Step Summary	Test Type	Status	Regression Test (Y/N)	Story	TestData Dependent
MSC-202222_Verify dub card validation failure marks component FAIL only	Yes	Not Started	P0		Given: Package in Acquire 2.0 with dub card that fails validation	End to End		Yes	MSC-202222	Yes
										When: Validation runs on the failing dub card
										Then: Only the dub card component is FAIL; package is not terminally failed
```
