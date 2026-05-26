# Pegasus QA Agents Lab

A centralized lab for **AI-driven QA agents** on the WBD Media Supply Chain (MSC) Jira instance and GitHub. Clone this repo, open it in [Cursor](https://cursor.com), and use three agents for test design, coverage validation, and bug filing.

**Jira:** [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net) · **Project:** MSC

---

## Agents

| # | Agent | What it does | How to invoke |
|---|--------|--------------|---------------|
| 1 | **msc-testcase-writer** | Reads Jira user stories → QMetry FF2.0 test cases (Excel) | `@msc-testcase-writer MSC-204417` |
| 2 | **msc-code-coverage-validator** | Validates Jira AC vs GitHub PR/code; dev vs QA coverage report | `/msc-code-coverage-validator MSC-204417` |
| 3 | **msc-jira-bug** | Drafts MSC Bug tickets; creates after your approval | `@msc-jira-bug` + describe the defect |

Guide deck: run `python scripts/generate_coverage_validator_ppt.py` → `reports/MSC-Code-Coverage-Validator-Guide.pptx`

---

## Quick start

### 1. Clone and open in Cursor

```bash
git clone https://github.com/mgunjal11/pegasus-qa-agents-lab.git
cd pegasus-qa-agents-lab
cursor .
```

### 2. Python dependencies

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
pip install python-pptx           # optional — for PPT guide
```

### 3. Atlassian MCP (all agents)

1. Cursor **Settings → MCP** → enable **Atlassian** (user-atlassian).
2. Authenticate for `wbdstreaming.atlassian.net`.

### 4. GitHub CLI (coverage validator only)

```bash
gh auth login
gh auth status
```

### 5. Auto-run permissions (recommended)

```bash
python scripts/install_coverage_validator_permissions.py
```

Merge `.cursor/permissions.example.json` into `~/.cursor/permissions.json`.

Cursor **Settings → Agents → Auto-Run → Allowlist** (not “Ask every time”).

### 6. Optional defaults

Copy and edit for your repo / timezone:

```bash
cp .cursor/skills/msc-code-coverage-validator/validator.defaults.example.json .coverage-validator.defaults.json
```

Guide deck: `docs/MSC-Code-Coverage-Validator-Guide.pptx` — run `python scripts/generate_coverage_validator_ppt.py`

---

## Outputs

| Agent | Path |
|-------|------|
| Test cases | `testcases/{ISSUE-KEY}-testcases.xlsx` |
| Coverage report | `reports/{ISSUE-KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html` (7-card summary) |
| Coverage validator PPT | `docs/MSC-Code-Coverage-Validator-Guide.pptx` |
| Jira bug | Issue key + URL in chat (created in MSC project) |

Reports use **your laptop local timezone** (e.g. `IST`, `EST`).

---

## Repository layout

```
.cursor/
  agents/          # Subagent definitions (3 agents)
  commands/        # Slash commands
  skills/          # Detailed workflows per agent
  permissions.json # MCP + terminal allowlist
scripts/           # Excel generator, GitHub prefetch, permissions installer
testcases/         # Generated QMetry TSV/XLSX
reports/           # Coverage HTML reports + cache
```

---

## Example commands

```text
@msc-testcase-writer MSC-204417

/msc-code-coverage-validator MSC-204417 --auto --write

@msc-jira-bug Caption status not updating in Monitor after ESS V2 deploy — staging
```

Reuse cached GitHub/Jira data:

```text
/msc-code-coverage-validator MSC-204417 --from-cache --auto
```

---

## Prerequisites checklist

- [ ] Cursor IDE with Agents enabled
- [ ] Atlassian MCP authenticated
- [ ] `gh` CLI authenticated (coverage validator)
- [ ] Python 3.10+ with `openpyxl`
- [ ] Permissions allowlist installed

---

## License

Internal WBD MSC QA tooling — use within your team's policies.
