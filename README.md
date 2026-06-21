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

### 5. Auto-run allowlist (coverage validator — recommended)

```bash
python scripts/install_coverage_validator_permissions.py
```

Cursor **Settings → Agents → Auto-Run → Allowlist**. Details: [.cursor/skills/coverage-validator/references/auto-approve-setup.md](.cursor/skills/coverage-validator/references/auto-approve-setup.md).

### 6. Run an agent

```text
/msc-testcase-writer MSC-204417
/msc-dev-code-and-qa-test-coverage-validator MSC-204417
```

See [Configuration](#configuration) for optional workspace defaults, Jira credentials, and local test plans.

---

## Configuration

All config files are **local** (gitignored where noted). The coverage validator merges options in this order: **inline flags → manifest → `.coverage-validator.defaults.json`**.

### Config files at a glance

| File | Required | Gitignored | Used by |
|------|----------|------------|---------|
| `.coverage-validator.defaults.json` | No | Yes | Coverage validator |
| `.env` | Recommended | Yes | Jira attachment download (`fetch_jira_testplan.py`) |
| `reports/.cache/{KEY}-manifest.json` | Auto-created | Partial | Per-issue run options + `lastReportFile` |
| `testplans/*.xlsx` | Sometimes | Yes (contents) | Local SharePoint-referenced test plans |
| `~/.cursor/permissions.json` | Recommended | N/A (user home) | Auto-run MCP + shell without prompts |

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

### `.env` (Jira API — test plan attachments)

```bash
cp .env.example .env
python scripts/verify_jira_credentials.py MSC-204417
```

Set credentials from `.env.example` so `fetch_jira_testplan.py` can download Excel attachments from Jira when present.

### Environment variables

| Variable | Overrides | Purpose |
|----------|-----------|---------|
| `COVERAGE_TEST_REPO_ROOT` | `testRepoRoot` in defaults | Local service clone for optional `--execute-tests` pytest run |

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
| `gh` CLI | No | No | **Yes** |
| Python + `openpyxl` | Yes | No | Yes |
| Permissions allowlist | Optional | Optional | **Recommended** |
| `.env` Jira token | No | No | **Recommended** (attachments) |
| `.coverage-validator.defaults.json` | No | No | **Optional** |
| `testplans/` Excel | No | No | **Sometimes** |
| `testRepoRoot` | No | No | **Optional** (`--execute-tests`) |

---

## Outputs

### Coverage validator

| Output | Path |
|--------|------|
| HTML report | `reports/{ISSUE-KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html` |
| Caches | `reports/.cache/{ISSUE-KEY}-*.json` |
| Optional pytest cache | `reports/.cache/{ISSUE-KEY}-test-execution.json` |

**Report highlights (content only — tooltips v22 unchanged):**

- **Summary** — QA scope remaining, Open gaps (condensed when ≥5 gaps)
- **§3** — Honest `testPlanSummaryNote`; **No execution evidence** for `workspace_generated` plans
- **§4** — Dev vs QA handoff; dev-covered list omits misleading **None** badge
- **§5** — FR / NFR / Process badges; symbol/pytest evidence; **NFR SIT validation capped at medium**
- **§6** — Correctly implemented + Gaps (SIT, CI, test plan)
- **§7** — Assumptions (max 3 bullets)
- **§8** — Dev and QA recommended actions

Content vs tooltips: [.cursor/skills/coverage-validator/references/content-vs-tooltips.md](.cursor/skills/coverage-validator/references/content-vs-tooltips.md)

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
| `fetch_jira_testplan.py` | Download/parse test plan; honest summary note |
| `prefetch_coverage_inputs.py` | Batch `gh` PR view/diff/checks → cache |
| `map_requirements_to_diff.py` | Requirement → PR diff; FR/NFR; NFR SIT evidence caps |
| `mapping_evidence.py` | Symbol + pytest-name scoring for §5 Evidence |
| `cache_freshness.py` | Stale mapping detection; auto-remap on build |
| `execute_pr_tests.py` | Optional local pytest on PR test files |
| `build_coverage_report.py` | HTML report; `--rerun`; `--execute-tests` |
| `install_coverage_validator_permissions.py` | Merge allowlist into `~/.cursor/permissions.json` |
| `sync_pegasus_qa_agents_lab.py` | Publish from TestCursor maintainer workspace |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Duplicate `/msc-*` suggestions | Use agents only; skills are workflow folders |
| Test plan 0% but xlsx existed | Re-run `write_testcase_excel.py {KEY}` then `fetch_jira_testplan.py` |
| Test plan **Pending** / `referenced_not_local` | Add Excel under `testplans/`; set `testPlanPath` in defaults |
| §5 SIT AC shows **high** or FR instead of NFR | Re-run `map_requirements_to_diff.py` + `build_coverage_report.py --rerun` |
| Open gaps note condensed | When ≥5 gaps, card summarizes — see **§6** for full list |
| CI coverage **NA** | Link PR; re-run prefetch |
| `--execute-tests` skipped | Set `testRepoRoot` or `COVERAGE_TEST_REPO_ROOT` to local clone |
| §6 Correctly implemented tooltip hidden under banner | Regenerate report — `TOOLTIP_LAYOUT_FIX_CSS` opens review-panel h3 tooltips below the icon |
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
