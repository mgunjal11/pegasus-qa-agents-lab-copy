# MSC dev code and QA test coverage validator

Validate the Jira issue in `$ARGUMENTS` against linked GitHub PR(s) and attached Excel test plan (Jira attachment).

## Required behavior (no manual Allow/Run stops)

1. **Default mode: `--auto --write`** — end-to-end without mid-run confirmation.
2. **Step 0** — merge inline flags → manifest → `.coverage-validator.defaults.json`.
3. **Jira** — one parallel MCP batch: `getJiraIssue` (include `attachment` field) + `getJiraIssueRemoteIssueLinks` + `getConfluencePage` when LADR/wiki links present (single turn). Persist attachment metadata in `reports/.cache/{KEY}-jira.json`.
4. **Confluence / LADR** — one shell: `python scripts/fetch_confluence_requirements.py {KEY} --from-jira-cache` (ESS milestones; cache `{KEY}-confluence.json`).
5. **Test plan** — one shell: `python scripts/fetch_jira_testplan.py {KEY} --from-jira-cache` (Jira AC + LADR mapping; Evidence = Mascot or Edit/Caption Group/Pegasus/Job IDs from SIT Jobs); use **`build_testplan_report_fields()`** for §3 HTML placeholders.
6. **GitHub** — one shell only: `python scripts/prefetch_coverage_inputs.py {KEY} --pr {URL}` or `python scripts/fetch_coverage_github.py {KEY} --repo {repo}`; if cache is fresh use `--from-cache` and skip gh.
7. **Never** issue multiple separate `gh` calls when a script or cache can be used.
8. Follow skill `.cursor/skills/msc-dev-code-and-qa-test-coverage-validator/SKILL.md` completely (dev/QA sections, test plan validation, LADR traceability, HTML report).
9. **Report UI** — before write, run HTML through `apply_report_ui_enhancements()` in `scripts/coverage_report_helpers.py` (info-icon tooltips; tooltip layout v5 — last two table columns anchor to th right edge, e.g. Dev tests / CI status; footer — Developed by Mayur Gunjal).

If PR URL is unknown, use manifest/repo from defaults; search once via prefetch script, not repeated gh calls.

Output: `reports/{KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html` (local timezone, e.g. `MSC-204417-05-26-2026-14-30-52-IST.html`) and save `reports/.cache/{KEY}-manifest.json` with `lastReportFile`.
