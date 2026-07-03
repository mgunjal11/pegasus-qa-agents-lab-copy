# Missing or partial Jira test plan — auto-generate + `/Spec2Test` fallback

When Jira has **no test plan attachment**, the orchestrator exits **2** and the agent invokes **`/Spec2Test {KEY}`** (preferred). When an attached plan is parsed, cases are mapped to **Jira + LADR** requirements; **gap supplement** adds cases **only for uncovered R/L**.

**Deterministic fallback:** `generate_testcases_from_requirements.py` full plan when `generateTestPlanIfMissing: true` in manifest/defaults (opt-in, default **off**).

**LLM path:** `/Spec2Test` on exit **2** / `needs_testcase_writer`. The orchestrator does **not** subprocess Spec2Test — exit **2** tells the agent/user to run `/Spec2Test {KEY}` and re-run Req2Release.

**Do not change** `apply_report_ui_enhancements()`, `SUMMARY_METRIC_INFO`, or report-template tooltip markup when adding this flow — only workflow, caches, and §3 narrative/notes.

## When to auto-generate (after Step 5 fetch)

Read `reports/.cache/{KEY}-testplan.json` after `fetch_jira_testplan.py`:

| status | Auto-generate (`generateTestPlanIfMissing` / `fillTestPlanGaps`) |
|--------|---------------------------------------------------------------------|
| `ok` with attached cases + uncovered R/L | **Gap supplement for uncovered R/L only** when `fillTestPlanGaps: true` |
| `ok` fully covered | **No** |
| `ok` with **0 attached** cases (parse miss) | **No gap fill** — fix attachment / add `testplans/{file}`; do not use supplement as primary |
| `referenced_not_local` | **No** — add `testplans/{filename}` locally |
| `parse_failed` | **No** (default) — fix file first |
| `no_testplan` | **`@Spec2Test {KEY}`** (exit 2); full generate only when `generateTestPlanIfMissing: true` |

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
| `generateTestPlanIfMissing` | `false` | Full QMetry plan when `no_testplan` (opt-in; default use `@Spec2Test`) |
| `fillTestPlanGaps` | `true` | Supplement cases for uncovered R/L on attached plans |
| `skipTestcaseGeneration` | `false` | Opt out of all auto-generation |

## Auto pipeline (`run_coverage_validator.py`)

1. **`no_testplan`:** `python scripts/generate_testcases_from_requirements.py {KEY} --write-excel` → `testcases/{KEY}-testcases.xlsx`
2. **Partial gaps:** `python scripts/generate_testcases_from_requirements.py {KEY} --gap-only from-testplan --write-excel` → `testcases/{KEY}-gap-supplement.xlsx` (merged with Jira attachment at fetch)
3. Re-fetch: `fetch_jira_testplan.py {KEY} --from-jira-cache`
4. Continue map + build
5. §3 note: workspace-generated / gap supplement (not attached on Jira unless uploaded)

**LLM upgrade (optional):** `@Spec2Test {KEY}` for richer scenarios; `--gap-only R4,L5` via generate script CLI.

## Interactive mode (no `--auto`)

Offer auto-generate or `/Spec2Test {KEY}` with normal approval before writing files.

When `status` is `no_testplan`:

1. Tell the user no Jira test plan was found.
2. Offer: run **`/Spec2Test {KEY}`** (with normal approval gate) or attach Excel to Jira / add to `testplans/`.
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
