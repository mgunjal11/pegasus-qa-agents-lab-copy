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

## Scoring reminder

| Source | Maps to report field |
|--------|----------------------|
| Jira AC → code mapping | Requirement coverage % |
| Jira AC → test mapping | Test requirement coverage % |
| Codecov / Sonar / CI log | CI line coverage % |

Never substitute CI line coverage for requirement coverage—they measure different things.
