# MSC code coverage validator

Validate the Jira issue in `$ARGUMENTS` against linked GitHub PR(s) and attached QMetry test plan.

## Required behavior (no manual Allow/Run stops)

1. **Default mode: `--auto --write`** — end-to-end without mid-run confirmation.
2. **Step 0** — merge inline flags → manifest → `.coverage-validator.defaults.json`.
3. **Jira** — one parallel MCP batch: `getJiraIssue` (include `attachment` field) + `getJiraIssueRemoteIssueLinks` (single turn). Persist attachment metadata in `reports/.cache/{KEY}-jira.json`.
4. **Test plan** — one shell: `python scripts/fetch_jira_testplan.py {KEY} --from-jira-cache` (Jira attachment download, comment sheet name, Section · Summary scenarios, Mascot links in Evidence); use `coverage_report_helpers.py` for `{{TESTPLAN_ROWS}}`; skip with `--skip-testplan` or fresh cache.
5. **GitHub** — one shell only: `python scripts/prefetch_coverage_inputs.py {KEY} --pr {URL}` or `python scripts/fetch_coverage_github.py {KEY} --repo {repo}`; if cache is fresh use `--from-cache` and skip gh.
6. **Never** issue multiple separate `gh` calls when a script or cache can be used.
7. Follow skill `.cursor/skills/msc-code-coverage-validator/SKILL.md` completely (dev/QA sections, test plan validation, HTML report).

If PR URL is unknown, use manifest/repo from defaults; search once via prefetch script, not repeated gh calls.

Output: `reports/{KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html` (local timezone, e.g. `MSC-204417-05-26-2026-14-30-52-IST.html`) and save `reports/.cache/{KEY}-manifest.json` with `lastReportFile`.
