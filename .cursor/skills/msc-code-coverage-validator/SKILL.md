---
name: msc-code-coverage-validator
description: >-
  Validates MSC Jira story implementation against linked GitHub PRs. Fetches Jira
  via Atlassian MCP, resolves PR links, reviews code with gh CLI, maps acceptance
  criteria to implementation and tests, differentiates dev-owned unit/integration
  coverage from QA-owned E2E/manual scope, and reports requirement coverage % plus
  CI test coverage as a downloadable HTML report. Use when validating an MSC Jira
  ticket against its PR, checking whether code matches the story description,
  asking what dev tests cover vs what QA must verify, or asking for coverage % for
  acceptance criteria on wbdstreaming.atlassian.net. Supports --auto, --fetch-only,
  --from-cache, --pr, --repo, and manifest files to avoid repeated manual fetches.
---

# MSC code coverage validator

Validate that GitHub PR(s) linked to an MSC Jira story implement the described requirements and quantify coverage at four levels, **separating dev test ownership from QA handoff**:

| Metric | Meaning |
|--------|---------|
| **Dev code coverage %** | Share of Jira AC/requirements with matching production code (display label; was “Requirement coverage”) |
| **Dev unit/integration test coverage %** | Share of **dev-owned** AC/requirements covered by unit and/or integration tests in the PR (shown in Coverage summary) |
| **Test requirement coverage %** | *(internal)* Share of AC with any automated test evidence — computed for traceability but **not shown** in Coverage summary |
| **CI line coverage %** | Line/branch coverage from PR checks (Codecov, SonarQube, pytest-cov, etc.) when reported |

Also produce a **QA scope summary**: which requirements QA must verify (E2E, manual, regression) because dev automated tests do not fully cover them.

Pattern references: `plan-aware-review`, `pr-review`, and `plan-feature` from [media-lib-arch-agent-context/skills](https://github.com/wbd-msc/media-lib-arch-agent-context/tree/main/skills).

## Preconditions

- **Atlassian MCP** authenticated for `wbdstreaming.atlassian.net`.
- **`gh` CLI** installed and authenticated (`gh auth status`).
- Read MCP tool schemas before calling `getJiraIssue`, `getJiraIssueRemoteIssueLinks`, or `searchJiraIssuesUsingJql`.
- **Run options:** Read [references/run-options.md](references/run-options.md). Parse inline flags, manifest, and workspace defaults before fetching.
- **Auto-approve:** Read [references/auto-approve-setup.md](references/auto-approve-setup.md). Run `python scripts/install_coverage_validator_permissions.py` once. Slash command `/msc-code-coverage-validator` defaults to `--auto --write`.

## Run options (Step 0 — always first)

Parse the user message and merge options from (highest priority wins):

1. **Inline flags** — `--auto`, `--fetch-only`, `--from-cache`, `--pr URL`, `--repo org/repo`, `--write`, `--no-write`, `--manifest PATH`, `--skip-pr-search`, `--skip-jira`, `--post-jira`, `--cache-max-age N`
2. **Manifest** — `reports/.cache/{ISSUE-KEY}-manifest.json` or path from `--manifest`
3. **Workspace defaults** — `.coverage-validator.defaults.json` at repo root (see [validator.defaults.example.json](validator.defaults.example.json))

| Mode | When | Behavior |
|------|------|----------|
| **auto** (`--auto`) | User wants one-shot | Fetch → analyze → write HTML; no mid-run confirmation |
| **fetch-only** (`--fetch-only`) | Warm cache | MCP Jira + gh/prefetch script → cache files; stop |
| **from-cache** (`--from-cache`) | Repeat run | Use fresh `reports/.cache/{KEY}-prefetch.json` and optional jira cache; skip gh if not stale |
| **interactive** | Default when no flags | Ask once for missing PR URL/repo; confirm before write unless `--write` |

**Default for `/msc-code-coverage-validator` slash command:** treat as **`--auto --write`** unless the user opts out.

**Minimize Allow/Run prompts (mandatory agent behavior):**

1. Install allowlist once: `python scripts/install_coverage_validator_permissions.py` (see [auto-approve-setup.md](references/auto-approve-setup.md)).
2. **One MCP turn** — call `getJiraIssue` and `getJiraIssueRemoteIssueLinks` in parallel (never sequential round-trips).
3. **One shell turn** — `python scripts/fetch_coverage_github.py {KEY} ...` or read cache; never N separate `gh` invocations.
4. **`--from-cache`** when `reports/.cache/{KEY}-prefetch.json` is fresh.

**Cache paths:** `reports/.cache/{ISSUE-KEY}-prefetch.json`, `{ISSUE-KEY}-jira.json`, `{ISSUE-KEY}-manifest.json`

**GitHub prefetch (recommended to avoid repeated gh approvals):**

```bash
python scripts/prefetch_coverage_inputs.py {ISSUE-KEY} --pr {PR_URL}
python scripts/prefetch_coverage_inputs.py {ISSUE-KEY} --repo {org}/{repo} --search-pr
```

Then run validation: `@msc-code-coverage-validator {ISSUE-KEY} --from-cache --auto`

**Batch fetches in auto mode:** Call `getJiraIssue` and `getJiraIssueRemoteIssueLinks` in parallel. Run all `gh` commands in one shell block or read prefetch cache. Save manifest after successful run for reuse.

## Workflow

```
Task Progress:
- [ ] Step 0: Parse run options (flags, manifest, defaults)
- [ ] Step 1: Resolve Jira issue key or URL
- [ ] Step 2: Fetch Jira story and extract requirements
- [ ] Step 3: Resolve linked GitHub PR(s)
- [ ] Step 4: Fetch PR changes and CI status
- [ ] Step 5: Map requirements to code, tests, and dev/QA ownership
- [ ] Step 6: Compute coverage percentages (including dev test coverage)
- [ ] Step 7: Build HTML report with dev vs QA sections
- [ ] Step 8: Write report file
```

### Step 1: Resolve issue

Accept: issue key (`MSC-1234`), browse URL, ARI from search, or `issueKey` in manifest. If ambiguous and not `--auto`, ask once; in `--auto` mode, fail fast with a clear message.

### Step 2: Fetch Jira story

Skip when `--skip-jira` and fresh `reports/.cache/{KEY}-jira.json` exists.

Otherwise:

1. Resolve `cloudId`: pass `wbdstreaming.atlassian.net` first; if that fails, call `getAccessibleAtlassianResources`.
2. Call `getJiraIssue` with `responseContentFormat: "markdown"`.
3. Request fields: `summary`, `description`, `issuetype`, `status`, `priority`, `components`, `labels`, `comment`, `issuelinks`, and acceptance-criteria custom fields visible in the response (common hint: `customfield_10037`).
4. In **`fetch-only`** or **`auto`** mode, also call `getJiraIssueRemoteIssueLinks` in parallel with step 2.
5. Extract discrete **requirement items** from:
   - Acceptance criteria (bullets, numbered lists, Given/When/Then)
   - User story scope in description
   - Explicit in-scope / out-of-scope statements
   - Non-functional requirements when stated (performance, security, logging)

Number each item `R1`, `R2`, … List **assumptions** and **gaps** when AC is incomplete.

In **`fetch-only`** mode, write cache to `reports/.cache/{KEY}-jira.json` (issue markdown, fields, remote links, extracted requirements) and stop unless GitHub prefetch is also requested.

### Step 3: Resolve GitHub PR(s)

Resolution order (stop when URLs found unless validating all):

1. **`--pr URL`** from inline flags or manifest — use directly; skip search when `--skip-pr-search`.
2. **`reports/.cache/{KEY}-prefetch.json`** — `prUrls` when `--from-cache` and cache is fresh.
3. **`getJiraIssueRemoteIssueLinks`** — GitHub PR URLs in remote links.
4. **Issue description and comments** — regex `https://github.com/[^/\s]+/[^/\s]+/pull/\d+`.
5. **Issue links** — linked development or implementation tickets that may contain PR URLs.
6. **Branch name heuristic** — when `repo` is known (defaults, `--repo`, or partial link):
   ```bash
   gh search prs "{ISSUE-KEY}" --repo {org}/{repo} --state open,closed --limit 10
   ```

If no PR is found: in **`auto`** mode, fail with what was checked; in **interactive** mode, ask once for PR URL or repo.

If multiple PRs apply, validate each separately then produce a rolled-up summary.

### Step 4: Fetch PR changes and CI

**Prefer cache:** If `--from-cache` and `reports/.cache/{KEY}-prefetch.json` exists and is not stale (`cacheMaxAgeHours`, default 24), read `view`, `diff`, `diffNames`, `checks`, `codecovComment` from cache — do not re-run `gh`.

**Otherwise** run prefetch script (preferred) or one batched shell block:

```bash
python scripts/prefetch_coverage_inputs.py {ISSUE-KEY} --pr {URL} --mode fetch-only
```

Or manually:

```bash
gh pr view {number} --repo {org}/{repo} --json title,state,author,body,headRefName,baseRefName,files,commits
gh pr diff {number} --repo {org}/{repo}
gh pr checks {number} --repo {org}/{repo}
```

In **`fetch-only`** mode, after Jira + GitHub cache writes, print cache paths and suggested next command (`--from-cache --auto`); do not analyze.

For CI line coverage, see [references/github-coverage.md](references/github-coverage.md).

Record: changed file paths, test files in diff (tag each as **unit** or **integration** using path/framework heuristics), CI pass/fail, and any coverage numbers from check output or bot comments.

### Step 5: Map requirements to code, tests, and dev/QA ownership

Read [references/dev-qa-test-scope.md](references/dev-qa-test-scope.md) and apply it to every requirement.

For each requirement `R{n}`:

**Production code**

| Status | Meaning |
|--------|---------|
| **Implemented** | Clear evidence in PR diff |
| **Partial** | Related change but incomplete or missing edge cases |
| **Missing** | No relevant change found |
| **N/A** | Explicitly out of scope in Jira |

**Automated tests (any tier)**

| Status | Meaning |
|--------|---------|
| **Covered** | Test file/assertion clearly exercises this requirement |
| **Partial** | Indirect or weak test evidence |
| **Missing** | No test change for this requirement |
| **N/A** | Requirement is non-code (docs-only, process) |

**Dev vs QA columns** (required for every scored requirement)

| Field | Values |
|-------|--------|
| **Owner** | Dev / Shared / QA |
| **Dev tier** | Unit / Integration / Both / N/A |
| **Dev test status** | Covered / Partial / Missing / N/A |
| **QA scope** | None / Spot-check / E2E / Manual / Regression |

Rules:
- **Dev** + tier **Unit** or **Integration** when PR tests prove the requirement at that level.
- **Shared** when dev tests cover logic/API but QA must validate E2E, staging config, or cross-system behavior.
- **QA** when verification is UI, production-like env, exploratory, or NFR without benchmark tests in PR.
- **QA scope None** only when dev tests fully satisfy the AC; otherwise assign the appropriate QA label.

Cite evidence: file path, function/symbol, test name with `(unit)` or `(integration)`, or diff hunk. Do not mark **Implemented** or **Covered** without pointing to specific code/tests.

Review changed production code for correctness vs the requirement (logic, error handling, config, API contract)—not just presence of a file.

### Step 6: Compute coverage percentages

**Dev code coverage %** (same formula as requirement → code mapping)

```
score(R) = 1.0 if Implemented
         = 0.5 if Partial
         = 0.0 if Missing
         = excluded if N/A

requirement_coverage_pct = round(100 * sum(score) / count(scored items), 1)
```

**Requirements mapped**

Count of Jira AC extracted and scored: `{{REQ_MAPPED_SUMMARY}}` e.g. `3/3 AC`. Detail: `{{REQ_MAPPED_DETAIL}}` e.g. `R1–R3`. Class `{{REQ_MAPPED_CLASS}}`: `metric-good` when all AC mapped, `metric-warn` if partial story scope.

**Open gaps**

From Implementation review gap list: `{{OPEN_GAPS_SUMMARY}}` e.g. `2 High · 2 Med`. `{{OPEN_GAPS_DETAIL}}` one-line context. Class `{{OPEN_GAPS_CLASS}}`: `metric-fail` if any High/Critical, `metric-warn` if Medium only, `metric-good` if none.

**Test requirement coverage %** *(internal only — not shown in summary)*

Same formula using test status (**Covered** = 1.0, **Partial** = 0.5, **Missing** = 0.0) across all scored requirements.

**Dev unit/integration test coverage %**

Same formula using **Dev test status**, but only for requirements where **Owner** is Dev or Shared (exclude QA-only and N/A).

Optionally report sub-counts in `{{DEV_COVERAGE_DETAIL}}`: e.g. `4/5 dev-owned — 2 unit, 2 integration, 1 both`.

**QA scope summary** (informational counts, not a percentage gate)

Count requirements by **QA scope** label. **QA remaining** = E2E + Manual + Regression items, plus Dev/Shared items where Dev test status is Partial or Missing. Populate `{{QA_SCOPE_SUMMARY}}` and `{{QA_HANDOFF_LIST}}`.

**CI line coverage %**

Use the best available source, in order:

1. Codecov / Coveralls check summary or PR comment
2. SonarQube quality gate or coverage metric on the PR
3. CI log artifact mentioning `coverage:` or `TOTAL` from pytest-cov/jest/nyc
4. If unavailable: use display value **`NA`** (not `—` or “Not available”) and note **`No PR for {ISSUE-KEY}; {reason}`** (e.g. `develop branch only`) in `{{CI_LINE_NOTE}}` / `{{CI_BRANCH_NOTE}}`.

When both line and branch coverage exist, report both as percentages; use **line** as the primary CI metric in the summary table.

**Coverage summary card CSS classes** — compute for each percentage metric:

```
metric_class(pct) =
  "metric-na"   if pct is "NA", "Not assessable", "—", or non-numeric
  "metric-good" if value >= 85
  "metric-warn" if value >= 70 and < 85
  "metric-fail" if value < 70
```

Apply `{{REQ_COVERAGE_CLASS}}` to **Dev code coverage** (required). Set `{{DEV_COVERAGE_CLASS}}` using the same tiers. Set `{{CI_LINE_CLASS}}` and `{{CI_BRANCH_CLASS}}` to `metric-na` when CI values are **`NA`**; use `metric-good` / `metric-warn` / `metric-fail` when CI percentages are available.

**Coverage summary cards (7 total)** in three groups — **Implementation & tests:** Dev code coverage, Dev unit/integration test coverage, Requirements mapped. **QA & release risk:** QA scope remaining, Open gaps. **CI pipeline coverage:** CI line coverage, CI branch coverage. Do **not** include Test requirement coverage or PR traceability in the summary. Use restrained coloring: white cards, colored left border + value only (`metric-good` / `metric-warn` / `metric-fail` / `metric-na` / `metric-neutral`).

### Step 7: Build HTML report

Read [report-template.html](report-template.html) and produce a **complete, self-contained HTML file** by replacing all `{{PLACEHOLDER}}` tokens.

**Required placeholders**

| Placeholder | Value |
|-------------|-------|
| `{{ISSUE_KEY}}` | Jira key |
| `{{STORY_TITLE}}` | Issue summary (escape HTML entities) |
| `{{JIRA_URL}}` | `https://wbdstreaming.atlassian.net/browse/{KEY}` |
| `{{ISSUE_STATUS}}`, `{{ISSUE_TYPE}}` | From Jira |
| `{{GENERATED_DATE}}` | Report date (ISO or readable) |
| `{{VERDICT}}` | Pass / Pass with gaps / Fail |
| `{{VERDICT_CLASS}}` | `pass`, `pass-gaps`, or `fail` (maps to CSS class) |
| `{{VERDICT_RATIONALE}}` | One-line rationale |
| `{{REQ_COVERAGE_PCT}}`, `{{DEV_COVERAGE_PCT}}` | e.g. `70.0%` or `Not assessable` |
| `{{REQ_COVERAGE_CLASS}}`, `{{DEV_COVERAGE_CLASS}}` | `metric-good` (≥85%), `metric-warn` (70–84.9%), `metric-fail` (<70%), `metric-na` |
| `{{REQ_COVERAGE_DETAIL}}`, `{{DEV_COVERAGE_DETAIL}}` | e.g. `3.5/5 scored`, `4/5 dev-owned — 2 unit, 2 integration` |
| `{{REQ_MAPPED_SUMMARY}}`, `{{REQ_MAPPED_DETAIL}}`, `{{REQ_MAPPED_CLASS}}` | e.g. `3/3 AC`, `R1–R3`, `metric-good` |
| `{{OPEN_GAPS_SUMMARY}}`, `{{OPEN_GAPS_DETAIL}}`, `{{OPEN_GAPS_CLASS}}` | e.g. `2 High · 2 Med`, brief note, `metric-warn` |
| `{{QA_SCOPE_SUMMARY}}` | e.g. `2 items` — use `metric-neutral` card (no purple) |
| `{{QA_HANDOFF_LIST}}` | `<li>` items — QA scenarios not covered by dev tests |
| `{{DEV_COVERED_LIST}}` | `<li>` items — what dev unit/integration tests already prove |
| `{{CI_LINE_COVERAGE}}`, `{{CI_BRANCH_COVERAGE}}` | Percent or **`NA`** when no PR/CI |
| `{{CI_LINE_NOTE}}`, `{{CI_BRANCH_NOTE}}` | e.g. `Source: codecov` or `No PR for MSC-204417; develop branch only` |
| `{{CI_LINE_CLASS}}`, `{{CI_BRANCH_CLASS}}` | `metric-na` when unavailable; else tier class if numeric |
| `{{PR_NOTE}}` | Optional `<div class="note-box">…</div>` when no PR linked; empty string if PR exists |
| `{{PR_ROWS}}` | HTML `<tr>` rows for linked PRs |
| `{{REQUIREMENT_ROWS}}` | HTML `<tr>` rows — Code, Dev tests, Owner, QA scope, Evidence (see below) |
| `{{CORRECTLY_IMPLEMENTED_LIST}}` | `<li>` items |
| `{{GAPS_LIST}}` | `<li class="critical|high|medium">` items |
| `{{ASSUMPTIONS_LIST}}`, `{{ACTIONS_LIST}}` | `<li>` items |

**Status badges** (requirement table):

```html
<span class="badge badge-implemented">Implemented</span>
<span class="badge badge-partial">Partial</span>
<span class="badge badge-missing">Missing</span>
<span class="badge badge-covered">Covered</span>
<span class="badge badge-na">N/A</span>
<span class="badge badge-not-verified">Not verified</span>
<span class="badge badge-dev">Dev</span>
<span class="badge badge-shared">Shared</span>
<span class="badge badge-qa">QA</span>
<span class="badge badge-unit">Unit</span>
<span class="badge badge-integration">Integration</span>
<span class="badge badge-spot">Spot-check</span>
<span class="badge badge-e2e">E2E</span>
<span class="badge badge-manual">Manual</span>
```

Escape user-provided text (`&`, `<`, `>`, `"`) in HTML body content. Use `<code>` for file paths and test names.

In chat, give a **brief summary** (verdict + dev code coverage %, dev unit/integration coverage %, QA handoff count) and the path to the HTML file — do not paste the full HTML unless the user asks.

### Step 8: Write output

Skip file write when `--no-write` or `writeReport: false` in manifest/defaults (chat summary only).

```bash
mkdir -p reports reports/.cache
```

Write the filled HTML to:

`reports/<ISSUE-KEY>-<TIMESTAMP>.html`

**Timestamp format:** `MM-DD-YYYY-HH-MM-SS-{TZ}` in the **worker's local timezone** (e.g. IST, EST) — filesystem-safe form of `mm/dd/yyyy-hh/mm/ss`. Example: `MSC-204417-05-26-2026-14-30-52-IST.html`.

- **Default:** laptop local timezone via `datetime.now().astimezone()` (works on Windows without IANA config; do not fall back to UTC).
- **Override:** `.coverage-validator.defaults.json` — `"timezone": "Asia/Kolkata"` or `"America/New_York"`, optional `"timezoneLabel": "IST"` or `"EST"` for the filename suffix.
- **Helper:** `python scripts/coverage_report_timestamp.py MSC-204417` returns path, display date, and label.

Set `{{GENERATED_DATE}}` in the report header to the same local instant, e.g. `2026-05-26 14:30:52 IST`. Generate at write time; do not reuse an old timestamp.

Record the path in `reports/.cache/<ISSUE-KEY>-manifest.json` as `"lastReportFile"`.

Save run options to `reports/.cache/<ISSUE-KEY>-manifest.json` for reuse.

Tell the user the full path so they can open it in a browser. Include the **reuse command**:

`@msc-code-coverage-validator {KEY} --from-cache --auto`

Optional: also write `reports/<ISSUE-KEY>-<TIMESTAMP>.md` if the user asks for markdown.

Optional: add a Jira comment summary via `addCommentToJiraIssue` when `--post-jira` or `postJiraComment: true`.

## Quality bar

- Every requirement row must have evidence or an explicit **Missing** reason.
- Every scored requirement must have **Owner**, **Dev tier**, **Dev test status**, and **QA scope** — no blank dev/QA columns.
- Separate **dev code coverage**, **dev unit/integration test coverage**, and **CI line coverage** in prose and tables.
- Explicitly list what dev unit/integration tests cover vs what QA must still verify.
- Flag PRs that implement code without dev tests for dev-owned AC items.
- Flag AC items implemented in code but contradicting the Jira description.
- Redact secrets and tokens from evidence citations.

## Additional resources

- **Primary report format:** [report-template.html](report-template.html)
- Markdown reference (optional): [report-template.md](report-template.md)
- Worked example: [examples.md](examples.md)
- GitHub / CI coverage commands: [references/github-coverage.md](references/github-coverage.md)
- Dev vs QA test scope rules: [references/dev-qa-test-scope.md](references/dev-qa-test-scope.md)
- Run modes, flags, cache, prefetch: [references/run-options.md](references/run-options.md)
- Auto-approve Allow/Run prompts: [references/auto-approve-setup.md](references/auto-approve-setup.md)
- Workspace defaults template: [validator.defaults.example.json](validator.defaults.example.json)
