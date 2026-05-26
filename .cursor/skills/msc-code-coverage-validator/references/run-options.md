# Run options — msc-code-coverage-validator

Use these options to avoid repeated manual prompts (MCP Allow/Run clicks, PR URL re-entry, repo guessing).

## Quick start

```bash
# One-shot GitHub prefetch (run in terminal — no MCP prompts for PR data)
python scripts/prefetch_coverage_inputs.py MSC-209376 --pr https://github.com/wbd-msc/my-repo/pull/42

# Full validation using cache + auto mode
@msc-code-coverage-validator MSC-209376 --from-cache --auto
```

```bash
# Or pass everything inline (agent fetches Jira via MCP once, GitHub via prefetch or gh batch)
@msc-code-coverage-validator MSC-209376 --pr https://github.com/wbd-msc/my-repo/pull/42 --repo wbd-msc/my-repo --auto --write
```

## Modes

| Mode | Flag | Behavior |
|------|------|----------|
| **auto** | `--auto` | Fetch all sources, write HTML report, no mid-run approval stops. Only ask if issue key is missing. |
| **fetch** | `--fetch-only` | Prefetch Jira (MCP) + GitHub (gh) into cache; no analysis or report. |
| **from-cache** | `--from-cache` | Skip live GitHub fetches when fresh cache exists; still fetch Jira if no cache. |
| **interactive** | *(default)* | Ask once for PR URL / repo when not found. Show summary before writing report. |

Modes combine: `--fetch-only` takes precedence; `--from-cache` skips gh when cache is fresh; `--auto` skips confirmation before write.

## Inline flags (parse from user message)

| Flag | Example | Effect |
|------|---------|--------|
| Issue key / URL | `MSC-209376` | Required unless in manifest |
| `--pr URL` | `--pr https://github.com/org/repo/pull/123` | Skip PR discovery; use this URL |
| `--pr URL2` | Multiple `--pr` allowed | Validate each PR |
| `--repo org/repo` | `--repo wbd-msc/media-lib-rasp` | Default repo for PR search + branch heuristic |
| `--auto` | | End-to-end without stops |
| `--fetch-only` | | Cache only |
| `--from-cache` | | Reuse `reports/.cache/{KEY}-prefetch.json` |
| `--write` | | Write HTML (default in auto mode) |
| `--no-write` | | Analysis in chat only |
| `--manifest PATH` | `--manifest my-run.json` | Load options from JSON file |
| `--skip-pr-search` | | Do not search Jira/heuristics when `--pr` provided |
| `--skip-jira` | | Use cached Jira markdown only (fetch-only must have run first) |
| `--post-jira` | | Post summary comment to Jira (default off) |
| `--cache-max-age H` | `--cache-max-age 48` | Hours before cache is stale (default 24) |

## Workspace defaults

Copy [validator.defaults.example.json](../validator.defaults.example.json) to repo root as `.coverage-validator.defaults.json` (gitignored). The agent merges: **inline flags > manifest > defaults**.

```json
{
  "repo": "wbd-msc/your-service",
  "mode": "auto",
  "searchPrIfMissing": true,
  "writeReport": true,
  "useCache": true,
  "cacheMaxAgeHours": 24
}
```

## Manifest file

For repeat runs on the same story, save a manifest:

```json
{
  "issueKey": "MSC-209376",
  "prUrls": ["https://github.com/wbd-msc/my-repo/pull/42"],
  "repo": "wbd-msc/my-repo",
  "mode": "auto",
  "skipPrSearch": true,
  "writeReport": true,
  "useCache": true
}
```

Run: `@msc-code-coverage-validator --manifest reports/.cache/MSC-209376-manifest.json`

After a successful run the agent may write the manifest to `reports/.cache/{ISSUE-KEY}-manifest.json` for next time.

## Cache layout

```
reports/.cache/
  {ISSUE-KEY}-prefetch.json    # GitHub PR view, diff, checks, codecov (from prefetch script)
  {ISSUE-KEY}-jira.json        # Jira issue markdown + remote links (from agent fetch-only)
  {ISSUE-KEY}-manifest.json    # Last-used run options
```

## Reducing MCP Allow / Run clicks

See **[references/auto-approve-setup.md](references/auto-approve-setup.md)** for full setup.

1. **Install permissions** — `python scripts/install_coverage_validator_permissions.py` + Cursor **Agents → Auto-Run → Allowlist**.
2. **Prefetch GitHub in one shell** — `python scripts/fetch_coverage_github.py {KEY} --repo {org}/{repo} --search-pr` or `--compare develop`.
3. **Batch MCP in one turn** — `getJiraIssue` + `getJiraIssueRemoteIssueLinks` parallel.
4. **`--fetch-only` then `--from-cache --auto --skip-jira`** — repeat runs need zero gh and zero Jira fetches.
5. Hooks alone do **not** override MCP approval — use `permissions.json`.

## Agent behavior by mode

| Step | auto | fetch-only | from-cache | interactive |
|------|------|------------|------------|-------------|
| Parse options / defaults | ✓ | ✓ | ✓ | ✓ |
| Fetch Jira (MCP) | ✓ unless `--skip-jira` + cache | ✓ | if no jira cache | ✓ |
| Resolve PR | use flags → cache → Jira links → search | same | skip gh if fresh prefetch | ask if missing |
| Fetch PR (gh) | batch or prefetch | prefetch script | read cache | batch |
| Analyze + report | ✓ write if `--write`/auto | ✗ | ✓ | confirm before write |
