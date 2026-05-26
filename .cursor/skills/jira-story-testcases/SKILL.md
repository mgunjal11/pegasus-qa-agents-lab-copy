---
name: jira-story-testcases
description: >-
  Reads Jira user stories via Atlassian MCP and generates QMetry-format test
  cases (11 QMetry columns, Given/When/Then, downloadable Excel with merged
  cells). Shows a full draft for review before writing files. Use when the user
  asks to create test cases from a Jira story, user story, ticket, or acceptance
  criteria on wbdstreaming.atlassian.net.
---

# Jira story → QMetry test cases

## Preconditions

- Atlassian MCP is enabled and authenticated (`wbdstreaming.atlassian.net`).
- Prefer MCP over guessing: resolve **cloudId** and fetch the full issue before writing test cases.
- Read tool schemas in the MCP folder before calling `getJiraIssue`, `searchJiraIssuesUsingJql`, or `getAccessibleAtlassianResources`.

## Defaults (confirm or override with the user)

| Item | Default |
|------|---------|
| Site | `wbdstreaming.atlassian.net` |
| Output format | QMetry Excel (.xlsx) matching FF2.0 template; TSV + MD intermediates |
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
- [ ] Step 2: Fetch story via Atlassian MCP
- [ ] Step 3: Extract requirements and acceptance criteria
- [ ] Step 4: Identify test scenarios
- [ ] Step 5: Draft test cases in QMetry format
- [ ] Step 6: Show draft to user and wait for approval
- [ ] Step 7: Write TSV, generate Excel, confirm download path (only after approval)
```

### Step 1: Resolve issue

Accept: issue key (`MSC-1234`), browse URL, or ARI from search. If ambiguous, ask once.

### Step 2: Fetch story

1. Resolve `cloudId`: pass `wbdstreaming.atlassian.net` first; if that fails, call `getAccessibleAtlassianResources`.
2. Call `getJiraIssue` with `responseContentFormat: "markdown"`.
3. Request fields needed for testing: `summary`, `description`, `issuetype`, `status`, `priority`, `components`, `labels`, `parent`, `subtasks`, `issuelinks`, and any acceptance-criteria custom fields visible in the response.
4. If the story is thin, fetch linked issues (parent epic, design doc links, subtasks) via `issuelinks` / JQL — do not invent requirements.

### Step 3: Extract requirements

Pull from the issue body:

- **User story** (As a… I want… So that…)
- **Acceptance criteria** (Given/When/Then, bullet checklist, or numbered list)
- **Scope / out of scope**
- **Dependencies**, feature flags, environments, roles
- **Non-functional** notes when stated

List **assumptions** and **open questions** separately when AC is incomplete.

### Step 4: Identify scenarios

For each acceptance criterion, derive at minimum:

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
- Include AC reference in Summary text or Step Summary where helpful.

### Step 6: Review gate (required)

Show the user a complete draft before writing any file. The draft must include:

- **Story summary**: key, title, link, issue type, status
- **Requirements extracted**: bullet list from AC + notable constraints
- **Assumptions / gaps**: anything not specified in Jira
- **Full QMetry table**: all rows in markdown (Summary through TestData Dependent)
- **Coverage summary**: case count by scenario type; AC items with no test case

**Wait for explicit approval** before writing files.

### Step 7: Write output (after approval)

1. Ensure `openpyxl` is available: `pip install -r requirements.txt` (once per environment).
2. Write TSV under `testcases/<ISSUE-KEY>-testcases.tsv` (intermediate; QMetry column layout).
3. Generate Excel by running:

```bash
python scripts/generate_qmetry_excel.py testcases/<ISSUE-KEY>-testcases.tsv
```

4. Write `testcases/<ISSUE-KEY>-testcases.md` as a human-readable mirror.
5. **Tell the user the full path** to the `.xlsx` file so they can open or download it from the workspace (e.g. `testcases/MSC-1234-testcases.xlsx`).

| File | Purpose |
|------|---------|
| `<ISSUE-KEY>-testcases.xlsx` | **Primary deliverable** — downloadable Excel for QMetry import |
| `<ISSUE-KEY>-testcases.tsv` | Intermediate tab-separated source for the Excel generator |
| `<ISSUE-KEY>-testcases.md` | Markdown mirror for review/archive |

Optional (only if asked): add a Jira comment with test case summary via `addCommentToJiraIssue`.

## Quality bar

- **Given/When/Then** steps are specific and pass/fail decidable.
- **Then** states observable outcomes, not subjective judgments.
- No duplicate cases that differ only in wording.
- Do not fabricate endpoints, UI labels, or business rules — note TBD in Summary or Step Summary.
- Redact secrets; use placeholders in **Given** steps.

## Additional resources

- Column definitions and TSV layout: [testcase-template.md](testcase-template.md)
- Excel generator: `scripts/generate_qmetry_excel.py`
- Worked example: [examples.md](examples.md)
