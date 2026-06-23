#!/usr/bin/env python3
"""Write Cursor permissions files for Req2Release auto-approve."""
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from jira_env import ensure_env_from_example  # noqa: E402

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
        "python scripts/preflight_coverage_validator.py",
        "mkdir",
    ],
}

EXAMPLE = {
    "_comment": "Merge into ~/.cursor/permissions.json. Requires Agents → Auto-Run = Allowlist.",
    **PERMS,
}

root = Path(__file__).resolve().parents[1]
env_status = ensure_env_from_example(root)
if env_status.get("created"):
    print(env_status["message"])
    print(f"  Edit: {env_status['envPath']}")
elif not (root / ".env").exists():
    print(env_status.get("message", "Create .env with Jira credentials"))
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
