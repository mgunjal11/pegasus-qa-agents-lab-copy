---
name: Spec2Test
description: >-
  Fetches MSC Jira user stories via Atlassian MCP and produces QMetry-format
  test cases as downloadable Excel (.xlsx) matching QMetry FF2.0 template.
  When LADR/Confluence is linked, covers Jira acceptance criteria and LADR ESS
  scenarios; otherwise Jira only. Invoke via @Spec2Test MSC-1234 or
  /Spec2Test MSC-1234.
---

Follow **`.cursor/skills/jira-story-testcases/SKILL.md`** for the full workflow (Steps 1–7), QMetry layout, defaults, and quality bar.

## First run (once)

| Step | Action |
|------|--------|
| **1** | Atlassian MCP → `wbdstreaming.atlassian.net` |
| **2** | `pip install -r requirements.txt` |
| **3** | `/Spec2Test MSC-1234` — draft → approval → Excel |

## Req2Release fallback (when orchestrator exits **2**)

`/Req2Release` does **not** invoke Spec2Test automatically. Flow:

1. **Jira attachment** — Req2Release downloads attached QMetry Excel when present.
2. **`no_testplan`** — orchestrator runs `generate_testcases_from_requirements.py` (deterministic) first.
3. **Exit 2** — only when auto-generate is off or produced zero cases → invoke **`/Spec2Test {KEY}`** here.

When Spec2Test is invoked for that fallback, follow [testplan-missing-fallback.md](.cursor/skills/coverage-validator/references/testplan-missing-fallback.md): show draft → approval → write `testcases/{KEY}-testcases.xlsx`, then re-run Req2Release.

**Standalone invoke** (normal path): draft → explicit user approval → Excel — always use the review gate in Step 6 of the skill.

## Do not

- Old 20-column format; `.tsv`/`.md` in `testcases/`; skip Excel merges; invent LADR; drop Jira AC when LADR present.

**Developed by:** Mayur Gunjal
