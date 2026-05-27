# Pegasus QA Agents Lab

A centralized lab for **AI-driven QA agents** on the WBD Media Supply Chain (MSC) Jira instance and GitHub. Clone this repo, open it in [Cursor](https://cursor.com), and use three agents for test design, coverage validation, and bug filing.

**Jira:** [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net) · **Project:** MSC · **Repo:** [github.com/mgunjal11/pegasus-qa-agents-lab](https://github.com/mgunjal11/pegasus-qa-agents-lab)

---

## Agents

| # | Agent | What it does | How to invoke |
|---|--------|--------------|---------------|
| 1 | **msc-testcase-writer** | Reads Jira user stories → QMetry FF2.0 test cases (Excel, Given/When/Then) | `@msc-testcase-writer MSC-204417` |
| 2 | **msc-code-coverage-validator** | Validates Jira acceptance criteria vs GitHub PR, dev tests, attached QMetry test plan; HTML report with dev vs QA handoff | `/msc-code-coverage-validator MSC-204417` |
| 3 | **msc-jira-bug** | Drafts MSC Bug tickets; creates only after your approval | `@msc-jira-bug` + describe the defect |

**Coverage validator guide deck:** `python scripts/generate_coverage_validator_ppt.py` → `docs/MSC-Code-Coverage-Validator-Guide.pptx`

---

## Quick start (new teammate)

### 1. Clone and open in Cursor

```bash
git clone https://github.com/mgunjal11/pegasus-qa-agents-lab.git
cd pegasus-qa-agents-lab
cursor .
```

You must open **this repo** as the workspace — slash commands and scripts live under `.cursor/` and `scripts/` here.

### 2. Python

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
pip install python-pptx           # optional — coverage validator PPT only
```

### 3. Atlassian MCP (all three agents)

1. Cursor **Settings → MCP** → enable **Atlassian** (`user-atlassian`).
2. Sign in for `wbdstreaming.atlassian.net`.

If `@msc-jira-bug` works, this step is already done.

### 4. GitHub CLI (coverage validator only)

```bash
gh auth login
gh auth status
```

Required for PR diff, CI checks, and Codecov/Sonar metrics. Not needed for testcase writer or jira-bug.

### 5. Auto-run permissions (coverage validator — recommended)

The slash command `/msc-code-coverage-validator` runs end-to-end (`--auto --write`). To avoid repeated **Allow** / **Run** prompts:

```bash
python scripts/install_coverage_validator_permissions.py
```

Then in Cursor: **Settings → Agents → Auto-Run → Allowlist** (not “Ask every time”).

Details: [.cursor/skills/msc-code-coverage-validator/references/auto-approve-setup.md](.cursor/skills/msc-code-coverage-validator/references/auto-approve-setup.md)

### 6. Jira API credentials (test plan download — recommended)

For stories with **QMetry / Domino test plans attached in Jira**, copy credentials once:

```bash
cp .env.example .env
# Edit .env: ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN
python scripts/verify_jira_credentials.py MSC-204417
```

Create a token at [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens). Never commit `.env`.

### 7. Workspace defaults (optional)

```bash
cp .cursor/skills/msc-code-coverage-validator/validator.defaults.example.json .coverage-validator.defaults.json
```

Set `repo` (e.g. `wbd-msc/pegasus-ess`), `timezone` / `timezoneLabel`, and test plan paths. This file is gitignored.

### 8. Local test plans (when Jira references SharePoint)

Some stories say *“Refer Inc as full sheet”* and point to SharePoint. Place the Excel locally:

```
testplans/Domino Test Plan.xlsx
```

See [testplans/README.md](testplans/README.md).

---

## Agent setup comparison

| Requirement | testcase-writer | jira-bug | code-coverage-validator |
|-------------|-----------------|----------|-------------------------|
| Atlassian MCP | Yes | Yes | Yes |
| `gh` CLI | No | No | **Yes** |
| Python + `openpyxl` | Yes | No | Yes |
| Permissions allowlist | Optional | Optional | **Recommended** |
| `.env` Jira token | No | No | **Recommended** (attachments) |
| `testplans/` Excel | No | No | **Sometimes** (SharePoint refs) |

---

## Coverage validator outputs

| Output | Path |
|--------|------|
| HTML report | `reports/{ISSUE-KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html` |
| Cache (reuse runs) | `reports/.cache/{ISSUE-KEY}-*.json` |
| Guide PPT | `docs/MSC-Code-Coverage-Validator-Guide.pptx` |

Reports use **your laptop local timezone** (e.g. `IST`, `EST`) in the filename and header.

### Coverage summary (8 cards)

The HTML report includes three groups:

**Implementation & tests**

- Dev code coverage %
- Dev unit/integration test coverage %
- Requirements mapped (acceptance criteria count)

**QA & release risk**

- Test plan acceptance criteria coverage %
- QA scope remaining
- Open gaps

**CI pipeline**

- CI line coverage %
- CI branch coverage %

Full workflow: [.cursor/skills/msc-code-coverage-validator/SKILL.md](.cursor/skills/msc-code-coverage-validator/SKILL.md)

---

## Example commands

```text
@msc-testcase-writer MSC-204417

/msc-code-coverage-validator MSC-204417

@msc-jira-bug Caption status not updating in Monitor after ESS V2 deploy — staging
```

Reuse cached Jira/GitHub data (faster, fewer prompts):

```text
/msc-code-coverage-validator MSC-204417 --from-cache --auto
```

Warm cache only:

```bash
python scripts/prefetch_coverage_inputs.py MSC-204417 --repo wbd-msc/your-service --search-pr
python scripts/fetch_jira_testplan.py MSC-204417 --from-jira-cache
```

---

## Repository layout

```
.cursor/
  agents/              # msc-testcase-writer, msc-code-coverage-validator, msc-jira-bug
  commands/            # Slash commands (/msc-code-coverage-validator, …)
  skills/              # Detailed workflows per agent
  permissions.json     # Project MCP + terminal allowlist
  permissions.example.json
scripts/
  generate_qmetry_excel.py
  fetch_jira_testplan.py       # Jira attachment + QMetry/Domino parse
  jira_env.py                  # .env loader for Jira REST
  coverage_report_helpers.py   # HTML test plan rows
  prefetch_coverage_inputs.py  # Single-shot GitHub prefetch
  fetch_coverage_github.py
  install_coverage_validator_permissions.py
  verify_jira_credentials.py
  generate_coverage_validator_ppt.py
testcases/             # Generated QMetry TSV/XLSX (gitignored contents)
testplans/             # Local Excel when Jira references SharePoint
reports/               # HTML reports + .cache/
docs/                  # Generated PPT and guides
.env.example           # Template for Jira API (copy → .env)
```

---

## Scripts reference

| Script | Purpose |
|--------|---------|
| `generate_qmetry_excel.py` | TSV → QMetry FF2.0 `.xlsx` |
| `fetch_jira_testplan.py` | Download/parse test plan; write `reports/.cache/{KEY}-testplan.json` |
| `prefetch_coverage_inputs.py` | Batch `gh` PR view/diff/checks → cache |
| `fetch_coverage_github.py` | GitHub-only fetch |
| `coverage_report_timestamp.py` | Local TZ filename for reports |
| `install_coverage_validator_permissions.py` | Merge allowlist into `~/.cursor/permissions.json` |
| `verify_jira_credentials.py` | Test `.env` against a Jira issue |
| `generate_coverage_validator_ppt.py` | Management guide deck |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/msc-code-coverage-validator` not found | Open this repo in Cursor (not another folder) |
| Many Allow/Run prompts | Run `install_coverage_validator_permissions.py`; set Auto-Run → **Allowlist** |
| Test plan shows **Pending** / `referenced_not_local` | Add Excel under `testplans/` or set `testPlanPath` in `.coverage-validator.defaults.json` |
| Cannot download Jira attachment | Set `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN` in `.env` |
| CI coverage **NA** | Link a PR on the story, or pass `--pr URL`; ensure `gh auth status` |
| `@msc-jira-bug` works but validator does not | Add `gh`, Python, and steps 5–7 above |

---

## Prerequisites checklist

- [ ] Cursor IDE with Agents enabled
- [ ] This repo cloned and opened as workspace
- [ ] Atlassian MCP authenticated (`wbdstreaming.atlassian.net`)
- [ ] `gh` CLI authenticated (coverage validator)
- [ ] Python 3.10+ with `openpyxl` (`pip install -r requirements.txt`)
- [ ] `python scripts/install_coverage_validator_permissions.py` + Auto-Run **Allowlist**
- [ ] `.env` from `.env.example` (if stories use Jira test plan attachments)
- [ ] `.coverage-validator.defaults.json` with your default `repo` (optional)

---

## Maintainers (publish updates from TestCursor)

From the parent `TestCursor` workspace:

```bash
python scripts/sync_pegasus_qa_agents_lab.py
cd pegasus-qa-agents-lab
git add -A && git commit -m "Sync agents, skills, README" && git push origin main
```

---

## License

Internal WBD MSC QA tooling — use within your team's policies.
