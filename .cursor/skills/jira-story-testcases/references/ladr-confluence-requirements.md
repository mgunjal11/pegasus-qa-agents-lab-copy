# LADR / Confluence requirements for testcase writer

Use when the Jira story links or references a **LADR** or Confluence design page with ESS scenarios.

## When LADR applies

| Signal | Action |
|--------|--------|
| Remote wiki link on Jira (`atlassian.net/wiki/...`) | Fetch Confluence |
| Description/comments mention **LADR**, **ESS**, milestone tasks | Fetch Confluence |
| `reports/.cache/{KEY}-confluence.json` has `ladrRequirements` | **Jira + LADR** mode |
| None of the above | **Jira only** mode |

## Fetch (after Jira cache exists)

```bash
python scripts/fetch_confluence_requirements.py {ISSUE-KEY} --from-jira-cache
```

Or parallel MCP: `getConfluencePage` with `pageId` from wiki URL, `contentFormat: markdown`.

Optional one-shot context for drafting:

```bash
python scripts/prepare_testcase_writer_context.py {ISSUE-KEY} --from-jira-cache --fetch
```

Returns `mode`: `jira_and_ladr` or `jira_only`, plus `jiraRequirements` (R1…) and `ladrRequirements` (L1…).

## Drafting rules — Jira + LADR mode

Cover **both** sets:

1. **Jira acceptance criteria** — at least one test case per `R1`…`Rn` (combine only when clarity suffers).
2. **LADR scenarios** — at least one test case per `L1`…`Ln` ESS milestone (task + status).

### ESS milestone mapping (Caption Monitoring style)

Include **task name** and **status** in **Then** (and Summary when helpful):

| Task | Example statuses |
|------|------------------|
| `demandAcknowledgment` | Completed, Failure |
| `manifestationAvailability` | Pending, Completed |
| `orderStatus` | Pending, Processing, Completed, Failure, Skipped |
| `registrationStatus` | Pending, Completed, Failure |

Example Then: `Then: orderStatus is Completed and status propagates to UI per LADR`

### Passport / pick-genie LADR

Use scenario labels in steps: **MVP Full**, **Incremental to Full**, **MDU to Full**, **MDU in Pick** — matches `map_testcases_to_requirements()` passport_scenario kind.

### Summary naming

- Jira-focused: `{KEY}_Verify house format promo skips normalization`
- LADR-focused: `{KEY}_Verify demandAcknowledgment Completed for caption order`
- Optional id hint: `{KEY}_Verify orderStatus Completed (L5, R2)`

## Draft review output

When `hasLadr` is true, show:

- **Jira requirements** — R1…Rn bullets
- **LADR requirements** — L1…Ln with task/status or scenario text
- **Coverage matrix** — each R* and L* mapped to ≥1 TC id (TC1…)

## Jira-only mode

When no LADR is linked, extract and test **only** Jira description AC — do not invent L-items.
