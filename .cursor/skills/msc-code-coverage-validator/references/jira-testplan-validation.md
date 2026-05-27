# Jira test plan validation

Validate **QMetry or Domino evidence test plans** linked from Jira (attachment, comment, or SharePoint reference) alongside PR code and dev tests.

## When to run

Always attempt test plan validation in **`--auto`** and **interactive** modes unless:

- User passes **`--skip-testplan`**
- Manifest/defaults set `"validateTestPlan": false`

## Detection (priority order)

1. **Jira attachments** — `.xlsx` / `.tsv` on the issue (`attachment` field).
2. **Jira comment / description references** — SharePoint Excel links and sheet names (e.g. *Refer **Inc as full** sheet for Test plan and evidence* → `Domino Test Plan.xlsx`).
3. **Workspace local file** — `testplans/{filename}`, `testplans/{KEY}/`, or `testPlanPath` in manifest/defaults.
4. **QMetry fallback** — `testcases/{KEY}-testcases.xlsx` or `.tsv`.

The agent must persist in `reports/.cache/{KEY}-jira.json`:

- `attachments` — Jira attachment metadata
- **`comments`** or `fields.comment` — so `fetch_jira_testplan.py` can extract SharePoint + sheet references
- `requirements` — R1…Rn for mapping

`fetch_jira_testplan.py` auto-writes **`testPlanReferences`** back into the jira cache.

### SharePoint / comment pattern (MSC Domino)

| Jira text | Parsed as |
|-----------|-----------|
| Link to `Domino Test Plan.xlsx` on SharePoint | `filename: Domino Test Plan.xlsx`, `type: sharepoint` |
| *Refer Inc as full sheet* | `sheet: Inc as full` |
| *Test plan and evidence* link text | evidence sheet (not QMetry Template) |

**Local setup** (SharePoint files are not downloaded automatically):

```bash
# Copy Excel from SharePoint once:
testplans/Domino Test Plan.xlsx
```

### Option C — Jira attachment (automated download)

Attach the test plan Excel **on the Jira issue** (not only a SharePoint link in a comment). Configure REST credentials:

```bash
cp .env.example .env   # ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN
python scripts/verify_jira_credentials.py MSC-205625
python scripts/upload_jira_testplan.py MSC-205625 --file "path/to/Domino Test Plan.xlsx"  # optional
python scripts/fetch_jira_testplan.py MSC-205625 --from-jira-cache --sheet "Inc as full"
```

Priority: Jira attachment download (with credentials) → local `testplans/` → SharePoint comment reference.

```json
// .coverage-validator.defaults.json or manifest
{
  "testPlanPath": "testplans/Domino Test Plan.xlsx",
  "testPlanSheet": "Inc as full"
}
```

## Fetch (one shell turn)

```bash
python scripts/fetch_jira_testplan.py {ISSUE-KEY} --from-jira-cache
python scripts/fetch_jira_testplan.py {ISSUE-KEY} --sheet "Inc as full"
```

Cache: `reports/.cache/{KEY}-testplan.json`

### Cache status values

| status | Meaning | Report |
|--------|---------|--------|
| `ok` | Test cases parsed | Show coverage % and rows |
| `referenced_not_local` | Jira comment references Excel + sheet; file not in `testplans/` | Show reference details + setup hint; **not** "no attachment" |
| `no_testplan` | No attachment and no comment reference found | `NA` |
| `parse_failed` | File found but sheet/parse error | Warn with parse errors |

## Sheet formats

### QMetry Template

Sheet **QMetry Template**, 11 columns, 3 rows per test case (Given/When/Then in **Step Summary**).

### Domino evidence sheets (e.g. Inc as full)

Flexible columns: Test Scenario / Summary, Preconditions, Steps, Expected Result, Jira/Story, Status.

Rows filtered to the current issue key when a Story/Jira column or row text contains `MSC-xxxxx`.

## Mapping test cases → requirements

For each `TC{n}` map to Jira requirements `R1`…`Rn`:

1. **Explicit ID** — Summary or steps mention `R1`, `R2`, etc.
2. **Keyword overlap** — significant tokens from requirement text appear in Summary/steps.
3. **Story column** — test case Story = issue key.
4. **Gap** — no mapped requirement → flag as **Unmapped test case**.

## Cross-check: test plan vs PR

For each mapped pair (`R{n}` ↔ `TC{x}`):

| Dimension | Check |
|-----------|-------|
| **Code** | PR implements what the test case Then clause verifies |
| **Dev tests** | PR unit/integration tests cover logic the test case exercises |
| **QA scope** | Test plan Test Type aligns with QA handoff |
| **Contradictions** | Test case expects behavior not present in PR diff |

## Metrics

**Test plan acceptance criteria coverage %** — use **`NA`** only when `status` is `no_testplan`. When `referenced_not_local`, show reference in note and use **`Pending`** or partial detail until local file is added.

**Test plan completeness** — e.g. `5 test cases · 5/5 full Given When Then · 3/4 acceptance criteria covered` or `Referenced: Domino Test Plan.xlsx · Inc as full · 0 parsed (local file missing)`.

**Domino attachment fields parsed:** `section`, `summary` (high-level scenario), Given/When/Then steps, `mascot_links` (QA/SIT Mascot columns), Story. Report note from `testPlanSummaryNote`: `Downloaded {file} from Jira attachment comment sheet {comment sheet} → Excel tab {tab} · N scenarios for {KEY}.`

## Report placeholders

| Placeholder | Content |
|-------------|---------|
| `{{TESTPLAN_COVERAGE_PCT}}` | e.g. `100.0%`, `Pending`, or `NA` |
| `{{TESTPLAN_COVERAGE_DETAIL}}` | completeness or reference summary |
| `{{TESTPLAN_NOTE}}` | Empty when parsed; otherwise reference + local setup hint (not generic "no attachment") |
| `{{TESTPLAN_ROWS}}` | TC rows or reference summary row |
| `{{TESTPLAN_GAPS_LIST}}` | Uncovered acceptance criteria, missing local file, misalignments |

## Verdict impact

- **Fail** — referenced test plan with zero AC coverage after local file provided, or critical test–code contradictions
- **Pass with gaps** — `referenced_not_local`, partial coverage, or SIT-only scenarios
- **Pass** — test plan covers AC and aligns with PR
