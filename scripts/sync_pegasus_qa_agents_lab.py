#!/usr/bin/env python3
"""Copy agents, skills, scripts into pegasus-qa-agents-lab for GitHub publish."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "pegasus-qa-agents-lab"
HOME_CURSOR = Path.home() / ".cursor"

COPY_DIRS = [
    (ROOT / ".cursor/skills/jira-story-testcases", LAB / ".cursor/skills/jira-story-testcases"),
    (ROOT / ".cursor/skills/msc-dev-code-and-qa-test-coverage-validator", LAB / ".cursor/skills/msc-dev-code-and-qa-test-coverage-validator"),
    (HOME_CURSOR / "skills/jira-msc-bug", LAB / ".cursor/skills/jira-msc-bug"),
]

COPY_FILES = [
    (ROOT / ".cursor/agents/msc-testcase-writer.md", LAB / ".cursor/agents/msc-testcase-writer.md"),
    (ROOT / ".cursor/agents/msc-dev-code-and-qa-test-coverage-validator.md", LAB / ".cursor/agents/msc-dev-code-and-qa-test-coverage-validator.md"),
    (HOME_CURSOR / "agents/msc-jira-bug.md", LAB / ".cursor/agents/msc-jira-bug.md"),
    (ROOT / ".cursor/commands/msc-dev-code-and-qa-test-coverage-validator.md", LAB / ".cursor/commands/msc-dev-code-and-qa-test-coverage-validator.md"),
    (ROOT / "requirements.txt", LAB / "requirements.txt"),
    (ROOT / "AGENTS.md", LAB / "AGENTS.md"),
    (ROOT / ".env.example", LAB / ".env.example"),
]

SCRIPTS = [
    "generate_qmetry_excel.py",
    "coverage_report_timestamp.py",
    "coverage_report_helpers.py",
    "ci_coverage.py",
    "fetch_coverage_github.py",
    "fetch_jira_testplan.py",
    "fetch_confluence_requirements.py",
    "confluence_requirements.py",
    "test_confluence_requirements.py",
    "jira_env.py",
    "prefetch_coverage_inputs.py",
    "install_coverage_validator_permissions.py",
    "generate_coverage_validator_ppt.py",
    "verify_jira_credentials.py",
    "testplan_evidence.py",
    "testplan_gwt.py",
    "test_testplan_evidence.py",
    "test_gwt_parsing.py",
    "test_mascot_links.py",
    "test_pr_rows.py",
    "test_report_ui_enhancements.py",
    "test_quick_links.py",
    "test_qa_scope_handoff.py",
    "patch_trace_section_template.py",
    "test_summary_metric_info.py",
    "patch_report_footer.py",
    "patch_report_template.py",
    "map_requirements_to_diff.py",
    "build_coverage_report.py",
    "generate_jira_template_for_coverage_validator.py",
    "test_confluence_remote_links.py",
    "test_map_requirements_to_diff.py",
    "test_ci_template_fields.py",
    "test_ci_coverage.py",
    "test_dev_tests_pr_column.py",
    "regen_msc204417_report.py",
    "regen_msc205625_report.py",
    "build_msc195138_report.py",
    "ppt_report_from_html.py",
    "sync_pegasus_qa_agents_lab.py",
]

PERMISSIONS = {
    "_comment": "Merge into ~/.cursor/permissions.json. Cursor Settings → Agents → Auto-Run → Allowlist.",
    "mcpAllowlist": [
        "user-atlassian:getJiraIssue",
        "user-atlassian:getJiraIssueRemoteIssueLinks",
        "user-atlassian:getConfluencePage",
        "user-atlassian:getAccessibleAtlassianResources",
        "user-atlassian:searchJiraIssuesUsingJql",
        "user-atlassian:getJiraIssueTypeMetaWithFields",
        "user-atlassian:getJiraProjectIssueTypesMetadata",
        "user-atlassian:createJiraIssue",
        "user-atlassian:addCommentToJiraIssue",
    ],
    "terminalAllowlist": [
        "gh",
        "python scripts/prefetch_coverage_inputs.py",
        "python scripts/fetch_coverage_github.py",
        "python scripts/fetch_jira_testplan.py",
        "python scripts/fetch_confluence_requirements.py",
        "python scripts/map_requirements_to_diff.py",
        "python scripts/build_coverage_report.py",
        "python scripts/generate_qmetry_excel.py",
        "python scripts/install_coverage_validator_permissions.py",
        "mkdir",
    ],
}

def remove_stale(lab: Path) -> None:
    """Remove renamed agent/skill paths and old guide deck."""
    stale_paths = [
        lab / ".cursor/skills/msc-code-coverage-validator",
        lab / ".cursor/agents/msc-code-coverage-validator.md",
        lab / ".cursor/commands/msc-code-coverage-validator.md",
        lab / "docs/MSC-Code-Coverage-Validator-Guide.pptx",
    ]
    for path in stale_paths:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()


def main() -> None:
    LAB.mkdir(parents=True, exist_ok=True)
    remove_stale(LAB)
    for src, dst in COPY_DIRS:
        if not src.exists():
            raise SystemExit(f"Missing source: {src}")
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    for src, dst in COPY_FILES:
        if not src.exists():
            if src.name == ".env.example":
                continue
            raise SystemExit(f"Missing source: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    (LAB / "scripts").mkdir(exist_ok=True)
    for name in SCRIPTS:
        src = ROOT / "scripts" / name
        if src.exists():
            shutil.copy2(src, LAB / "scripts" / name)
    (LAB / "testcases").mkdir(exist_ok=True)
    (LAB / "reports").mkdir(exist_ok=True)
    (LAB / "reports" / ".cache").mkdir(exist_ok=True)
    (LAB / "testcases" / ".gitkeep").write_text("", encoding="utf-8")
    (LAB / "reports" / ".gitkeep").write_text("", encoding="utf-8")
    (LAB / "reports" / ".cache" / ".gitkeep").write_text("", encoding="utf-8")
    (LAB / "testplans").mkdir(exist_ok=True)
    (LAB / "testplans" / ".gitkeep").write_text("", encoding="utf-8")
    write_testplans_readme(LAB)
    (LAB / "docs").mkdir(exist_ok=True)
    (LAB / "docs" / ".gitkeep").write_text("", encoding="utf-8")
    (LAB / ".cursor" / "permissions.json").write_text(
        json.dumps({k: v for k, v in PERMISSIONS.items() if not k.startswith("_")}, indent=2) + "\n",
        encoding="utf-8",
    )
    (LAB / ".cursor" / "permissions.example.json").write_text(
        json.dumps(PERMISSIONS, indent=2) + "\n", encoding="utf-8",
    )
    write_commands(LAB)
    write_gitignore(LAB)
    write_agents_md(LAB)
    update_lab_readme(LAB)
    # README.md body is updated via update_lab_readme; full copy not used
    docs = LAB / "docs"
    docs.mkdir(exist_ok=True)
    ppt = ROOT / "docs" / "MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx"
    if not ppt.exists():
        ppt = ROOT / "reports" / "MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx"
    if ppt.exists():
        shutil.copy2(ppt, docs / ppt.name)
    print(f"Synced to {LAB.resolve()}")


def write_commands(lab: Path) -> None:
    cmds = lab / ".cursor" / "commands"
    cmds.mkdir(parents=True, exist_ok=True)
    (cmds / "msc-testcase-writer.md").write_text(
        """# MSC testcase writer

Generate QMetry-format test cases from Jira story `$ARGUMENTS` on wbdstreaming.atlassian.net.

1. Follow skill `.cursor/skills/jira-story-testcases/SKILL.md`.
2. Fetch Jira via Atlassian MCP (`getJiraIssue`).
3. Show full draft for user approval before writing files.
4. After approval: write `testcases/{KEY}-testcases.tsv` and run:
   `python scripts/generate_qmetry_excel.py testcases/{KEY}-testcases.tsv`
5. Output: `testcases/{KEY}-testcases.xlsx`
""",
        encoding="utf-8",
    )
    (cmds / "msc-jira-bug.md").write_text(
        """# MSC Jira bug filer

Draft and file an MSC Bug on wbdstreaming.atlassian.net from `$ARGUMENTS`.

1. Follow skill `.cursor/skills/jira-msc-bug/SKILL.md` and agent `.cursor/agents/msc-jira-bug.md`.
2. Search duplicates via JQL; fetch create metadata for MSC + Bug.
3. Show full draft (summary, description, field plan) — **wait for explicit approval**.
4. Create via `createJiraIssue` only after user approves.
5. Return issue key and browse URL.
""",
        encoding="utf-8",
    )


def write_agents_md(lab: Path) -> None:
    agents = lab / "AGENTS.md"
    agents.write_text(_AGENTS_MD, encoding="utf-8")


def update_lab_readme(lab: Path) -> None:
    """Refresh README and docs/README with renamed validator references."""
    replacements = [
        ("MSC-Code-Coverage-Validator-Guide.pptx", "MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx"),
        ("MSC Code Coverage Validator", "MSC Dev Code and QA Test Coverage Validator"),
        ("msc-code-coverage-validator", "msc-dev-code-and-qa-test-coverage-validator"),
    ]
    for rel in ("README.md", "docs/README.md"):
        path = lab / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in replacements:
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")


_AGENTS_MD = """# Pegasus QA Agents Lab

Three Cursor agents for MSC QA on [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net).

| Agent | Invoke | Output |
|-------|--------|--------|
| **msc-testcase-writer** | `@msc-testcase-writer MSC-1234` | `testcases/{KEY}-testcases.xlsx` (QMetry FF2.0) |
| **msc-dev-code-and-qa-test-coverage-validator** | `/msc-dev-code-and-qa-test-coverage-validator MSC-1234` | `build_coverage_report.py`; QA scope None when dev tests cover AC; Jira readiness green ✓ / red ✗; Confluence quick links; CI + Dev tests; tooltips v8 / §4 v3 |
| **msc-jira-bug** | `@msc-jira-bug` + defect description | MSC Bug in Jira (after explicit approval) |

## Skills

| Skill | Path |
|-------|------|
| QMetry test cases from Jira | `.cursor/skills/jira-story-testcases/SKILL.md` |
| Coverage vs PR + test plan | `.cursor/skills/msc-dev-code-and-qa-test-coverage-validator/SKILL.md` |
| MSC Bug filing | `.cursor/skills/jira-msc-bug/SKILL.md` |

Full teammate setup: [README.md](README.md)
"""


def write_testplans_readme(lab: Path) -> None:
    (lab / "testplans" / "README.md").write_text(_TESTPLANS_README, encoding="utf-8")


_TESTPLANS_README = """# Local test plans

Place QMetry / Domino Excel files here when a Jira story **references** a test plan in comments or SharePoint but does not attach the file (or you prefer a local copy).

## Example

Jira comment: *"Refer Inc as full sheet for Test plan and evidence"* → `Domino Test Plan.xlsx`, sheet **Inc as full**.

1. Copy the workbook to `testplans/Domino Test Plan.xlsx`
2. Optionally set `testPlanPath` / `testPlanSheet` in `.coverage-validator.defaults.json`
3. Re-run `/msc-dev-code-and-qa-test-coverage-validator {KEY}`

## Jira attachment

If the Excel is on the issue, set `.env` from `.env.example` so `fetch_jira_testplan.py` can download it automatically.
"""


def write_gitignore(lab: Path) -> None:
    (lab / ".gitignore").write_text(
        """# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Agent outputs (keep structure)
reports/*
!reports/.gitkeep
!reports/.cache/
reports/.cache/*
!reports/.cache/.gitkeep
testcases/*
!testcases/.gitkeep

# Secrets and local overrides
.env
.coverage-validator.defaults.json

# Local test plan workbooks (keep folder + README)
testplans/*
!testplans/.gitkeep
!testplans/README.md
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
