# GitHub PR and CI coverage commands

Use **`gh` CLI** for all GitHub operations. If `gh auth status` fails, direct the user to `gh auth login`.

## PR metadata and diff

```bash
# Parse org/repo/number from URL first
gh pr view {number} --repo {org}/{repo} --json title,state,author,body,headRefName,baseRefName,files,commits,headRefOid
gh pr diff {number} --repo {org}/{repo}
gh pr diff {number} --repo {org}/{repo} --name-only
gh pr checks {number} --repo {org}/{repo}
```

## Find PR by Jira key

When org/repo is known:

```bash
gh search prs "MSC-205866" --repo wbd-msc/{repo} --state open,closed --limit 10
gh pr list --repo {org}/{repo} --search "MSC-205866 in:title,body" --state all
```

## CI line coverage sources

### 1. Check run summaries

```bash
gh pr checks {number} --repo {org}/{repo}
gh api repos/{org}/{repo}/commits/{head_sha}/check-runs --jq '.check_runs[] | {name, conclusion, output_title, output_summary}'
```

Look for check names containing: `codecov`, `coverage`, `sonar`, `pytest`, `test`.

### 2. Codecov PR comment

```bash
gh api repos/{org}/{repo}/issues/{number}/comments --jq '.[] | select(.user.login | test("codecov"; "i")) | .body' | head -1
```

Typical patterns: `Coverage: 87.2%`, `Patch coverage: 92%`.

### 3. SonarQube

Sources parsed by `scripts/ci_coverage.py` (`parse_sonar_text`, quality-gate log JSON, measures JSON):

- PR comment: `95.30% Coverage (94.50% Estimated after merge)`
- PR comment (Sonar bot markdown): `Code Coverage (Estimated after PR merge) - `62.6%``
- Check run `output_summary` on Sonar-named checks
- Quality-gate `new_coverage` / `new_branch_coverage` in CI build job logs

If the org uses SonarQube checks, read `output_summary` from the Sonar check run. Do not guess project keys.

### 4. Workflow run logs (fallback)

```bash
gh run list --repo {org}/{repo} --branch {headRefName} --limit 5
gh run view {run_id} --repo {org}/{repo} --log | rg -i "coverage|TOTAL|lines covered"
```

### 5. Artifacts (when published)

```bash
gh run download {run_id} --repo {org}/{repo} -n coverage-report
```

Then parse `coverage.xml`, `lcov.info`, or HTML summary if present.

### 6. When CI shows NA but an older report had numbers

| Cause | What happened |
|-------|----------------|
| Job logs **HTTP 410** | GitHub deleted workflow job logs; `fetch_ci_job_log` cannot recover pytest-cov or Sonar gate JSON |
| Artifact **expired** | `unit-coverage-report-ci` zip no longer downloadable |
| Codecov comment missing | No bot comment on the PR |
| Sonar comment format | Older parser missed markdown bullets — fixed in `parse_sonar_text()` for estimated-after-merge lines |

**Recovery:** Re-trigger CI on the PR (fresh logs + artifact), then `prefetch_coverage_inputs.py {KEY} --pr URL …` and `build_coverage_report.py {KEY}`. If only the Sonar PR comment remains in cache, report may show **estimated after merge** % (not necessarily the same as new-code quality-gate % from expired logs).

## Scoring reminder

| Source | Maps to report field |
|--------|----------------------|
| Jira AC → code mapping | Requirement coverage % |
| Jira AC → test mapping | Test requirement coverage % |
| Codecov / Sonar / CI log | CI line coverage % |

Never substitute CI line coverage for requirement coverage—they measure different things.

## Multi-org PR access (Option C)

Stories may link PRs across orgs (e.g. `wbd-msc/cde-media-manager` + `discoveryinc-cs/distribute-configuration`).

1. **Authorize every org** your token needs:
   ```bash
   gh auth refresh -h github.com -s read:org,repo
   ```
   Then open `https://github.com/orgs/{org}` and **Authorize SSO** for each enterprise org.

2. **Preflight** (with issue key) probes each repo in `reports/.cache/{KEY}-jira.json` `prUrls`:
   ```bash
   python scripts/preflight_coverage_validator.py MSC-208859 --verify-jira
   ```

3. **Partial prefetch** — `prefetch_coverage_inputs.py` fetches accessible PRs and records failures in `prefetchErrors` (report §2 shows **Inaccessible** rows). Pipeline continues when ≥1 PR succeeds.

4. **Jira Development panel count** — Jira may show 5 merged PRs while only 3 URLs appear in comments. The validator stores `jiraDevPanel.githubPrCount` and warns in §2 when counts differ. Paste missing PR URLs in Jira comments or manifest `prUrls`.

```bash
python scripts/prefetch_coverage_inputs.py MSC-208859 --from-jira-cache --write-manifest
```
