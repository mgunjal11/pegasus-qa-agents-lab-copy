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
4. **QMetry fallback** — `testcases/{KEY}-testcases.xlsx` only.

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
| `no_testplan` | No attachment and no comment reference found | **`NA`** until generated — see [testplan-missing-fallback.md](testplan-missing-fallback.md) |
| `parse_failed` | File found but sheet/parse error | Warn with parse errors |

## No Jira attachment — generate test cases

When `status` is **`no_testplan`** (not `referenced_not_local`):

1. Coverage validator invokes **`/Spec2Test {KEY}`** when `generateTestPlanIfMissing` is true (default in `--auto --write`).
2. Writes `reports/.cache/{KEY}-testcases-source.tsv` + `testcases/{KEY}-testcases.xlsx` via `write_testcase_excel.py`.
3. Re-runs `fetch_jira_testplan.py` — script priority **4** loads `testcases/{KEY}-testcases.xlsx`.
4. Report §3 note should state plan was **generated locally** (not attached on Jira). Does not change report tooltip markup.

Opt out: manifest `skipTestcaseGeneration: true` or `--skip-testplan`.

## Sheet formats

### QMetry Template

Sheet **QMetry Template**, 11 columns, 3 rows per test case (Given/When/Then in **Step Summary**).

### Domino evidence sheets (e.g. Inc as full)

Flexible columns: Test Scenario / Summary, Preconditions, Steps, Expected Result, Jira/Story, Status.

Rows filtered to the current issue key when a Story/Jira column or row text contains `MSC-xxxxx`.

## Mapping test cases → requirements

For each `TC{n}` map to Jira requirements `R1`…`Rn` **and** LADR ESS scenarios `L1`…`Ln` when Confluence/LADR is referenced:

1. **LADR ESS task + status** — match milestone names (`demandAcknowledgment`, `orderStatus`, …) and status (Completed, Pending, Failure, …) in Summary/Then steps → `L*`
2. **Jira AC inference** — ESS scenarios imply R1 (V2 ESS), R2 (status propagation), R3 (failure / 8000 / 9000)
3. **Explicit ID** — Summary or steps mention `R1`, `L3`, etc.
4. **Keyword overlap** — significant tokens from Jira requirement text appear in Summary/steps.
5. **Gap** — no mapped requirement → flag as **Unmapped test case**.

See [confluence-ladr-requirements.md](confluence-ladr-requirements.md) for fetch and cache paths.

## Cross-check: test plan vs PR

For each mapped pair (`R{n}` ↔ `TC{x}`):

| Dimension | Check |
|-----------|-------|
| **Code** | PR implements what the test case Then clause verifies |
| **Dev tests** | PR unit/integration tests cover logic the test case exercises |
| **QA scope** | Test plan Test Type aligns with QA handoff |
| **Contradictions** | Test case expects behavior not present in PR diff |

## Metrics

**Test plan acceptance criteria coverage %** — scores **Jira AC + LADR scenarios** when LADR is present. Use **`NA`** only when `status` is `no_testplan`. When `referenced_not_local`, show reference in note and use **`Pending`** or partial detail until local file is added.

**Test plan completeness** — e.g. `12 test cases · 12/12 full Given When Then · 13/14 LADR scenarios covered · 3/3 Jira acceptance criteria covered` or `Referenced: Domino Test Plan.xlsx · Inc as full · 0 parsed (local file missing)`.

**Attachment fields parsed:** `section`, `summary` (high-level scenario), Given/When/Then steps (from **any** step column — `Step Summary`, `Test Steps`, etc.; split combined blobs via `testplan_gwt.py`), `mascot_links` (QA/SIT Mascot link columns and hyperlinks), `evidence_text` (SIT Jobs, QA Jobs, Comments, Evidence, and similar columns — Edit ID, Caption Group ID, Pegasus ID, Job ID, or bare UUID), `evidence_ids` (parsed from `evidence_text` + mapped Jira AC), Story. **Given When Then completeness** counts test cases with all three markers in step **content** (including common typos e.g. `Than:` → `Then`), not whether columns are named Given/When/Then.

**Report Evidence column** — `render_testplan_evidence()`:

| `testPlanSource` | Evidence display |
|----------------|------------------|
| `jira_attachment`, `local_testplans`, `sharepoint_local` | Mascot links first, then parsed SIT/QA job IDs |
| `workspace_generated` | **No execution evidence** — `testplan_evidence.py` skips step extraction (`include_steps=False`) |
| `referenced_not_local` | Pending / setup hint until local file added |

**Report note** — `testPlanSummaryNote` from `build_testplan_summary_note()` — filename/sheet only when actually parsed; generated plans state local Spec2Test origin (not Domino defaults).

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
