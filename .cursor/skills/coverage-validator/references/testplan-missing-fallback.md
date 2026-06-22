# Missing or partial Jira test plan — auto-generate + `/msc-testcase-writer` fallback

When Jira has **no test plan attachment**, the orchestrator **auto-generates** QMetry cases via `generate_testcases_from_requirements.py` (deterministic). When an attached plan has **uncovered R/L**, it writes **`testcases/{KEY}-gap-supplement.xlsx`** and merges at fetch.

**LLM fallback:** `/msc-testcase-writer` when auto-generate is disabled or exit **2** / `needs_testcase_writer`.

**Do not change** `apply_report_ui_enhancements()`, `SUMMARY_METRIC_INFO`, or report-template tooltip markup when adding this flow — only workflow, caches, and §3 narrative/notes.

## When to auto-generate (after Step 5 fetch)

Read `reports/.cache/{KEY}-testplan.json` after `fetch_jira_testplan.py`:

| status | Auto-generate (`generateTestPlanIfMissing` / `fillTestPlanGaps`) |
|--------|---------------------------------------------------------------------|
| `ok` with uncovered R/L | **Gap supplement** when `fillTestPlanGaps: true` |
| `ok` fully covered | **No** |
| `referenced_not_local` | **No** — add `testplans/{filename}` locally |
| `parse_failed` | **No** (default) — fix file first |
| `no_testplan` | **Full generate** when `generateTestPlanIfMissing: true` |

Also skip when:

- `--skip-testplan` or `validateTestPlan: false`
- `skipTestcaseGeneration: true`
- `--no-auto-generate-testplan` / `--no-fill-testplan-gaps`

## Manifest / defaults flags

```json
{
  "generateTestPlanIfMissing": true,
  "fillTestPlanGaps": true,
  "skipTestcaseGeneration": false
}
```

| Flag | Default | Meaning |
|------|---------|---------|
| `generateTestPlanIfMissing` | `true` | Full QMetry plan when `no_testplan` |
| `fillTestPlanGaps` | `true` | Supplement cases for uncovered R/L on attached plans |
| `skipTestcaseGeneration` | `false` | Opt out of all auto-generation |

## Auto pipeline (`run_coverage_validator.py`)

1. **`no_testplan`:** `python scripts/generate_testcases_from_requirements.py {KEY} --write-excel` → `testcases/{KEY}-testcases.xlsx`
2. **Partial gaps:** `python scripts/generate_testcases_from_requirements.py {KEY} --gap-only from-testplan --write-excel` → `testcases/{KEY}-gap-supplement.xlsx` (merged with Jira attachment at fetch)
3. Re-fetch: `fetch_jira_testplan.py {KEY} --from-jira-cache`
4. Continue map + build
5. §3 note: workspace-generated / gap supplement (not attached on Jira unless uploaded)

**LLM upgrade (optional):** `@msc-testcase-writer {KEY}` for richer scenarios; `--gap-only R4,L5` via generate script CLI.

## Interactive mode (no `--auto`)

Offer auto-generate or `/msc-testcase-writer {KEY}` with normal approval before writing files.

When `status` is `no_testplan`:

1. Tell the user no Jira test plan was found.
2. Offer: run **`/msc-testcase-writer {KEY}`** (with normal approval gate) or attach Excel to Jira / add to `testplans/`.
3. After user approves testcase writer output, re-run `fetch_jira_testplan.py` and continue validation.

## LADR-aware cases

Before drafting, run:

```bash
python scripts/fetch_confluence_requirements.py {KEY} --from-jira-cache
python scripts/prepare_testcase_writer_context.py {KEY} --from-jira-cache
```

| `mode` | Testcase writer scope |
|--------|------------------------|
| `jira_and_ladr` | Cover every **R1…Rn** and **L1…Ln**; ESS task+status in **Then** steps |
| `jira_only` | Cover Jira AC only — no invented L-items |

See `.cursor/skills/jira-story-testcases/references/ladr-confluence-requirements.md`.

## What this does **not** replace

- SharePoint-only references (`referenced_not_local`) — still need `testplans/Domino Test Plan.xlsx` locally.
- Domino evidence sheets with Mascot/SIT Jobs columns — generated QMetry cases use standard QMetry columns only. Validator §3 Evidence shows **No execution evidence** for `workspace_generated` plans (step UUIDs in Then clauses are not execution proof).
- Jira readiness **✗ Test plan** until a file is attached on the issue (generated local plan does not flip readiness ✓ unless uploaded).
