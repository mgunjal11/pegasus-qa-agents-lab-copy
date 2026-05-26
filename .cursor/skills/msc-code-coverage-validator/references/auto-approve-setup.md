# Auto-approve setup — no more Allow/Run clicks

Cursor shows **Allow** / **Run** when the agent calls MCP tools or shell commands. For `msc-code-coverage-validator`, configure auto-approve once using the steps below.

> **Important:** Hooks that return `"permission": "allow"` do **not** reliably override MCP approval. Use **`permissions.json`** + **Auto-Run mode** (official path).

## One-time setup (5 minutes)

### 1. Enable Auto-Run in Cursor

**Cursor Settings → Agents → Auto-Run**

Choose one of:

| Mode | Effect |
|------|--------|
| **Allowlist** | Only allowlisted MCP/shell auto-runs *(recommended)* |
| **Allowlist (with Sandbox)** | Allowlisted runs outside sandbox |
| **Run Everything** | All tools auto-run *(least restrictive)* |

Turn **off** (if present): **MCP Tool Protection** (Enterprise) for this workflow.

### 2. Install project allowlist

This repo includes `.cursor/permissions.json` with coverage-validator tools pre-allowlisted.

If prompts still appear, **merge the same arrays** into your user file:

**Windows:** `%USERPROFILE%\.cursor\permissions.json`  
**macOS/Linux:** `~/.cursor/permissions.json`

Use [permissions.coverage-validator.example.json](../../../permissions.coverage-validator.example.json) as a template. Merge — do not delete existing entries.

```json
{
  "mcpAllowlist": [
    "user-atlassian:getJiraIssue",
    "user-atlassian:getJiraIssueRemoteIssueLinks",
    "user-atlassian:getAccessibleAtlassianResources",
    "user-atlassian:searchJiraIssuesUsingJql"
  ],
  "terminalAllowlist": [
    "gh",
    "python scripts/prefetch_coverage_inputs.py",
    "python scripts/fetch_coverage_github.py",
    "mkdir"
  ]
}
```

**MCP pattern:** `server:tool` — case-insensitive, `*` wildcards supported (`user-atlassian:*` allowlists all Atlassian tools).

**Terminal pattern:** prefix match — `gh` matches all `gh` subcommands.

Restart Cursor after creating or editing `~/.cursor/permissions.json`.

### 3. Set workspace defaults (optional)

Copy [validator.defaults.example.json](../validator.defaults.example.json) → `.coverage-validator.defaults.json` at repo root:

```json
{
  "repo": "wbd-msc/pegasus-ess",
  "mode": "auto",
  "writeReport": true,
  "useCache": true
}
```

### 4. Invoke with auto mode

```
/msc-code-coverage-validator MSC-204417 --auto
```

Or use the slash command (defaults to `--auto --write`):

```
/msc-code-coverage-validator MSC-204417
```

## Why you still see prompts (troubleshooting)

| Symptom | Fix |
|---------|-----|
| MCP Allow on every Jira fetch | Add `user-atlassian:*` to `mcpAllowlist`; enable Auto-Run Allowlist |
| Run on every `gh` call | Add `gh` to `terminalAllowlist` |
| Many shell prompts | Agent must use **one** prefetch script call, not N separate `gh` commands — see agent/skill |
| Hook returns allow but still prompts | Expected — use `permissions.json`, not hooks alone |
| Auto-Run is "Ask Every Time" | Change to **Allowlist** or **Run Everything** |

## Zero-prompt workflow (GitHub only)

Run prefetch **once in your terminal** (outside agent — no approval UI):

```bash
python scripts/prefetch_coverage_inputs.py MSC-204417 --repo wbd-msc/pegasus-ess --search-pr
```

Then agent run needs only Jira MCP (one parallel batch):

```
/msc-code-coverage-validator MSC-204417 --from-cache --auto --skip-jira
```

Or after Jira cache exists from a prior `--fetch-only` run:

```
/msc-code-coverage-validator MSC-204417 --from-cache --auto --skip-jira
```

## Agent rules that reduce prompts

Even with allowlists, the agent is instructed to:

1. Batch Jira MCP calls in **one turn** (parallel).
2. Use **one shell** for all GitHub data (prefetch script or cache).
3. Default **`--auto --write`** for `/msc-code-coverage-validator` invocations.
4. Save manifest/cache for repeat runs.
