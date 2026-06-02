# Confluence / LADR requirements

When a Jira story references a **LADR** or Confluence design doc (especially ESS status codes and milestones), fetch and merge those requirements with Jira acceptance criteria before computing **Test plan acceptance criteria coverage %**.

## When to run

- Jira description or comments mention **LADR**, **Confluence**, or link to `atlassian.net/wiki/...`
- Test plan scenarios align to LADR ESS milestones (`demandAcknowledgment`, `manifestationAvailability`, `orderStatus`, `registrationStatus`) rather than Jira AC wording
- Coverage summary shows **0%** despite a parsed test plan with full Given/When/Then

Skip when `--skip-testplan` or `--skip-confluence` (if added) or manifest sets `validateConfluence: false`.

## Fetch (one shell turn)

```bash
python scripts/fetch_confluence_requirements.py {ISSUE-KEY} --from-jira-cache
python scripts/fetch_jira_testplan.py {ISSUE-KEY} --from-jira-cache
```

`fetch_jira_testplan.py` **auto-invokes** Confluence fetch when `{KEY}-confluence.json` is missing or empty.

Cache: `reports/.cache/{KEY}-confluence.json`

**Quick links (report header):** `build_quick_links()` calls `collect_confluence_page_links()` — sources include `confluence.json` (`pages`, `confluenceUrls`), `testplan.json` → `confluence.pages`, Jira `remoteLinks`/description/comments, and wiki URLs embedded in any `reports/.cache/{KEY}*.json` (e.g. `{KEY}-analysis.json`). Do not omit Confluence when LADR requirements exist but `pages` is empty (inferred ESS table).

### Atlassian MCP (agent)

When REST credentials are unavailable or for freshest content, call in parallel with Jira:

1. Read MCP schema for `getConfluencePage`
2. `cloudId`: `wbdstreaming.atlassian.net`
3. `pageId`: numeric ID from wiki URL (`.../pages/2984378410/...`) or tiny link
4. `contentFormat`: `markdown`

Persist to cache:

```json
{
  "issueKey": "MSC-204417",
  "pages": [{ "id": "2984378410", "title": "...", "bodyText": "...", "webUrl": "..." }],
  "ladrRequirements": [ ... ],
  "status": "ok"
}
```

Or run `fetch_confluence_requirements.py` after MCP auth so REST uses `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN`.

## LADR ESS requirements (Caption Monitoring)

Parsed as `L1`…`Ln` only when the Confluence body has **real ESS context** (`\bess\b` or explicit milestone task names). Substrings like **“address”** must **not** trigger the ESS table parser.

From the LADR **ESS** section:

| Task | Statuses |
|------|----------|
| `demandAcknowledgment` | Completed, Failure |
| `manifestationAvailability` | Pending, Completed |
| `orderStatus` | Pending, Processing, Completed, Failure, Skipped |
| `registrationStatus` | Pending, Completed, Failure |

Optional status-code rows: **8000** (`STATUS_FAILURE`), **9000** (`STATUS_ERROR`).

## Mapping test cases → requirements

1. **LADR milestone** — match ESS `task` + `status` in Summary / Then steps (e.g. `demandAcknowledgment` + `Completed` → `L1`)
2. **Jira AC inference** — ESS scenarios imply **R1** (V2 ESS), **R2** (status propagation), **R3** (failure / 8000 / 9000)
3. **Explicit ID** — Summary or steps mention `R1`, `L3`, etc.
4. **Keyword overlap** — legacy token match on Jira AC text

## Coverage metrics

**Test plan acceptance criteria coverage %** scores against **Jira acceptance criteria + LADR scenarios** when LADR is present:

```
coverageDetail example:
12 test cases · 12/12 full Given When Then · 13/14 LADR scenarios covered · 3/3 Jira acceptance criteria covered
```

Use **`NA`** only when `status` is `no_testplan`. Do not report **0%** when test cases semantically cover LADR/Jira scope but lacked token overlap — re-run fetch after Confluence merge.

## Passport / pick-genie design pages (non-ESS)

When the linked wiki page describes **passport attachment scenarios** (e.g. MSC-205625, MSC-204417) and does **not** contain an ESS milestone table, `confluence_requirements.py` uses **`parse_passport_confluence_requirements()`**:

| Scenario (examples) | Requirement text |
|---------------------|------------------|
| MVP Full | Passport always attached |
| Incremental to Full on PICK | Passport when pick evaluates full |
| MDU to Full in Pack | Passport in pack fulfillment |
| Incremental | Stamp-change audit path |
| MDU in Pick | Passport not attached (expected) |

Test-case mapping uses `kind: passport_scenario` keyword rules in `map_testcases_to_requirements()` (incremental, full, mdu, pick).

## Report impact

- `{{TESTPLAN_COVERAGE_PCT}}` — combined Jira + LADR percentage
- `{{TESTPLAN_COVERAGE_DETAIL}}` — separate LADR and Jira counts when available
- `{{LADR_TRACEABILITY_BLOCK}}` — §3 table: each L1…Ln → mapped Excel test case ID(s); **Gap** when no test case covers that LADR item
- Evidence column uses **`render_testplan_evidence()`** — Mascot links first; else Edit/Caption Group/Pegasus/Job IDs from **SIT Jobs** and similar Excel columns (`testplan_evidence.py`)
- `{{TESTPLAN_GAPS_LIST}}` — list uncovered `L*` / `R*` IDs (e.g. missing STATUS_ERROR 9000 scenario)

Build report test-plan placeholders in one call:

```python
from coverage_report_helpers import build_testplan_report_fields
fields = build_testplan_report_fields("MSC-204417")
# fields["{{LADR_TRACEABILITY_BLOCK}}"], fields["{{TESTPLAN_ROWS}}"], ...
```
