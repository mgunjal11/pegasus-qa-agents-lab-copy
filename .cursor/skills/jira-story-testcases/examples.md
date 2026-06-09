# Example: QMetry FF2.0 format

Reference: `QMetry FF2.0.xlsx` — sheet **QMetry Template**, 11 columns, merged cells.

## TSV source

```
Summary	Automatable	Automation Status	Priority	Folders	Step Summary	Test Type	Status	Regression Test (Y/N)	Story	TestData Dependent
MSC-202222_Verify dub card validation failure marks component FAIL only	Yes	Not Started	P0		Given: Package in Acquire 2.0 with failing dub card	End to End		Yes	MSC-202222	Yes
When: Validation runs on the failing dub card
Then: Only dub card component is FAIL; package is not terminally failed
```

When/Then rows: only **Step Summary** column populated (generator auto-fixes column placement).

## Generate Excel

```bash
python scripts/write_testcase_excel.py MSC-202222
```

Output: merged metadata cells (including Status) + Given/When/Then in column F, sheet name `QMetry Template`.
