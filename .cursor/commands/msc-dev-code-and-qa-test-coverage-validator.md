# MSC dev code and QA test coverage validator

Validate the Jira issue in `$ARGUMENTS` against linked GitHub PR(s) and attached Excel test plan (Jira attachment).

## Required behavior (no manual Allow/Run stops)

1. **Default mode: `--auto --write`** — end-to-end without mid-run confirmation.
2. **Step 0** — merge inline flags → manifest → `.coverage-validator.defaults.json`.
3. **Jira** — one parallel MCP batch: `getJiraIssue` (include `attachment` field) + `getJiraIssueRemoteIssueLinks` + `getConfluencePage` when LADR/wiki links present (single turn). Persist attachment metadata in `reports/.cache/{KEY}-jira.json` (include `remoteLinks` / `confluenceLinks` with `pageId`).
4. **Confluence / LADR** — one shell: `python scripts/fetch_confluence_requirements.py {KEY} --from-jira-cache` (reads description **and** Jira remote wiki links; cache `{KEY}-confluence.json`).
5. **Test plan** — one shell: `python scripts/fetch_jira_testplan.py {KEY} --from-jira-cache` (Jira AC + LADR mapping; Evidence = Mascot or Edit/Caption Group/Pegasus/Job IDs from SIT Jobs); use **`build_testplan_report_fields()`** for §3 HTML placeholders.
6. **GitHub** — one shell only: `python scripts/prefetch_coverage_inputs.py {KEY} --pr {URL}` or `python scripts/fetch_coverage_github.py {KEY} --repo {repo}`; if cache is fresh use `--from-cache` and skip gh.
7. **Requirement mapping** — one shell: `python scripts/map_requirements_to_diff.py {KEY}` → `reports/.cache/{KEY}-mapping.json` (scores R1…Rn vs PR diff + test files; per-PR `devTests` summary).
8. **Report** — prefer generic builder: `python scripts/build_coverage_report.py {KEY}` (caches + mapping; auto **CI** `{{CI_*}}` placeholders; auto **Dev tests** in Linked PR table; `apply_report_ui_enhancements()`). Refine via `--analysis` JSON if needed.
9. **Never** issue multiple separate `gh` calls when a script or cache can be used.
10. Follow skill `.cursor/skills/msc-dev-code-and-qa-test-coverage-validator/SKILL.md` completely (dev/QA sections, test plan validation, LADR traceability, Jira readiness block, HTML report).
11. **Report UI** — `apply_report_ui_enhancements()` in `scripts/coverage_report_helpers.py` adds info-icon tooltips on **all** report labels (header, readiness, release score, summary metrics, tables, review panels); tooltip layout v5; footer — Developed by Mayur Gunjal. Builder already calls this — do not skip on manual HTML edits.

If PR URL is unknown, use manifest/repo from defaults; search once via prefetch script, not repeated gh calls.

**Multiple PRs:** pass each URL in one prefetch invocation:
`python scripts/prefetch_coverage_inputs.py {KEY} --pr {URL1} --pr {URL2}`

**No linked PR (develop-only):** when manifest has `compareBranch` (e.g. `develop`):
`python scripts/fetch_coverage_github.py {KEY} --repo {org}/{repo} --compare develop`
Mapping uses `branchCompare.files` from prefetch; report shows branch-compare PR note and CI **NA** with honest note.

**Jira input quality:** See `docs/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Jira-Template.docx`.

Output: `reports/{KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html` (local timezone) and save `reports/.cache/{KEY}-manifest.json` with `lastReportFile`.
