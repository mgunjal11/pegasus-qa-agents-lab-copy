---
name: msc-dev-code-and-qa-test-coverage-validator
author: Mayur Gunjal
description: >-
  Validates MSC Jira story implementation against linked GitHub PRs and attached
  QMetry test plans. Fetches Jira via Atlassian MCP (including attachments),
  resolves PR links, reviews code with gh CLI, maps acceptance criteria to
  implementation, dev tests, and QA test plan cases, differentiates dev-owned
  unit/integration coverage from QA-owned E2E/manual scope, and reports requirement
  coverage % plus CI test coverage as a downloadable HTML report. Use when validating
  an MSC Jira ticket against its PR and test plan, checking whether code matches
  the story description and attached test cases, asking what dev tests cover vs what
  QA must verify, or asking for coverage % for acceptance criteria on
  wbdstreaming.atlassian.net. Supports --auto, --fetch-only, --from-cache, --pr,
  --repo, --skip-testplan, and manifest files to avoid repeated manual fetches.
---

# MSC dev code and QA test coverage validator

> **Renamed** from `msc-code-coverage-validator` / `/msc-code-coverage-validator`. Do not use the old name in docs, commands, or agent invocations.

Validate that GitHub PR(s) linked to an MSC Jira story implement the described requirements, that **attached QMetry test plans** cover the acceptance criteria, and quantify coverage at five levels, **separating dev test ownership from QA handoff**:

| Metric | Meaning |
|--------|---------|
| **Dev code coverage %** | Share of Jira AC/requirements with matching production code (display label; was “Requirement coverage”) |
| **Dev unit/integration test coverage %** | Share of **dev-owned** AC/requirements covered by unit and/or integration tests in the PR (shown in Coverage summary) |
| **Test plan acceptance criteria coverage %** | Share of Jira acceptance criteria plus linked LADR/Confluence ESS scenarios with ≥1 mapped test case in the attached test plan |
| **Test requirement coverage %** | *(internal)* Share of AC with any automated test evidence — computed for traceability but **not shown** in Coverage summary |
| **CI line coverage %** | Line/branch coverage from PR checks (Codecov, SonarQube, pytest-cov, etc.) when reported |

Also produce a **QA scope summary**: which requirements QA must verify (E2E, manual, regression) because dev automated tests do not fully cover them.

Pattern references: `plan-aware-review`, `pr-review`, and `plan-feature` from [media-lib-arch-agent-context/skills](https://github.com/wbd-msc/media-lib-arch-agent-context/tree/main/skills).

## Preconditions

- **Atlassian MCP** authenticated for `wbdstreaming.atlassian.net`.
- **`gh` CLI** installed and authenticated (`gh auth status`).
- Read MCP tool schemas before calling `getJiraIssue`, `getJiraIssueRemoteIssueLinks`, `getConfluencePage`, or `searchJiraIssuesUsingJql`.
- **Run options:** Read [references/run-options.md](references/run-options.md). Parse inline flags, manifest, and workspace defaults before fetching.
- **Auto-approve:** Read [references/auto-approve-setup.md](references/auto-approve-setup.md). Run `python scripts/install_coverage_validator_permissions.py` once. Slash command `/msc-dev-code-and-qa-test-coverage-validator` defaults to `--auto --write`.

## Run options (Step 0 — always first)

Parse the user message and merge options from (highest priority wins):

1. **Inline flags** — `--auto`, `--fetch-only`, `--from-cache`, `--pr URL`, `--repo org/repo`, `--write`, `--no-write`, `--manifest PATH`, `--skip-pr-search`, `--skip-jira`, `--skip-testplan`, `--post-jira`, `--cache-max-age N`
2. **Manifest** — `reports/.cache/{ISSUE-KEY}-manifest.json` or path from `--manifest`
3. **Workspace defaults** — `.coverage-validator.defaults.json` at repo root (see [validator.defaults.example.json](validator.defaults.example.json))

| Mode | When | Behavior |
|------|------|----------|
| **auto** (`--auto`) | User wants one-shot | Fetch → analyze → write HTML; no mid-run confirmation |
| **fetch-only** (`--fetch-only`) | Warm cache | MCP Jira + gh/prefetch script → cache files; stop |
| **from-cache** (`--from-cache`) | Repeat run | Use fresh `reports/.cache/{KEY}-prefetch.json` and optional jira cache; skip gh if not stale |
| **interactive** | Default when no flags | Ask once for missing PR URL/repo; confirm before write unless `--write` |

**Default for `/msc-dev-code-and-qa-test-coverage-validator` slash command:** treat as **`--auto --write`** unless the user opts out.

**Minimize Allow/Run prompts (mandatory agent behavior):**

1. Install allowlist once: `python scripts/install_coverage_validator_permissions.py` (see [auto-approve-setup.md](references/auto-approve-setup.md)).
2. **One MCP turn** — call `getJiraIssue` and `getJiraIssueRemoteIssueLinks` in parallel (never sequential round-trips).
3. **One shell turn** — `python scripts/fetch_coverage_github.py {KEY} ...` or read cache; never N separate `gh` invocations.
4. **`--from-cache`** when `reports/.cache/{KEY}-prefetch.json` is fresh.

**Cache paths:** `reports/.cache/{ISSUE-KEY}-prefetch.json`, `{ISSUE-KEY}-jira.json`, `{ISSUE-KEY}-testplan.json`, `{ISSUE-KEY}-confluence.json`, `{ISSUE-KEY}-mapping.json`, `{ISSUE-KEY}-manifest.json`

**GitHub prefetch (recommended to avoid repeated gh approvals):**

```bash
python scripts/prefetch_coverage_inputs.py {ISSUE-KEY} --pr {PR_URL}
python scripts/prefetch_coverage_inputs.py {ISSUE-KEY} --repo {org}/{repo} --search-pr
```

Then run validation: `@msc-dev-code-and-qa-test-coverage-validator {ISSUE-KEY} --from-cache --auto`

**Batch fetches in auto mode:** Call `getJiraIssue` and `getJiraIssueRemoteIssueLinks` in parallel. Run all `gh` commands in one shell block or read prefetch cache. Save manifest after successful run for reuse.

## Slash command pipeline (`/msc-dev-code-and-qa-test-coverage-validator`)

When invoked via slash command with issue key in `$ARGUMENTS`, run **end-to-end** with **`--auto --write`** (no confirmation). Match `.cursor/commands/msc-dev-code-and-qa-test-coverage-validator.md`:

| # | Step |
|---|------|
| 0 | Parse flags → manifest → `.coverage-validator.defaults.json` |
| 1 | Resolve `{KEY}` |
| 2 | **Parallel MCP:** `getJiraIssue` (`attachment`, `comment`, `issuelinks`) + `getJiraIssueRemoteIssueLinks` (+ `getConfluencePage` when wiki links); write `{KEY}-jira.json` with `pageId` on remote/confluence links |
| 3 | `fetch_confluence_requirements.py {KEY} --from-jira-cache` |
| 4 | `fetch_jira_testplan.py {KEY} --from-jira-cache` |
| 5 | **One shell:** `prefetch_coverage_inputs.py {KEY} --pr URL …` (multiple `--pr`) or `--from-cache`; branch-only: `fetch_coverage_github.py {KEY} --repo org/repo --compare develop` |
| 6 | `map_requirements_to_diff.py {KEY}` |
| 7 | `build_coverage_report.py {KEY}` [`--analysis` optional] |
| 8 | Manifest `lastReportFile` (builder writes timestamped HTML) |

Never issue multiple separate `gh` invocations; use prefetch cache or one prefetch script call.

## Workflow

```
Task Progress:
- [ ] Step 0: Parse run options (flags, manifest, defaults)
- [ ] Step 1: Resolve Jira issue key or URL
- [ ] Step 2: Fetch Jira story and extract requirements
- [ ] Step 2b: Fetch Confluence / LADR linked from Jira (unless `--skip-testplan`)
- [ ] Step 3: Resolve linked GitHub PR(s)
- [ ] Step 4: Fetch PR changes and CI status
- [ ] Step 5: Fetch and parse attached QMetry test plan (unless `--skip-testplan`)
- [ ] Step 6: Map requirements to code, tests, test plan cases, and dev/QA ownership
- [ ] Step 7: Compute coverage percentages (including dev test and test plan coverage)
- [ ] Step 8: Build HTML report with dev vs QA and test plan sections; run `apply_report_ui_enhancements()`
- [ ] Step 9: Write report file
```

### Step 1: Resolve issue

Accept: issue key (`MSC-1234`), browse URL, ARI from search, or `issueKey` in manifest. If ambiguous and not `--auto`, ask once; in `--auto` mode, fail fast with a clear message.

### Step 2: Fetch Jira story

Skip when `--skip-jira` and fresh `reports/.cache/{KEY}-jira.json` exists.

Otherwise:

1. Resolve `cloudId`: pass `wbdstreaming.atlassian.net` first; if that fails, call `getAccessibleAtlassianResources`.
2. Call `getJiraIssue` with `responseContentFormat: "markdown"`.
3. Request fields: `summary`, `description`, `issuetype`, `status`, `priority`, `components`, `labels`, `comment`, `issuelinks`, `attachment`, and acceptance-criteria custom fields visible in the response (common hint: `customfield_10037`).
4. In **`fetch-only`** or **`auto`** mode, also call `getJiraIssueRemoteIssueLinks` in parallel with step 2.
5. Persist **attachment metadata** and **comment bodies** (plain text or ADF flattened) in `reports/.cache/{KEY}-jira.json` — required for SharePoint test plan links and sheet names (e.g. *Inc as full*). Run `python scripts/fetch_jira_testplan.py {KEY} --from-jira-cache` to auto-populate `testPlanReferences` in the cache.
6. Extract discrete **requirement items** from:
   - Acceptance criteria (bullets, numbered lists, Given/When/Then)
   - User story scope in description
   - Explicit in-scope / out-of-scope statements
   - Non-functional requirements when stated (performance, security, logging)

Number each item `R1`, `R2`, … List **assumptions** and **gaps** when AC is incomplete.

In **`fetch-only`** mode, write cache to `reports/.cache/{KEY}-jira.json` (issue markdown, fields, remote links, extracted requirements) and stop unless GitHub prefetch is also requested.

### Step 2b: Fetch Confluence / LADR requirements

Read [references/confluence-ladr-requirements.md](references/confluence-ladr-requirements.md).

When Jira comments or description mention **LADR** or link to Confluence (`atlassian.net/wiki/...`):

1. **Prefer one shell turn:**
   ```bash
   python scripts/fetch_confluence_requirements.py {ISSUE-KEY} --from-jira-cache
   ```
2. **Or Atlassian MCP** (parallel with Jira when credentials missing): `getConfluencePage` with `cloudId: wbdstreaming.atlassian.net`, `pageId` from wiki URL, `contentFormat: markdown`. Persist body to `reports/.cache/{KEY}-confluence.json` via script or agent write.
3. Parse **ESS milestones** only when Confluence body has real ESS context (`\bess\b` word boundary or explicit `demandAcknowledgment` / `orderStatus` tasks) — **not** substrings inside unrelated words (e.g. “address”).
4. For **passport / pick-genie design pages** (no ESS table), use **`parse_passport_confluence_requirements()`** — scenario rows such as MVP Full, Incremental to Full on PICK, MDU to Full in Pack as `L1`…`Ln`.
5. If no wiki URL is in Jira but comments reference LADR ESS, infer the standard ESS table from comment text (script fallback).

Merge LADR requirements with Jira `R1`…`Rn` before test plan mapping. Test plan fetch (`fetch_jira_testplan.py`) loads this cache automatically.

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

If multiple PRs apply, pass **each URL** in one prefetch call: `prefetch_coverage_inputs.py {KEY} --pr {URL1} --pr {URL2}`.

**No linked PR (branch-only implementation):** When Jira has no PR but manifest/defaults specify `repo` + `compareBranch` (e.g. `develop`):

```bash
python scripts/fetch_coverage_github.py {KEY} --repo wbd-msc/pegasus-ess --compare develop
```

Prefetch cache stores `branchCompare` (`files`, `commits`, `ahead_by`). `map_requirements_to_diff.py` scores requirements from branch file list + commit messages when `prs` is empty. Report uses `build_branch_compare_pr_note()` and `render_branch_compare_pr_rows()`; CI cards show **NA** with note `No PR for {KEY}; {head} branch only`.

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

In **`fetch-only`** mode, write cache to `reports/.cache/{KEY}-jira.json` (issue markdown, fields, remote links, attachments, extracted requirements) and stop unless GitHub prefetch is also requested.

### Step 5: Fetch and parse attached test plan

Skip when **`--skip-testplan`** or manifest/defaults set `validateTestPlan: false`.

Read [references/jira-testplan-validation.md](references/jira-testplan-validation.md).

**Prefer cache:** If `--from-cache` and `reports/.cache/{KEY}-testplan.json` is fresh, read parsed test cases from cache.

**Otherwise** run once (same shell block as GitHub prefetch is OK):

```bash
python scripts/fetch_confluence_requirements.py {ISSUE-KEY} --from-jira-cache
python scripts/fetch_jira_testplan.py {ISSUE-KEY} --from-jira-cache
```

**SharePoint / comment-referenced plans** (e.g. *Refer Inc as full sheet for Test plan and evidence* → `Domino Test Plan.xlsx`): the script extracts `testPlanReferences` from Jira comments. Place the Excel locally at `testplans/Domino Test Plan.xlsx` or set `testPlanPath` / `testPlanSheet` in manifest or `.coverage-validator.defaults.json`. Do **not** report "no attachment" when a comment reference exists — use status `referenced_not_local` and show filename + sheet + setup hint.

Optional sheet override:

```bash
python scripts/fetch_jira_testplan.py {ISSUE-KEY} --from-jira-cache --sheet "Inc as full"
```

If Jira attachment download fails, retry with workspace fallback:

```bash
python scripts/fetch_jira_testplan.py {ISSUE-KEY} --attachment testplans/Domino Test Plan.xlsx --sheet "Inc as full"
```

Parse output: `testCases` (include `section`, `summary`, `mascot_links`, `evidence_text`, `evidence_ids`, `steps`, `mapped_requirements`), `jiraRequirements`, `ladrRequirements`, `ladrTraceability` (L1…Ln → test case IDs), `confluence`, `testPlanReferences`, `testPlanSummaryNote`, `status` (`ok` | `referenced_not_local` | `no_testplan`), `coverage.testplanCoveragePct`, `coverage.jiraRequirementsCovered`, `coverage.ladrRequirementsCovered`, `coverage.coverageDetail`, `localSetupHint`.

**Jira attachment (Option C):** When `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN` are set, download the Excel from the issue attachment first. Resolve the sheet from Jira comment text (e.g. *Inc as full* → Excel tab *Inc as Fulll*). Parse **high-level scenarios** from Domino sheets: **Section** + **Summary**, Given/When/Then steps, **Mascot links** from QA/SIT mascot columns, and **`evidence_text`** from **SIT Jobs**, **QA Jobs**, **Comments**, and similar columns (Caption Monitoring stores Edit ID / Caption Group ID / Pegasus ID there). When Mascot links are absent, **`testplan_evidence.py`** extracts labeled IDs and UUIDs from `evidence_text` and mapped Jira acceptance criteria — rendered via **`render_testplan_evidence()`**.

**Report wording:** In Coverage summary use **acceptance criteria** (not AC) and **Given When Then** (not GWT). **GWT completeness is content-based** — detect `Given` / `When` / `Then` inside any step column (`Step Summary`, `Test Steps`, etc.) via `scripts/testplan_gwt.py` (optional colons; common typos like `Than:` normalized to `Then`); do not require QMetry column names. Set `{{TESTPLAN_NOTE}}` from cache `testPlanSummaryNote` when present. Build test plan placeholders with **`scripts/coverage_report_helpers.build_testplan_report_fields()`** — includes `{{TESTPLAN_ROWS}}` (Evidence via `render_testplan_evidence()`), `{{LADR_TRACEABILITY_BLOCK}}`, and `{{TESTPLAN_GAPS_LIST}}`. Always call **`apply_report_ui_enhancements(html)`** before write.

When `status` is `referenced_not_local`, set `{{TESTPLAN_COVERAGE_PCT}}` to **Pending**, populate `{{TESTPLAN_NOTE}}` with the referenced filename and sheet (not "no QMetry attachment"). When `status` is `no_testplan`, use **`NA`**.

### Step 5b: Map requirements to PR diff (automated)

After prefetch and test plan caches exist:

```bash
python scripts/map_requirements_to_diff.py {ISSUE-KEY}
```

Writes `reports/.cache/{ISSUE-KEY}-mapping.json` with per-requirement `codeStatus`, `devTestStatus`, `matchedFiles`, `confidence` (**high** only when `matchedFiles` non-empty; else medium/low with **`evidenceNote`**), **suggestedTestCases** for partial keyword overlap, and per-PR **`devTests`** (comma-separated pytest module names from `diffNames`, e.g. `test_passport_manager.py`).

When **`prs` is empty** but **`branchCompare.files`** exists, mapping uses branch file paths, commit messages, and domain hints (caption/passport/status codes) for scoring.

Use mapping scores as the baseline for **Dev code coverage %** and **Dev unit/integration test coverage %** in the report. Agent may override with narrative when diff evidence is clearer than token overlap, or via **`--analysis` JSON** (`reqCoveragePct`, `devCoveragePct`, `reqCoverageDetail`, `devCoverageDetail`).

### Step 6: Map requirements to code, tests, test plan, and dev/QA ownership

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

**Test plan cross-check** (when test plan cache exists)

For each requirement `R{n}` with mapped test case(s) `TC{x}`:

| Field | Values |
|-------|--------|
| **Test plan status** | Covered / Partial / Missing / N/A |
| **Test plan alignment** | Aligned / Partial / Gap / Unverified |

- Compare test case **Then** steps against PR implementation and dev tests.
- Flag **Gap** when test plan expects behavior absent from PR diff.
- Flag **Partial** when code exists but dev tests missing for dev-owned logic covered by the test case.
- List unmapped test cases and uncovered AC in `{{TESTPLAN_GAPS_LIST}}`.

### Step 7: Compute coverage percentages

**Dev code coverage %** (same formula as requirement → code mapping)

```
score(R) = 1.0 if Implemented
         = 0.5 if Partial
         = 0.0 if Missing
         = excluded if N/A

requirement_coverage_pct = round(100 * sum(score) / count(scored items), 1)
```

**Requirements mapped**

Count of Jira acceptance criteria extracted and scored: `{{REQ_MAPPED_SUMMARY}}` e.g. `3/3 acceptance criteria`. Detail: `{{REQ_MAPPED_DETAIL}}` e.g. `R1–R3`. Class `{{REQ_MAPPED_CLASS}}`: `metric-good` when all acceptance criteria mapped, `metric-warn` if partial story scope.

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

**Generic builder:** `build_coverage_report.py` calls **`ci_coverage_report_fields(issue_key)`** in `coverage_report_helpers.py`, which merges `ciCoverage` from each PR in `{KEY}-prefetch.json` (Sonar/Codecov/pytest-cov) and maps to template placeholders **`{{CI_LINE_COVERAGE}}`**, **`{{CI_BRANCH_COVERAGE}}`**, **`{{CI_LINE_NOTE}}`**, **`{{CI_BRANCH_NOTE}}`**, **`{{CI_LINE_CLASS}}`**, **`{{CI_BRANCH_CLASS}}`**. Re-extracts from cached `sonarComment` / `codecovComment` / `checks` when `ciCoverage` is empty. Do not hand-set legacy keys `lineCoverage` / `branchCoverage` on the replacements dict.

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

**Coverage summary cards (8 total)** in three groups — **Implementation & tests:** Dev code coverage, Dev unit/integration test coverage, Requirements mapped. **QA & release risk:** Test plan acceptance criteria coverage, QA scope remaining, Open gaps. **CI pipeline coverage:** CI line coverage, CI branch coverage. Do **not** include Test requirement coverage or PR traceability in the summary. Use restrained coloring: white cards, colored left border + value only (`metric-good` / `metric-warn` / `metric-fail` / `metric-na` / `metric-neutral`).

**Report terminology:** Never abbreviate **acceptance criteria** as AC or **Given When Then** as GWT in user-facing report text. Use `4/4 acceptance criteria` not `4/4 AC`; use `5/5 full Given When Then` not `5/5 full GWT`.

**Test plan section** (section 4 in report) — placeholders:

| Placeholder | Value |
|-------------|-------|
| `{{TESTPLAN_COVERAGE_PCT}}` | e.g. `100.0%` or `NA` |
| `{{TESTPLAN_COVERAGE_CLASS}}` | metric-* tier class |
| `{{TESTPLAN_COVERAGE_DETAIL}}` | completeness summary |
| `{{TESTPLAN_NOTE}}` | note-box when no attachment/auth error; empty otherwise |
| `{{TESTPLAN_ROWS}}` | `<tr>` — TC ID, Scenario (Section · Summary), Mapped Req, Given When Then, Alignment, Evidence (Mascot links or Edit/Job/Request UUIDs) |
| `{{LADR_TRACEABILITY_BLOCK}}` | When Confluence LADR is linked: HTML table tying each L1…Ln to Excel test case IDs (use `build_testplan_report_fields()` or `render_ladr_traceability_block()`) |
| `{{TESTPLAN_GAPS_LIST}}` | `<li>` uncovered acceptance criteria, unmapped LADR items, unmapped TCs, misalignments |

**Test plan acceptance criteria coverage %**

Scores against **Jira acceptance criteria plus LADR/Confluence ESS scenarios** when LADR is linked or referenced. Semantic mapping matches ESS `task` + `status` in test case Summary/Then steps (not only keyword overlap on Jira AC text).

```
testplan_score(R or L) = 1.0 if ≥1 mapped test case with full Given/When/Then
                         = 0.5 if mapped but incomplete GWT or weak match
                         = 0.0 if no mapped test case
                         = excluded if N/A

testplan_coverage_pct = round(100 * sum(scores) / count(scored items), 1)
```

Use **`NA`** when no attachment and no local fallback. Populate `{{TESTPLAN_COVERAGE_DETAIL}}` from cache `coverage.coverageDetail`, e.g. `12 test cases · 12/12 full Given When Then · 13/14 LADR scenarios covered · 3/3 Jira acceptance criteria covered · Jira attachment`.

Apply `{{TESTPLAN_COVERAGE_CLASS}}` using the same tiers as dev coverage.

**Verdict** — factor test plan gaps and open-gap severity:

- **Fail** when `gap_summary` contains **one or more High gaps** — match `[1-9]\d* High`, **not** the substring `High` inside `0 High · N Med` (builder uses this regex in `_verdict()`).
- **Fail** when dev code coverage < 50%.
- **Pass with gaps** when test plan < 85% or dev code < 100%, or only Medium gaps.
- **Pass** when requirements, dev tests, and test plan alignment are satisfactory.

### Step 8: Build HTML report

**Preferred (generic builder):**

```bash
python scripts/map_requirements_to_diff.py {ISSUE-KEY}
python scripts/build_coverage_report.py {ISSUE-KEY}
```

Optional narrative overrides: `python scripts/build_coverage_report.py {ISSUE-KEY} --analysis reports/.cache/{ISSUE-KEY}-analysis.json`

Analysis JSON keys (optional): `verdict`, `verdictClass`, `verdictRationale`, `reqCoveragePct`, `reqCoverageDetail`, `devCoveragePct`, `devCoverageDetail`, `qaScopeSummary`, `openGapsSummary`, `openGapsClass`, `openGapsDetail`, `gapsList`, `devCoveredList`, `qaHandoffList`, `correctlyImplementedList`, `assumptionsList`, `actionsList`, `requirementRows`, `prNote`, `storyTitle`.

The builder fills: Jira readiness block, **quick links** (`build_quick_links()` — Jira, SharePoint test plan, PR(s), **Confluence** via `collect_confluence_page_links()` from confluence cache, test plan cache, Jira remote/wiki text, and any `reports/.cache/{KEY}*.json` including analysis), release score, split test plan metrics, **§4 Dev vs QA ownership** via `build_qa_ownership_fields()` — requirements with **QA scope None** (dev unit/integration **Covered**) are **not** listed for QA test-plan execution; only TCs mapped to QA-scoped `R*` appear in handoff, **Linked PR rows** (file counts + **auto Dev tests** from prefetch/mapping), **branch-compare rows** when no PRs, **CI pipeline cards** via `ci_coverage_report_fields()` (re-extracts Sonar/Codecov/pytest-cov; `finalize_ci_coverage()` for branch display), auto traceability rows from mapping cache (unless `requirementRows` in analysis), unmapped TCs, suggested mappings. **`{{PR_NOTE}}`** from analysis or `build_branch_compare_pr_note()`. Always runs `apply_report_ui_enhancements()` before write (idempotent if called twice).

**Manual / agent-refined:** Read [report-template.html](report-template.html) and replace all `{{PLACEHOLDER}}` tokens. New placeholders: `{{CACHE_META}}`, `{{QUICK_LINKS}}`, `{{JIRA_READINESS_BLOCK}}`, `{{RELEASE_SCORE_BLOCK}}`, `{{TESTPLAN_SPLIT_METRICS}}`, `{{UNMAPPED_TC_BLOCK}}`, `{{SUGGESTED_MAPPING_BLOCK}}`.

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
| `{{REQ_MAPPED_SUMMARY}}`, `{{REQ_MAPPED_DETAIL}}`, `{{REQ_MAPPED_CLASS}}` | e.g. `3/3 acceptance criteria`, `R1–R3`, `metric-good` |
| `{{OPEN_GAPS_SUMMARY}}`, `{{OPEN_GAPS_DETAIL}}`, `{{OPEN_GAPS_CLASS}}` | e.g. `2 High · 2 Med`, brief note, `metric-warn` |
| `{{QA_SCOPE_SUMMARY}}` | e.g. `2 items` — use `metric-neutral` card (no purple) |
| `{{QA_HANDOFF_LIST}}` | `<li>` items — QA scenarios not covered by dev tests |
| `{{DEV_COVERED_LIST}}` | `<li>` items — what dev unit/integration tests already prove |
| `{{CI_LINE_COVERAGE}}`, `{{CI_BRANCH_COVERAGE}}` | Percent or **`NA`** when no PR/CI |
| `{{CI_LINE_NOTE}}`, `{{CI_BRANCH_NOTE}}` | e.g. `Source: codecov` or `No PR for MSC-204417; develop branch only` |
| `{{CI_LINE_CLASS}}`, `{{CI_BRANCH_CLASS}}` | `metric-na` when unavailable; else tier class if numeric |
| `{{PR_NOTE}}` | Optional `<div class="note-box">…</div>` when no PR linked; empty string if PR exists |
| `{{PR_ROWS}}` | HTML `<tr>` rows for section 2 — use `coverage_report_helpers.render_pr_rows()` |

**Section 2 Linked PR(s)** — seven columns:

| Column | Content |
|--------|---------|
| PR | Link `#number` to GitHub PR URL |
| Repo | `org/repo` |
| State | open / MERGED / CLOSED from `gh pr view` |
| Title | PR title from `gh pr view --json title` |
| Files | `{n} files ({m} test)` from `diffNames` in prefetch |
| Dev tests | Pytest modules from PR diff — **auto** via `format_dev_tests_summary()` / `{KEY}-mapping.json` `prs[].devTests`; shows `—` when no `test_*.py` / `*_test.py` in diff |
| CI status | `gh pr checks` — **N/A** when empty or prefetch failed |

```python
from coverage_report_helpers import render_pr_rows, render_pr_rows_from_prefetch

# Default — Dev tests filled from caches (no manual dict required):
rows = render_pr_rows_from_prefetch("MSC-205625")

# Optional override for richer labels after agent review:
rows = render_pr_rows_from_prefetch("MSC-205625", dev_tests_by_number={161: "TestDominoPassportRouting, passport_manager unit tests"})
```

`build_coverage_report.py` sets `{{PR_ROWS}}` using `render_pr_rows_from_prefetch()` without overrides unless you pass `dev_tests_by_number` into `build_report()`.

Never put PR title or dev tests in the CI status column.

**Report UI enhancements (mandatory before write)**

After replacing all placeholders, pass the HTML through **`coverage_report_helpers.apply_report_ui_enhancements(html)`** — idempotent; upgrades legacy tooltip CSS to **v8** and ownership block to **v3**.

The helper adds (idempotent — safe to call on template or post-builder HTML):

- **Info-icon tooltips** (`i` badge) on:
  - Report title (h1), meta fields (Jira, Status, Type, Generated), cache freshness, quick links
  - Jira input readiness panel + each checklist item (AC, PR, test plan, Confluence)
  - Verdict banner, all §1–§8 section h2 headings, summary group titles
  - All Coverage summary metric labels (including **Release readiness score** and CI line/branch)
  - Test plan note-box, Jira/LADR split metrics, §4 Dev vs QA ownership (section h2, intro callout icon at **end** of paragraph, metric cards)
  - Table column headers: Linked PR(s) (7 cols), test plan, LADR trace, **requirements traceability** (§5 — **QA scope** and **Evidence** open **left** to avoid table clip)
  - Review panels (gaps, unmapped TCs, suggested mappings, correctly implemented); LADR block uses `ladr-section-lead` (not `section-lead-with-tip`)
- **Linked PR table** — body via `render_pr_rows()` / `render_pr_rows_from_prefetch()`; plain `<thead>` upgraded by `inject_pr_table_header_tooltips()`
- **Tooltip layout fix v8** — `overflow: visible` on sections/tables. PR/trace **last two columns** open left; metric cards in summary flip **up**; **§4 ownership (v3)** — section title tooltip below header; intro tooltip **below** top-right icon; **Covered by dev tests** / **QA handoff** tooltips **below** icon inside each card (`metric-qa` aligns tooltip **left** so columns do not overlap)
- **Requirements traceability (§5)** — `trace-section-lead`, `trace-table`, evidence file list + `evidenceNote` when no path match (`inject_trace_section_styles` v2)
- **Footer attribution** — `Generated by msc-dev-code-and-qa-test-coverage-validator · Developed by Mayur Gunjal` (`REPORT_AGENT_NAME`, `REPORT_DEVELOPER` in `coverage_report_helpers.py`)

Tooltip copy lives in `SUMMARY_METRIC_INFO`, `PR_TABLE_COLUMN_INFO`, `SECTION_HEADER_INFO`, `OWNERSHIP_LABEL_INFO`, `TRACE_TABLE_COLUMN_INFO`, etc. in `scripts/coverage_report_helpers.py` — extend those dicts when adding new UI labels; do not duplicate tooltip HTML in reports.

**Quick links:** `build_quick_links()` uses `confluence_requirements.collect_confluence_page_links()` — do not rely only on `confluence.json` `pages[].webUrl`; inferred LADR without a fetched page may still resolve a wiki URL from Jira text or `{KEY}-analysis.json`.

Do **not** hand-roll tooltip CSS in generated reports; always call the helper once before write. Base template `report-template.html` uses `.report-section { overflow: visible; }` — do not revert to `overflow: hidden`.

**Regression tests:** `python -m pytest scripts/test_report_ui_enhancements.py scripts/test_quick_links.py scripts/test_qa_scope_handoff.py scripts/test_confluence_requirements.py -q`

```python
from coverage_report_helpers import apply_report_ui_enhancements, render_pr_rows_from_prefetch

html = filled_template  # all {{PLACEHOLDER}} tokens replaced
html = apply_report_ui_enhancements(html)
```

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

### Step 9: Write output

Skip file write when `--no-write` or `writeReport: false` in manifest/defaults (chat summary only).

**Before write:** ensure `apply_report_ui_enhancements(html)` has been applied (Step 8).

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

`@msc-dev-code-and-qa-test-coverage-validator {KEY} --from-cache --auto`

Optional: also write `reports/<ISSUE-KEY>-<TIMESTAMP>.md` if the user asks for markdown.

Optional: add a Jira comment summary via `addCommentToJiraIssue` when `--post-jira` or `postJiraComment: true`.

## Quality bar

- Every requirement row must have evidence or an explicit **Missing** reason.
- Every scored requirement must have **Owner**, **Dev tier**, **Dev test status**, and **QA scope** — no blank dev/QA columns.
- Separate **dev code coverage**, **dev unit/integration test coverage**, and **CI line coverage** in prose and tables.
- Explicitly list what dev unit/integration tests cover vs what QA must still verify.
- When a test plan is attached, show AC coverage % and test-case ↔ requirement ↔ PR alignment.
- Flag PRs that implement code without dev tests for dev-owned AC items.
- Flag AC items implemented in code but contradicting the Jira description.
- Redact secrets and tokens from evidence citations.

## Additional resources

- **Primary report format:** [report-template.html](report-template.html)
- Markdown reference (optional): [report-template.md](report-template.md)
- Worked example: [examples.md](examples.md)
- GitHub / CI coverage commands: [references/github-coverage.md](references/github-coverage.md)
- Dev vs QA test scope rules: [references/dev-qa-test-scope.md](references/dev-qa-test-scope.md)
- Jira test plan validation: [references/jira-testplan-validation.md](references/jira-testplan-validation.md)
- Confluence / LADR requirements: [references/confluence-ladr-requirements.md](references/confluence-ladr-requirements.md)
- Run modes, flags, cache, prefetch: [references/run-options.md](references/run-options.md)
- Auto-approve Allow/Run prompts: [references/auto-approve-setup.md](references/auto-approve-setup.md)
- Workspace defaults template: [validator.defaults.example.json](validator.defaults.example.json)
