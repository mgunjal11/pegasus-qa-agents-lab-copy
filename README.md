# Pegasus QA Agents Lab

AI-driven QA agents for the WBD Media Supply Chain (MSC) on Jira and GitHub. Clone this repo, open it in [Cursor](https://cursor.com), and invoke agents for QMetry test design, Jira-to-PR coverage validation, and MSC bug filing.

| Resource | Link |
|----------|------|
| Jira | [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net) (project **MSC**) |
| Repository | [github.com/mgunjal11/pegasus-qa-agents-lab](https://github.com/mgunjal11/pegasus-qa-agents-lab) |

---

## Agents

| Agent | Purpose | Invoke |
|-------|---------|--------|
| **msc-testcase-writer** | Jira (+ LADR when linked) → QMetry FF2.0 Excel (Given/When/Then) | `@msc-testcase-writer MSC-204417` or `/msc-testcase-writer MSC-204417` |
| **msc-dev-code-and-qa-test-coverage-validator** | Jira AC + LADR + test plan vs PR; §5 FR/NFR; NFR SIT capped at medium; optional `--execute-tests` | `@msc-dev-code-and-qa-test-coverage-validator MSC-204417` or `/msc-dev-code-and-qa-test-coverage-validator MSC-204417` |
| **msc-jira-bug** | Draft MSC Bug tickets (creates only after approval) | `@msc-jira-bug` + defect description |

Workflow skills live under `.cursor/skills/` — they are **not** duplicate slash commands. Agent definitions: `.cursor/agents/`.

---

## Quick start

### 1. Clone and open in Cursor

```bash
git clone https://github.com/mgunjal11/pegasus-qa-agents-lab.git
cd pegasus-qa-agents-lab
cursor .
```

Open **this repo** as the workspace root.

### 2. Python

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### 3. Atlassian MCP (all agents)

Cursor **Settings → MCP** → enable **Atlassian** (`user-atlassian`) and sign in for `wbdstreaming.atlassian.net`.

### 4. GitHub CLI (coverage validator)

```bash
gh auth login
gh auth status
```

### 5. Jira API credentials (coverage validator — when test plan is a Jira attachment)

If the story has a **test plan Excel attached on the Jira issue** (not only a SharePoint link), Python scripts download the file via the **Jira REST API**. That requires a local `.env` file — Atlassian MCP alone does not download attachment binaries.

```bash
cp .env.example .env
# Edit .env — see Configuration → Jira REST API credentials
python scripts/verify_jira_credentials.py MSC-204417
```

Skip this step when the test plan is only referenced in a comment/SharePoint (use `testplans/` instead) or when the validator auto-generates cases via `@msc-testcase-writer`.

### 6. Auto-run allowlist (coverage validator — recommended)

```bash
python scripts/install_coverage_validator_permissions.py
```

Cursor **Settings → Agents → Auto-Run → Allowlist**. Details: [.cursor/skills/coverage-validator/references/auto-approve-setup.md](.cursor/skills/coverage-validator/references/auto-approve-setup.md).

### 7. Run an agent

```text
/msc-testcase-writer MSC-204417
/msc-dev-code-and-qa-test-coverage-validator MSC-204417
```

See [Configuration](#configuration) for workspace defaults, **Jira REST credentials**, local test plans, and optional pytest settings.

---

## Configuration

All config files are **local** (gitignored where noted). The coverage validator merges options in this order: **inline flags → manifest → `.coverage-validator.defaults.json`**.

### Config files at a glance

| File | Required | Gitignored | Used by |
|------|----------|------------|---------|
| `.env` | **When Jira has test plan attachment** | Yes | Jira attachment download, Confluence REST fallback |
| `.coverage-validator.defaults.json` | No | Yes | Coverage validator defaults |
| `reports/.cache/{KEY}-manifest.json` | Auto-created | Partial | Per-issue run options + `lastReportFile` |
| `testplans/*.xlsx` | Sometimes | Yes (contents) | SharePoint-referenced test plans (no Jira attachment) |
| `~/.cursor/permissions.json` | Recommended | N/A (user home) | Auto-run MCP + shell without prompts |

### Jira and Atlassian authentication

Two complementary setups — both may be needed for full coverage validation:

| Method | Where configured | Used for |
|--------|------------------|----------|
| **Atlassian MCP** | Cursor **Settings → MCP** → `user-atlassian` (OAuth / sign-in) | Agent reads Jira issue text, comments, attachment **metadata**, remote Confluence links |
| **Jira REST API** | Repo root `.env` (`ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN`) | Python scripts **download** Excel attachments, verify auth, optional Confluence REST when not using MCP cache |

**MCP does not replace `.env` for attachment download.** When a QMetry/Domino workbook is attached to the Jira issue, `fetch_jira_testplan.py` calls the Jira REST API to fetch the binary file into `reports/.cache/{KEY}-testplan-files/`.

#### When `.env` Jira credentials are required

| Test plan source | `.env` needed? | What to do |
|------------------|----------------|------------|
| **Excel attached on Jira issue** | **Yes** | Set `.env` and run `verify_jira_credentials.py` |
| **SharePoint / comment link only** (no attachment) | No | Copy workbook to `testplans/`; set `testPlanPath` / `testPlanSheet` in defaults |
| **No test plan on Jira** | No | Validator may invoke `@msc-testcase-writer` to generate `testcases/{KEY}-testcases.xlsx` |
| **Locally generated plan** (`workspace_generated`) | No | Uses `testcases/{KEY}-testcases.xlsx` from testcase writer |

Same credentials are used by `fetch_confluence_requirements.py` when fetching Confluence/LADR pages via REST (agents normally populate `{KEY}-jira.json` and `{KEY}-confluence.json` via MCP first).

#### Jira REST API credentials (`.env`)

**1. Create an Atlassian API token**

1. Sign in at [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net).
2. Open [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
3. **Create API token** — copy the token immediately (shown once).

Use your **WBD Atlassian account email** (the address you use to log into Jira), not a service account, unless your team provides one.

**2. Create `.env` from the example**

```bash
cp .env.example .env
```

**3. Set required variables**

| Variable | Required | Description |
|----------|----------|-------------|
| `ATLASSIAN_EMAIL` | **Yes** | Your Atlassian account email (e.g. `you@wbd.com`) |
| `ATLASSIAN_API_TOKEN` | **Yes** | API token from [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens) |

Optional aliases (same values — scripts accept either name):

| Variable | Alias for |
|----------|-----------|
| `JIRA_EMAIL` | `ATLASSIAN_EMAIL` |
| `JIRA_API_TOKEN` | `ATLASSIAN_API_TOKEN` |

Example `.env` (never commit this file):

```bash
ATLASSIAN_EMAIL=you@wbd.com
ATLASSIAN_API_TOKEN=ATATT3xFfGF0...your-token-here
```

**4. Verify credentials**

```bash
python scripts/verify_jira_credentials.py MSC-204417
```

Expected success output includes `"ok": true`, your `issueKey`, and `attachmentCount` ≥ 1 when the issue has Excel attached. If auth works but `attachmentCount` is 0, attach the test plan on Jira or use `testplans/` for a local copy.

**5. Security**

- `.env` is listed in `.gitignore` — **never commit** tokens to GitHub.
- Prefer `.env` in the repo root (same folder as `scripts/`).
- Shell exports override `.env` only when the variable is already set in the environment before `load_dotenv()` runs.

**Scripts that use Jira REST auth**

| Script | Purpose |
|--------|---------|
| `fetch_jira_testplan.py` | Download Jira attachment → parse QMetry/Domino sheet |
| `verify_jira_credentials.py` | Test email + token against a live issue |
| `fetch_confluence_requirements.py` | Confluence REST fallback (same token) |
| `upload_jira_testplan.py` | Optional — upload local Excel to a Jira issue |

Implementation: `scripts/jira_env.py` (`load_dotenv`, Basic auth header).

### `.coverage-validator.defaults.json`

Copy the example and edit for your team:

```bash
cp .cursor/skills/coverage-validator/validator.defaults.example.json .coverage-validator.defaults.json
```

| Key | Type | Description |
|-----|------|-------------|
| `repo` | string | Default GitHub repo (`org/service`) for branch-only runs |
| `mode` | string | `interactive` \| `auto` — slash commands default to `--auto --write` |
| `searchPrIfMissing` | bool | Search GitHub for PR when Jira has no PR URL |
| `writeReport` | bool | Write HTML report after validation |
| `useCache` | bool | Reuse fresh `reports/.cache/` files |
| `cacheMaxAgeHours` | number | Max cache age before refetch (default 24) |
| `postJiraComment` | bool | Post summary to Jira (default false) |
| `timezone` | string | IANA timezone, e.g. `Asia/Kolkata` |
| `timezoneLabel` | string | Report timestamp label, e.g. `IST` |
| `validateTestPlan` | bool | Parse and score attached/local test plan |
| `testPlanPath` | string | Local Excel path, e.g. `testplans/Domino Test Plan.xlsx` |
| `testPlanSheet` | string | Worksheet name, e.g. `Inc as full` |
| `testPlanFilename` | string | Display name when Jira references SharePoint |
| `testRepoRoot` | string | Absolute or workspace-relative path to a **local clone** of the service repo — enables `build_coverage_report.py {KEY} --execute-tests` |

Example:

```json
{
  "repo": "wbd-msc/your-service",
  "mode": "auto",
  "cacheMaxAgeHours": 24,
  "timezone": "Asia/Kolkata",
  "timezoneLabel": "IST",
  "testPlanPath": "testplans/Domino Test Plan.xlsx",
  "testPlanSheet": "Inc as full",
  "testRepoRoot": "C:/dev/your-service-clone"
}
```

### Other environment variables

| Variable | Overrides | Purpose |
|----------|-----------|---------|
| `COVERAGE_TEST_REPO_ROOT` | `testRepoRoot` in defaults | Local service clone for optional `--execute-tests` pytest run |
| `JIRA_EMAIL` / `JIRA_API_TOKEN` | — | Aliases for `ATLASSIAN_EMAIL` / `ATLASSIAN_API_TOKEN` |

### Per-issue manifest

After a successful coverage run, `reports/.cache/{KEY}-manifest.json` stores:

- `issueKey`, `prUrls`, `repo`, `mode`, `cacheMaxAgeHours`
- `lastReportFile` — path to latest HTML report
- `timezoneLabel`

Reuse a prior run:

```text
/msc-dev-code-and-qa-test-coverage-validator MSC-204417 --from-cache --auto
```

### Local test plans (`testplans/`)

When Jira **references** SharePoint/Domino Excel but does not attach the file, copy the workbook locally. See [testplans/README.md](testplans/README.md).

### Cursor permissions allowlist

`python scripts/install_coverage_validator_permissions.py` merges MCP and shell patterns into `~/.cursor/permissions.json`. Lab copy: [.cursor/permissions.example.json](.cursor/permissions.example.json).

---

## Agent setup comparison

| Requirement | testcase-writer | jira-bug | coverage-validator |
|-------------|-----------------|----------|-------------------|
| Atlassian MCP | Yes | Yes | Yes |
| `.env` Jira token (`ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN`) | No | No | **Yes when test plan is Jira attachment** |
| `gh` CLI | No | No | **Yes** |
| Python + `openpyxl` | Yes | No | Yes |
| Permissions allowlist | Optional | Optional | **Recommended** |
| `.coverage-validator.defaults.json` | No | No | **Optional** |
| `testplans/` Excel | No | No | **When SharePoint link only** (no attachment) |
| `testRepoRoot` | No | No | **Optional** (`--execute-tests`) |

---

## Outputs

### Coverage validator

| Output | Path |
|--------|------|
| HTML report | `reports/{ISSUE-KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html` |
| Caches | `reports/.cache/{ISSUE-KEY}-*.json` |
| Optional pytest cache | `reports/.cache/{ISSUE-KEY}-test-execution.json` |

### Coverage report sections

Each HTML report has eight numbered sections. **Section content** comes from data builders (`coverage_report_helpers.py`, `map_requirements_to_diff.py`, etc.). **Info-icon tooltips** (layout v22) are injected by `apply_report_ui_enhancements()` — change content via builders only; do not edit tooltip strings when updating report text. See [content-vs-tooltips.md](.cursor/skills/coverage-validator/references/content-vs-tooltips.md).

| Section | Highlights |
|---------|------------|
| **Summary** | QA scope remaining; Open gaps card (condensed when ≥5 gaps) |
| **§3 Test plan** | Honest `testPlanSummaryNote`; **No execution evidence** for `workspace_generated` plans |
| **§4 Dev vs QA** | Handoff list; dev-covered rows omit misleading **None** badge in bullets |
| **§5 Traceability** | FR / NFR / Process badges; Evidence shows 2 paths + 1 test; **click +N more** to expand all files/tests; NFR SIT capped at **medium** |
| **§6 Implementation review** | Correctly implemented list + Gaps (SIT, CI, test plan) |
| **§7 Assumptions** | Max 3 short bullets |
| **§8 Recommended actions** | Separate Dev and QA action lists |

Full workflow: [.cursor/skills/coverage-validator/SKILL.md](.cursor/skills/coverage-validator/SKILL.md)

### Testcase writer

| Output | Path |
|--------|------|
| Deliverable | `testcases/{KEY}-testcases.xlsx` only |
| Internal source | `reports/.cache/{KEY}-testcases-source.tsv` |

Skill: [.cursor/skills/jira-story-testcases/SKILL.md](.cursor/skills/jira-story-testcases/SKILL.md)

When the coverage validator finds **no Jira test plan** (`no_testplan`), it auto-invokes the testcase writer in `--auto --write` mode.

---

## Example commands

```text
/msc-testcase-writer MSC-204417

/msc-dev-code-and-qa-test-coverage-validator MSC-204417

/msc-jira-bug Promo normalization fails on DN HD ingest — QA
```

Prefetch GitHub (one shell, multiple PRs):

```bash
python scripts/prefetch_coverage_inputs.py MSC-204417 \
  --pr https://github.com/wbd-msc/org-repo/pull/1 \
  --pr https://github.com/wbd-msc/other-repo/pull/2
```

Optional local pytest (requires `testRepoRoot` or `COVERAGE_TEST_REPO_ROOT`):

```bash
python scripts/build_coverage_report.py MSC-204417 --execute-tests
```

Force remap when upstream caches changed:

```bash
python scripts/build_coverage_report.py MSC-204417 --rerun
```

---

## Repository layout

```
.cursor/
  agents/              # Agent definitions (invoke with @ or /)
  skills/
    jira-story-testcases/
    coverage-validator/
    bug-filing/
  permissions.json     # Example allowlist (install merges to ~/.cursor/)
scripts/               # Python pipeline (see Scripts reference)
testcases/             # Generated xlsx (gitignored contents)
testplans/             # Local Excel when Jira references SharePoint
reports/               # HTML reports + .cache/
docs/
```

---

## Scripts reference

| Script | Purpose |
|--------|---------|
| `write_testcase_excel.py` | Cache TSV → `testcases/{KEY}-testcases.xlsx` (QMetry FF2.0) |
| `prepare_testcase_writer_context.py` | `jira_and_ladr` vs `jira_only` mode |
| `fetch_confluence_requirements.py` | LADR/Confluence → `{KEY}-confluence.json` |
| `fetch_jira_testplan.py` | Download Jira attachment / parse local plan; honest summary note |
| `verify_jira_credentials.py` | Verify `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN` against a Jira issue |
| `upload_jira_testplan.py` | Upload local Excel test plan to a Jira issue (optional) |
| `prefetch_coverage_inputs.py` | Batch `gh` PR view/diff/checks → cache |
| `map_requirements_to_diff.py` | Requirement → PR diff; FR/NFR; NFR SIT evidence caps |
| `mapping_evidence.py` | Symbol + pytest-name scoring; `rank_matched_files()` |
| `test_trace_evidence.py` | Unit tests for compact §5 Evidence display |
| `cache_freshness.py` | Stale mapping detection; auto-remap on build |
| `execute_pr_tests.py` | Optional local pytest on PR test files |
| `build_coverage_report.py` | HTML report; `--rerun`; `--execute-tests` |
| `install_coverage_validator_permissions.py` | Merge allowlist into `~/.cursor/permissions.json` |
| `sync_pegasus_qa_agents_lab.py` | Publish from TestCursor maintainer workspace |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Jira credentials missing` / HTTP 401 on test plan fetch | Create `.env` from `.env.example`; set `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN`; run `verify_jira_credentials.py {KEY}` |
| Test plan **Pending** / attachment not downloaded | Confirm Excel is **attached** on Jira (not link-only); verify token; re-run `fetch_jira_testplan.py {KEY} --from-jira-cache` |
| Test plan **Pending** / `referenced_not_local` | No Jira attachment — add Excel under `testplans/`; set `testPlanPath` in defaults |
| Test plan 0% but xlsx existed | Re-run `write_testcase_excel.py {KEY}` then `fetch_jira_testplan.py` |
| Duplicate `/msc-*` suggestions | Use agents only; skills are workflow folders |
| §5 SIT AC shows **high** or FR instead of NFR | Re-run `map_requirements_to_diff.py` + `build_coverage_report.py --rerun` |
| Open gaps note condensed | When ≥5 gaps, card summarizes — see **§6** for full list |
| CI coverage **NA** | Link PR; re-run prefetch |
| `--execute-tests` skipped | Set `testRepoRoot` or `COVERAGE_TEST_REPO_ROOT` to local clone |
| §6 Correctly implemented tooltip hidden under banner | Regenerate report — review-panel h3 tooltips open below icon (`TOOLTIP_LAYOUT_FIX_CSS`) |
| §5 Evidence shows only "+N more" with no expand | Regenerate report — click **+N more** expands via `<details>`; `_summarize_trace_evidence()` in `coverage_report_helpers.py` |
| §5 Evidence lists too many files by default | Expected — default view is 2 paths + 1 test; expand **+N more** for full list; full path on hover |
| Garbled em dash in §6 | Regenerate report (UTF-8 HTML) |

---

## Maintainers

Publish from the TestCursor workspace:

```bash
python scripts/sync_pegasus_qa_agents_lab.py --publish
cd pegasus-qa-agents-lab
git add -A && git status
git commit -m "Sync agents, skills, scripts, and README"
git push origin main
```

**Do not** edit tooltip copy (`SUMMARY_METRIC_INFO`, `apply_report_ui_enhancements()` injection) when changing report content — use data builders only.

---

## License

Internal WBD MSC QA tooling — use within your team's policies.
