---
name: jira-story-testcases
description: >-
  Reads Jira user stories via Atlassian MCP and generates QMetry-format test
  cases (11 QMetry columns, Given/When/Then, downloadable Excel with merged
  cells). When LADR/Confluence is linked, drafts cover Jira acceptance criteria
  and LADR ESS scenarios together; otherwise Jira only. Shows a full draft for
  review before writing files. Invoke via @msc-testcase-writer KEY or
  /msc-testcase-writer KEY on wbdstreaming.atlassian.net.
---

# Jira story → QMetry test cases

## Preconditions

- Atlassian MCP is enabled and authenticated (`wbdstreaming.atlassian.net`).
- Prefer MCP over guessing: resolve **cloudId** and fetch the full issue before writing test cases.
- Read tool schemas in the MCP folder before calling `getJiraIssue`, `searchJiraIssuesUsingJql`, or `getAccessibleAtlassianResources`.
- Python: `pip install -r requirements.txt` (needs `openpyxl` for Excel output).

## Defaults (confirm or override with the user)

| Item | Default |
|------|---------|
| Site | `wbdstreaming.atlassian.net` |
| Output format | QMetry Excel (.xlsx) only in `testcases/` (matches FF2.0 template) |
| Summary format | `{ISSUE-KEY}_{descriptive scenario and verification}` |
| Step format | `Given:` / `When:` / `Then:` in **Step Summary** — 3 rows per test case |
| Automatable | Yes |
| Automation Status | Not Started |
| Priority | P0 (happy path), P1 (negative/edge) |
| Test Type | End to End |
| Regression Test (Y/N) | Yes |
| Story column | Jira issue key |

**Do not assume** without asking: QMetry **Folders** path or priority overrides.

Reference template: `QMetry FF2.0.xlsx` — sheet **QMetry Template**, 11 columns, merged metadata cells per 3-row block (including **Status**; only Step Summary unmerged).

## Workflow

```
Task Progress:
- [ ] Step 1: Resolve Jira issue key or URL
- [ ] Step 2: Fetch story via Atlassian MCP (+ remote wiki links)
- [ ] Step 2b: Fetch Confluence / LADR when linked (else skip — Jira only)
- [ ] Step 3: Extract requirements (Jira R1…Rn; + L1…Ln when LADR present)
- [ ] Step 4: Identify test scenarios (Jira AC + LADR milestones when applicable)
- [ ] Step 5: Draft test cases in QMetry format
- [ ] Step 6: Show draft to user and wait for approval
- [ ] Step 7: Write cache TSV, build Excel only in testcases/ (only after approval)
```

### Step 1: Resolve issue

Accept: issue key (`MSC-1234`), browse URL, or ARI from search. If ambiguous, ask once.

### Step 2: Fetch story

1. Resolve `cloudId`: pass `wbdstreaming.atlassian.net` first; if that fails, call `getAccessibleAtlassianResources`.
2. **Parallel MCP:** `getJiraIssue` (`responseContentFormat: "markdown"`) + `getJiraIssueRemoteIssueLinks`.
3. Request fields: `summary`, `description`, `issuetype`, `status`, `priority`, `components`, `labels`, `parent`, `subtasks`, `issuelinks`, `comment`, `attachment`.
4. Persist `reports/.cache/{KEY}-jira.json` with `requirements` (R1…Rn), `remoteLinks` / `confluenceLinks` (`pageId` when wiki URLs present).
5. If the story is thin, fetch linked issues via `issuelinks` / JQL — do not invent requirements.

### Step 2b: Fetch Confluence / LADR (when linked)

**Skip** when no wiki/LADR signals — proceed **Jira only**.

When description, comments, or remote links reference Confluence / LADR / ESS:

```bash
python scripts/fetch_confluence_requirements.py {ISSUE-KEY} --from-jira-cache
```

Or MCP `getConfluencePage` (`pageId` from wiki URL, `contentFormat: markdown`).

Optional context bundle:

```bash
python scripts/prepare_testcase_writer_context.py {ISSUE-KEY} --from-jira-cache --fetch
```

Read `mode`: `jira_and_ladr` when `ladrRequirements` is non-empty; else `jira_only`.

Details: [references/ladr-confluence-requirements.md](references/ladr-confluence-requirements.md)

### Step 3: Extract requirements

**Always — Jira:** user story, acceptance criteria as **R1…Rn**, scope, dependencies, environments.

**When LADR attached (`jira_and_ladr` mode):** also list **L1…Ln** from `ladrRequirements` (ESS task+status or passport scenario text). Do not drop Jira AC — cover **both**.

**When no LADR:** extract Jira only; do not invent L-items.

List **assumptions** and **open questions** separately when AC or LADR is incomplete.

**FR vs NFR (for coverage validator §5):** Behavior AC (passport retained, must deliver, …) is functional. SIT/staging validation-only AC may set `"section": "non-functional"` on that item in `{KEY}-jira.json` — the coverage report shows **NFR (validation)** and caps mapping confidence at **medium** (PR unit tests are not SIT proof).

### Step 4: Identify scenarios

**Jira only:** for each acceptance criterion, derive at minimum:

**Jira + LADR:** same categories for each **R*** item **plus** at least one scenario per **L*** milestone (ESS task+status in Then; passport labels in steps when applicable).

| Category | When to include |
|----------|-----------------|
| Happy path | Always — primary success flow |
| Negative | Invalid input, missing data, unauthorized action |
| Edge / boundary | Limits, empty states, duplicates, timing |
| Role / permission | Multiple actors or access levels mentioned |
| Integration | External systems, APIs, pipelines referenced |
| Regression | Existing behavior that must not break |

One AC may map to multiple test cases; combine trivial checks only when clarity suffers.

### Step 5: Draft test cases

Follow [testcase-template.md](testcase-template.md) exactly (11 columns).

- **Summary**: `{ISSUE-KEY}_{descriptive title}` on row 1 only.
- **3 rows per case**: row 1 = metadata + `Given:` in Step Summary; rows 2–3 = `When:` / `Then:` in Step Summary only.
- **Story**: issue key on row 1.
- **Status**: leave blank for new test cases (merged across 3 rows in Excel).
- Include **R*** / **L*** reference in Summary or Step Summary where helpful (required for coverage-validator §5 trace, §6 review, and QA scope mapping). §5 Evidence displays compact file lists — testcase row mapping still uses full cache data.
- **LADR Then steps:** include milestone **task** and **status** (e.g. `orderStatus Completed`) so `map_testcases_to_requirements()` can score L-items after import.

### Step 6: Review gate (required)

**Exception:** When invoked from **`/msc-dev-code-and-qa-test-coverage-validator`** in **`--auto --write`** mode and Jira has **no test plan** (`no_testplan`), skip this gate and write files immediately (see `.cursor/skills/coverage-validator/references/testplan-missing-fallback.md`).

Show the user a complete draft before writing any file. The draft must include:

- **Story summary**: key, title, link, issue type, status
- **Requirements extracted**: Jira R1…Rn; when LADR linked, also L1…Ln with task/status
- **Source mode**: `jira_only` or `jira_and_ladr`
- **Assumptions / gaps**: anything not specified in Jira or LADR
- **Full QMetry table**: all rows in markdown (Summary through TestData Dependent)
- **Coverage summary**: case count by type; **matrix** mapping each R* and L* (when present) to TC ids

**Wait for explicit approval** before writing files.

### Step 7: Write output (after approval)

**Only** `testcases/<ISSUE-KEY>-testcases.xlsx` — do **not** write `.tsv` or `.md` under `testcases/`.

1. Ensure `openpyxl` is available: `pip install -r requirements.txt` (once per environment).
2. Write QMetry rows to cache (intermediate, not a user deliverable):

   `reports/.cache/<ISSUE-KEY>-testcases-source.tsv`

3. Build Excel:

```bash
python scripts/write_testcase_excel.py <ISSUE-KEY>
```

4. **Tell the user the full path** to the `.xlsx` (e.g. `testcases/MSC-1234-testcases.xlsx`).

| File | Purpose |
|------|---------|
| `testcases/<ISSUE-KEY>-testcases.xlsx` | **Deliverable** — QMetry import |
| `reports/.cache/<ISSUE-KEY>-testcases-source.tsv` | Internal source for Excel build (optional to keep) |

Optional (only if asked): add a Jira comment with test case summary via `addCommentToJiraIssue`.

## Quality bar

- **Given/When/Then** steps are specific and pass/fail decidable.
- **Then** states observable outcomes, not subjective judgments.
- No duplicate cases that differ only in wording.
- Do not fabricate endpoints, UI labels, or business rules — note TBD in Summary or Step Summary.
- Redact secrets; use placeholders in **Given** steps.

## Additional resources

- Column definitions and TSV layout: [testcase-template.md](testcase-template.md)
- LADR / Confluence drafting: [references/ladr-confluence-requirements.md](references/ladr-confluence-requirements.md)
- Context helper: `scripts/prepare_testcase_writer_context.py`
- Excel generator: `scripts/write_testcase_excel.py` (reads `reports/.cache/{KEY}-testcases-source.tsv`)
- Worked example: [examples.md](examples.md)
