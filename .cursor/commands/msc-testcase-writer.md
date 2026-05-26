# MSC testcase writer

Generate QMetry-format test cases from Jira story `$ARGUMENTS` on wbdstreaming.atlassian.net.

1. Follow skill `.cursor/skills/jira-story-testcases/SKILL.md`.
2. Fetch Jira via Atlassian MCP (`getJiraIssue`).
3. Show full draft for user approval before writing files.
4. After approval: write `testcases/{KEY}-testcases.tsv` and run:
   `python scripts/generate_qmetry_excel.py testcases/{KEY}-testcases.tsv`
5. Output: `testcases/{KEY}-testcases.xlsx`
