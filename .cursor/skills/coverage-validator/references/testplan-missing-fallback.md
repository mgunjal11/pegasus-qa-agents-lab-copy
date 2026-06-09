# Missing Jira test plan — `/msc-testcase-writer` fallback

When Jira has **no test plan attachment** and no SharePoint/comment reference, the coverage validator can **generate QMetry test cases** via **`/msc-testcase-writer`** (skill: `.cursor/skills/jira-story-testcases/SKILL.md`) so the pipeline can still score test-plan coverage from local files.

**Do not change** `apply_report_ui_enhancements()`, `SUMMARY_METRIC_INFO`, or report-template tooltip markup when adding this flow — only workflow, caches, and §3 narrative/notes.

## When to invoke (after Step 5 fetch)

Read `reports/.cache/{KEY}-testplan.json` → `status` after the first `fetch_jira_testplan.py` run:

| status | Invoke `/msc-testcase-writer`? |
|--------|-------------------------------|
| `ok` | **No** — test cases already parsed |
| `referenced_not_local` | **No** — Jira references SharePoint/Domino Excel; place file under `testplans/` and re-fetch |
| `parse_failed` | **No** (default) — fix the local file; optionally generate only if user asks |
| `no_testplan` | **Yes** (when enabled below) |

Also skip when:

- `--skip-testplan` or manifest/defaults `validateTestPlan: false`
- Manifest/defaults `skipTestcaseGeneration: true`
- `testcases/{KEY}-testcases.xlsx` already exists (re-fetch should pick it up — run fetch again before generating duplicates)

## Manifest / defaults flags

```json
{
  "generateTestPlanIfMissing": true,
  "skipTestcaseGeneration": false
}
```

| Flag | Default in `--auto --write` | Meaning |
|------|-----------------------------|---------|
| `generateTestPlanIfMissing` | `true` | Run testcase writer when `status` is `no_testplan` |
| `skipTestcaseGeneration` | `false` | Opt out of auto-generation |

## Auto pipeline (`--auto --write`)

When `generateTestPlanIfMissing` is true and `status` is `no_testplan`:

1. **Invoke testcase writer** for `{KEY}` — follow `.cursor/skills/jira-story-testcases/SKILL.md` and agent `.cursor/agents/msc-testcase-writer.md`.
2. **Approval gate:** In coverage-validator **`--auto --write`**, **skip** testcase-writer Step 6 (do not wait for user approval). Draft internally, then write files immediately.
3. **Write outputs** (Excel only in `testcases/`):
   - `reports/.cache/{KEY}-testcases-source.tsv`
   - `python scripts/write_testcase_excel.py {KEY}` → `testcases/{KEY}-testcases.xlsx`
4. **Re-fetch test plan** (one shell):
   ```bash
   python scripts/fetch_jira_testplan.py {KEY} --from-jira-cache
   ```
   `fetch_jira_testplan.py` loads `testcases/{KEY}-testcases.xlsx` as source **4** in its priority list.
5. **Continue** mapping + `build_coverage_report.py` as usual.
6. **Report honesty:** In §3 note / `{{TESTPLAN_NOTE}}`, state that the plan was **generated locally via msc-testcase-writer** (not attached on Jira). Suggested upload: `python scripts/upload_jira_testplan.py {KEY} --file testcases/{KEY}-testcases.xlsx` when credentials are configured.

## Interactive mode (no `--auto`)

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
