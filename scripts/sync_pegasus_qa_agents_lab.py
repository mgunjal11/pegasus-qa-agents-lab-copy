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
    (ROOT / ".cursor/skills/coverage-validator", LAB / ".cursor/skills/coverage-validator"),
    (ROOT / ".cursor/skills/bug-filing", LAB / ".cursor/skills/bug-filing"),
]

COPY_FILES = [
    (ROOT / ".cursor/agents/msc-testcase-writer.md", LAB / ".cursor/agents/msc-testcase-writer.md"),
    (ROOT / ".cursor/agents/msc-dev-code-and-qa-test-coverage-validator.md", LAB / ".cursor/agents/msc-dev-code-and-qa-test-coverage-validator.md"),
    (ROOT / ".cursor/agents/msc-jira-bug.md", LAB / ".cursor/agents/msc-jira-bug.md"),
    (ROOT / "requirements.txt", LAB / "requirements.txt"),
    (ROOT / "AGENTS.md", LAB / "AGENTS.md"),
    (ROOT / ".env.example", LAB / ".env.example"),
]

SCRIPTS = [
    "generate_qmetry_excel.py",
    "write_testcase_excel.py",
    "coverage_report_timestamp.py",
    "coverage_report_helpers.py",
    "ci_coverage.py",
    "fetch_coverage_github.py",
    "fetch_jira_testplan.py",
    "fetch_jira_story.py",
    "jira_story.py",
    "fetch_confluence_requirements.py",
    "confluence_requirements.py",
    "test_confluence_requirements.py",
    "jira_env.py",
    "prefetch_coverage_inputs.py",
    "install_coverage_validator_permissions.py",
    "verify_jira_credentials.py",
    "upload_jira_testplan.py",
    "preflight_coverage_validator.py",
    "coverage_validator_config.py",
    "testplan_evidence.py",
    "testplan_gwt.py",
    "test_testplan_evidence.py",
    "test_gwt_parsing.py",
    "test_mascot_links.py",
    "test_pr_rows.py",
    "test_report_ui_enhancements.py",
    "test_quick_links.py",
    "test_qa_scope_handoff.py",
    "test_implementation_review.py",
    "test_requirement_type.py",
    "test_nfr_validation_evidence.py",
    "test_trace_evidence.py",
    "mapping_evidence.py",
    "cache_freshness.py",
    "test_mapping_evidence.py",
    "test_cache_freshness.py",
    "test_verdict_mode.py",
    "test_preflight_coverage_validator.py",
    "test_coverage_pipeline_golden.py",
    "test_semantic_and_run_validator.py",
    "patch_trace_section_template.py",
    "test_summary_metric_info.py",
    "patch_report_footer.py",
    "patch_report_template.py",
    "map_requirements_to_diff.py",
    "semantic_mapping_boost.py",
    "run_coverage_validator.py",
    "build_coverage_report.py",
    "execute_pr_tests.py",
    "test_confluence_remote_links.py",
    "test_map_requirements_to_diff.py",
    "test_ci_template_fields.py",
    "test_ci_coverage.py",
    "prepare_testcase_writer_context.py",
    "test_prepare_testcase_writer_context.py",
    "generate_testcases_from_requirements.py",
    "test_generate_testcases_from_requirements.py",
    "test_fetch_jira_story.py",
    "test_fetch_jira_testplan_summary.py",
    "test_dev_tests_pr_column.py",
    "regen_msc204417_report.py",
    "regen_msc205625_report.py",
    "build_msc195138_report.py",
    "sync_pegasus_qa_agents_lab.py",
]

PERMISSIONS = {
    "_comment": "Merge into ~/.cursor/permissions.json. Cursor Settings â†’ Agents â†’ Auto-Run â†’ Allowlist.",
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
        "python scripts/preflight_coverage_validator.py",
        "python scripts/fetch_jira_story.py",
        "python scripts/run_coverage_validator.py",
        "python scripts/generate_testcases_from_requirements.py",
        "python scripts/execute_pr_tests.py",
        "python scripts/generate_qmetry_excel.py",
        "python scripts/write_testcase_excel.py",
        "python scripts/install_coverage_validator_permissions.py",
        "mkdir",
    ],
}

def remove_stale(lab: Path) -> None:
    """Remove renamed agent/skill paths and old guide deck."""
    stale_paths = [
        lab / ".cursor/skills/msc-code-coverage-validator",
        lab / ".cursor/skills/msc-dev-code-and-qa-test-coverage-validator",
        lab / ".cursor/skills/jira-msc-bug",
        lab / ".cursor/agents/msc-code-coverage-validator.md",
        lab / ".cursor/commands/msc-code-coverage-validator.md",
        lab / "docs/MSC-Code-Coverage-Validator-Guide.pptx",
        lab / "docs/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx",
        lab / "docs/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Directory-Guide.docx",
        lab / "reports/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx",
        lab / "MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx",
    ]
    for path in stale_paths:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()


def main() -> None:
    import sys

    keep_cursor = "--publish" in sys.argv
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
    copy_report_helpers(LAB)
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
    copy_lab_readme_templates(LAB)
    copy_github_workflow(LAB)
    copy_test_fixtures(LAB)
    # Lab nested inside TestCursor: drop .cursor so Cursor does not double-register agents/skills.
    if not keep_cursor and LAB.resolve().parent == ROOT.resolve():
        lab_cursor = LAB / ".cursor"
        if lab_cursor.exists():
            shutil.rmtree(lab_cursor)
        print(
            f"Synced to {LAB.resolve()} (lab .cursor removed — use TestCursor root .cursor; "
            "re-run with --publish before pushing lab repo)"
        )
    else:
        print(f"Synced to {LAB.resolve()}")


def write_commands(lab: Path) -> None:
    """Agents-only â€” slash commands duplicate agent entries in Cursor UI."""
    cmds = lab / ".cursor" / "commands"
    if cmds.exists():
        shutil.rmtree(cmds)


def write_agents_md(lab: Path) -> None:
    agents = lab / "AGENTS.md"
    agents.write_text(_AGENTS_MD, encoding="utf-8")


def copy_lab_readme_templates(lab: Path) -> None:
    """Copy maintainer-authored README templates (UTF-8)."""
    tpl = ROOT / "scripts" / "templates"
    pairs = [
        (tpl / "pegasus-qa-agents-lab-README.md", lab / "README.md"),
        (tpl / "pegasus-qa-agents-lab-docs-README.md", lab / "docs" / "README.md"),
    ]
    for src, dst in pairs:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def copy_report_helpers(lab: Path) -> None:
    src = ROOT / "scripts" / "report_helpers"
    dst = lab / "scripts" / "report_helpers"
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_github_workflow(lab: Path) -> None:
    src = ROOT / "scripts" / "templates" / "coverage-validator-ci.yml"
    if not src.exists():
        return
    dst_dir = lab / ".github" / "workflows"
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst_dir / "coverage-validator.yml")


def copy_test_fixtures(lab: Path) -> None:
    src = ROOT / "scripts" / "test_fixtures"
    dst = lab / "scripts" / "test_fixtures"
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


_AGENTS_MD = """# Pegasus QA Agents Lab

Three Cursor agents for MSC QA on [wbdstreaming.atlassian.net](https://wbdstreaming.atlassian.net).

| Agent | Invoke | Output |
|-------|--------|--------|
| **msc-testcase-writer** | `@msc-testcase-writer MSC-1234` | `testcases/{KEY}-testcases.xlsx` (QMetry FF2.0) |
| **msc-dev-code-and-qa-test-coverage-validator** | `@msc-dev-code-and-qa-test-coverage-validator MSC-1234` | HTML report; run `preflight_coverage_validator.py` first; §5 expandable Evidence; `verdictMode`; optional `--execute-tests` |
| **msc-jira-bug** | `@msc-jira-bug` + defect description | MSC Bug in Jira (after explicit approval) |

## Skills (workflow docs — not duplicate slash commands)

| Skill folder | Path |
|--------------|------|
| QMetry test cases | `.cursor/skills/jira-story-testcases/SKILL.md` |
| Coverage validator | `.cursor/skills/coverage-validator/SKILL.md` |
| MSC Bug filing | `.cursor/skills/bug-filing/SKILL.md` |

Full teammate setup: [README.md](README.md)
"""


def write_testplans_readme(lab: Path) -> None:
    (lab / "testplans" / "README.md").write_text(_TESTPLANS_README, encoding="utf-8")


_TESTPLANS_README = """# Local test plans

Place QMetry / Domino Excel files here when a Jira story **references** a test plan in comments or SharePoint but does not attach the file (or you prefer a local copy).

## Example

Jira comment: *"Refer Inc as full sheet for Test plan and evidence"* â†’ `Domino Test Plan.xlsx`, sheet **Inc as full**.

1. Copy the workbook to `testplans/Domino Test Plan.xlsx`
2. Optionally set `testPlanPath` / `testPlanSheet` in `.coverage-validator.defaults.json`
3. Re-run `@msc-dev-code-and-qa-test-coverage-validator {KEY}`

## Jira attachment

If the Excel is on the issue, set `.env` from `.env.example` so `fetch_jira_testplan.py` can download it automatically.

## No test plan on Jira

Coverage validator can auto-generate QMetry cases via `@msc-testcase-writer` and `write_testcase_excel.py`.
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
