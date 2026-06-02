#!/usr/bin/env python3
"""Write Cursor permissions files for msc-dev-code-and-qa-test-coverage-validator auto-approve."""
import json
from pathlib import Path

PERMS = {
    "mcpAllowlist": [
        "user-atlassian:getJiraIssue",
        "user-atlassian:getJiraIssueRemoteIssueLinks",
        "user-atlassian:getAccessibleAtlassianResources",
        "user-atlassian:searchJiraIssuesUsingJql",
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
        "mkdir",
    ],
}

EXAMPLE = {
    "_comment": "Merge into ~/.cursor/permissions.json. Requires Agents → Auto-Run = Allowlist.",
    **PERMS,
}

root = Path(__file__).resolve().parents[1]
(root / ".cursor" / "permissions.json").write_text(
    json.dumps(PERMS, indent=2) + "\n", encoding="utf-8"
)
(root / ".cursor" / "permissions.coverage-validator.example.json").write_text(
    json.dumps(EXAMPLE, indent=2) + "\n", encoding="utf-8"
)

user = Path.home() / ".cursor" / "permissions.json"
existing = {}
if user.exists():
    existing = json.loads(user.read_text(encoding="utf-8"))

for key in ("mcpAllowlist", "terminalAllowlist"):
    merged = list(existing.get(key, []))
    for item in PERMS[key]:
        if item not in merged:
            merged.append(item)
    existing[key] = merged

user.parent.mkdir(parents=True, exist_ok=True)
user.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
print(f"Project: {root / '.cursor' / 'permissions.json'}")
print(f"User:    {user}")
