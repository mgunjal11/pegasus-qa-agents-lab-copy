# Pegasus QA Agents Lab

A centralized lab for **AI-driven QA agents** on the WBD Media Supply Chain (MSC) Jira instance and GitHub. Clone this repo, open it in [Cursor](https://cursor.com), and use three agents for test design, coverage validation, and bug filing.

**Jira:** [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net) · **Project:** MSC · **Repo:** [github.com/mgunjal11/pegasus-qa-agents-lab](https://github.com/mgunjal11/pegasus-qa-agents-lab)

---

## Agents

| # | Agent | What it does | How to invoke |
|---|--------|--------------|---------------|
| 1 | **msc-testcase-writer** | Jira (+ LADR when linked) → QMetry FF2.0 Excel, Given/When/Then | `@msc-testcase-writer MSC-204417` |
| 2 | **msc-dev-code-and-qa-test-coverage-validator** | Jira AC + LADR + test plan vs PR; §5 **FR/NFR** badges; §7 brief assumptions; QA/Open gaps cards; §4 dev-covered omits None badge; §6/§8 auto content; tooltips v22 | `@msc-dev-code-and-qa-test-coverage-validator MSC-204417` |
| 3 | **msc-jira-bug** | Drafts MSC Bug tickets; creates only after your approval | `@msc-jira-bug` + describe the defect |

**One registration per agent** — workflow skills live under `.cursor/skills/coverage-validator/` and `bug-filing/` (not duplicate slash entries).

---

## Quick start (new teammate)

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
pip install -r requirements.txt
```

### 3. Atlassian MCP (all three agents)

Cursor **Settings → MCP** → enable **Atlassian** (`user-atlassian`) and sign in for `wbdstreaming.atlassian.net`.

### 4. GitHub CLI (coverage validator only)

```bash
gh auth login
gh auth status
```

### 5. Auto-run permissions (coverage validator — recommended)

```bash
python scripts/install_coverage_validator_permissions.py
```

Cursor **Settings → Agents → Auto-Run → Allowlist**.

Details: [.cursor/skills/coverage-validator/references/auto-approve-setup.md](.cursor/skills/coverage-validator/references/auto-approve-setup.md)

### 6. Jira API credentials (test plan download — recommended)

```bash
cp .env.example .env
python scripts/verify_jira_credentials.py MSC-204417
```

### 7. Workspace defaults (optional)

```bash
cp .cursor/skills/coverage-validator/validator.defaults.example.json .coverage-validator.defaults.json
```

### 8. Local test plans (SharePoint references)

Place Excel under `testplans/` when Jira comments reference SharePoint — see [testplans/README.md](testplans/README.md).

---

## Agent setup comparison

| Requirement | testcase-writer | jira-bug | coverage-validator |
|-------------|-----------------|----------|-------------------|
| Atlassian MCP | Yes | Yes | Yes |
| `gh` CLI | No | No | **Yes** |
| Python + `openpyxl` | Yes | No | Yes |
| Permissions allowlist | Optional | Optional | **Recommended** |
| `.env` Jira token | No | No | **Recommended** (attachments) |
| `testplans/` Excel | No | No | **Sometimes** |

---

## Coverage validator outputs

| Output | Path |
|--------|------|
| HTML report | `reports/{ISSUE-KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html` |
| Cache (reuse runs) | `reports/.cache/{ISSUE-KEY}-*.json` |

### Report highlights (HTML)

- **Summary — QA scope remaining** — count with scope breakdown (e.g. `4 E2E · 1 Manual`); note lists Jira/LADR ids and linked test plan case ids (`{{QA_SCOPE_DETAIL}}`)
- **Summary — Open gaps** — severity count from `build_implementation_gaps_list()`; note via `build_open_gaps_detail()` — named gaps when **&lt; 5** total; theme summary + **see §6 for full list** when **≥ 5** (not tooltip copy)
- **§3** — Honest `testPlanSummaryNote`; Evidence **No execution evidence** for locally generated QMetry plans (`workspace_generated`)
- **§4** — **Covered by dev tests** omits **None** badge (internal `qaScope: none` unchanged); QA handoff skips dev-covered requirements and limits execute-test-plan bullets to QA-scoped TCs
- **§5** — Jira `R*` + LADR `L*` trace rows; **FR** / **NFR** / **Process** badge on every ID (`classify_requirement_type()` — SIT validation → NFR; product behavior → FR); LADR badge on `L*`; **Dev tests** = Covered / Partial / Missing only; **QA scope** column still shows **None** when dev-covered
- **§6** — Auto **Correctly implemented** (Jira + LADR with PR evidence); **Gaps** (test plan, partial code/dev tests, SIT validation, CI)
- **§7** — **Assumptions** — max 3 bullets (open questions, mapping review, scoring note)
- **§8** — Separate **Dev** and **QA** recommended action lists
- **Tooltips v22** — hover `i` on labels unchanged; metric/card **content** edits use data builders only (see `references/content-vs-tooltips.md`)

Full workflow: [.cursor/skills/coverage-validator/SKILL.md](.cursor/skills/coverage-validator/SKILL.md)

---

## Testcase writer outputs

| Output | Path |
|--------|------|
| Deliverable | `testcases/{KEY}-testcases.xlsx` only |
| Internal source | `reports/.cache/{KEY}-testcases-source.tsv` |

Skill: [.cursor/skills/jira-story-testcases/SKILL.md](.cursor/skills/jira-story-testcases/SKILL.md)

When coverage validator finds **no Jira test plan**, it auto-invokes testcase writer (`write_testcase_excel.py`) in `--auto --write` mode.

---

## Example commands

```text
@msc-testcase-writer MSC-204417

@msc-dev-code-and-qa-test-coverage-validator MSC-204417

@msc-jira-bug Promo normalization fails on DN HD ingest — QA
```

Reuse cached data:

```text
@msc-dev-code-and-qa-test-coverage-validator MSC-204417 --from-cache --auto
```

Prefetch GitHub (one shell, multiple PRs):

```bash
python scripts/prefetch_coverage_inputs.py MSC-204417 \
  --pr https://github.com/wbd-msc/org-repo/pull/1 \
  --pr https://github.com/wbd-msc/other-repo/pull/2
```

---

## Repository layout

```
.cursor/
  agents/              # msc-testcase-writer, msc-dev-code-and-qa-test-coverage-validator, msc-jira-bug
  skills/
    jira-story-testcases/     # QMetry testcase workflow
    coverage-validator/       # Coverage validator workflow (not a duplicate slash command)
    bug-filing/               # MSC bug filing workflow (agent: msc-jira-bug)
  permissions.json
scripts/
  write_testcase_excel.py     # Cache TSV → QMetry FF2.0 xlsx
  fetch_jira_testplan.py
  build_coverage_report.py
testcases/             # Generated xlsx (gitignored contents)
testplans/             # Local Excel when Jira references SharePoint
reports/               # HTML reports + .cache/
docs/                  # Optional notes (primary deliverables are HTML + xlsx)
```

---

## Scripts reference

| Script | Purpose |
|--------|---------|
| `write_testcase_excel.py` | `reports/.cache/{KEY}-testcases-source.tsv` → `testcases/{KEY}-testcases.xlsx` |
| `prepare_testcase_writer_context.py` | `jira_and_ladr` vs `jira_only` mode |
| `fetch_jira_testplan.py` | Download/parse test plan; honest summary note |
| `prefetch_coverage_inputs.py` | Batch `gh` PR view/diff/checks → cache (`--mode from-cache` to reuse) |
| `build_coverage_report.py` | HTML report; calls §6/§7 builders in `coverage_report_helpers.py` |
| `map_requirements_to_diff.py` | Requirement → PR diff mapping; `classify_requirement_type()` → FR/NFR on §5 rows |
| `install_coverage_validator_permissions.py` | Merge allowlist into `~/.cursor/permissions.json` |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Duplicate `/msc-*` suggestions | Use agents only; skills are `coverage-validator` / `bug-filing` folders |
| Test plan 0% but xlsx existed | Re-run `write_testcase_excel.py {KEY}` then `fetch_jira_testplan.py` |
| `â€"` garbled text in §6 Gaps | Regenerate report — `build_implementation_gaps_list()` uses UTF-8 em dash |
| Test plan **Pending** / `referenced_not_local` | Add Excel under `testplans/` |
| Open gaps note lists partial gap themes only | When **≥ 5** gaps, card note is condensed — open **§6 Implementation review** for the full gap list |
| §5 shows FR on SIT validation AC | Regenerate report — SIT/staging validation AC should show **NFR** (validation); remap with latest `map_requirements_to_diff.py` |
| CI coverage **NA** | Link PR; re-run prefetch; Sonar PR comment fallback when logs expired |

---

## Maintainers (publish from TestCursor)

```bash
python scripts/sync_pegasus_qa_agents_lab.py --publish
cd pegasus-qa-agents-lab
git add -A && git commit -m "Sync agents, skills, docs" && git push origin main
```

---

## License

Internal WBD MSC QA tooling — use within your team's policies.
