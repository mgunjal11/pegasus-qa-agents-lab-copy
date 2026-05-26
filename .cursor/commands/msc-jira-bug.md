# MSC Jira bug filer

Draft and file an MSC Bug on wbdstreaming.atlassian.net from `$ARGUMENTS`.

1. Follow skill `.cursor/skills/jira-msc-bug/SKILL.md` and agent `.cursor/agents/msc-jira-bug.md`.
2. Search duplicates via JQL; fetch create metadata for MSC + Bug.
3. Show full draft (summary, description, field plan) — **wait for explicit approval**.
4. Create via `createJiraIssue` only after user approves.
5. Return issue key and browse URL.
