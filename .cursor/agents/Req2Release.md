---

name: Req2Release

description: >-

  MSC Jira-to-PR and QMetry test plan validator for WBD Streaming. One-command pipeline via

  run_coverage_validator.py (auto Jira fetch, preflight, semantic mapping, auto test-plan

  generation). Dev vs QA scope, NFR SIT caps, optional --execute-tests. Invoke via

  @Req2Release MSC-1234 or /Req2Release MSC-1234.

model: inherit

---



Follow **`.cursor/skills/coverage-validator/SKILL.md`** for the full workflow (Steps 0–9), report placeholders, and references. **Never** edit tooltip copy when changing report content — [content-vs-tooltips.md](.cursor/skills/coverage-validator/references/content-vs-tooltips.md).



## First run (once)



| Step | Action |

|------|--------|

| **0** | [cli.github.com](https://cli.github.com) → `gh auth login` |

| **1** | Jira REST: run install or preflight — auto-copies `.env.example` → `.env` (gitignored); set `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` |

| **2** | `python scripts/install_coverage_validator_permissions.py` |

| **3** | Optional: `validator.defaults.example.json` → `.coverage-validator.defaults.json` |

| **4** | `/Req2Release MSC-1234` |



Preflight and Jira fetch run **automatically** inside `run_coverage_validator.py`.



## Slash invoke (`--auto --write`)



**One command** (auto-generates missing/partial test plans unless opted out):



```bash

python scripts/run_coverage_validator.py {KEY} --auto --write --skip-if-fresh --verify-jira

```



Runs preflight → **fetch_jira_story** → confluence → test plan → **auto-generate QMetry cases when needed** → prefetch → **map (PR-gated code + dev test evidence)** → build.

## Evidence sources (mandatory)

| Report area | Primary evidence | Not scored from |
|-------------|------------------|-----------------|
| **§5 Code** | `gh pr diff` — production `src/` paths | LADR, Confluence, test-plan text |
| **§5 Dev tests** | `gh pr diff` — `def test_*` in diff | Test module name alone; design docs |
| **§3 Test plan** | Jira attachment (REST download) → local `testplans/` → workspace Excel | PR diff |
| **§1 Dev code / dev test %** | Same badges as §5 (Implemented/Partial/Missing; Covered/Partial/Missing weights) | Semantic boost on design context |
| **§1 Attached test plan %** | Jira-attached cases only | Gap-supplement Excel (see effective % in §3 split) |
| **Release readiness** | Weighted: dev code 30%, dev tests 25%, attached test plan 25%, gaps 10%, CI 10% | — |

**§5 traceability:** Code and Dev tests columns come from `gh pr diff` only — production `src/` paths for **Implemented**; `def test_*` in diff for **Covered**. LADR/Confluence/test-plan overlap is advisory in Evidence (`designContextOverlap`), not scored.

**Semantic boost (`semanticMappingBoost`, default `false`):** when enabled, may raise **Code** scores from **PR diff comment lines** only — never from LADR, Confluence, or test-plan steps.



| Situation | Orchestrator behavior (default) |

|-----------|----------------------------------|

| Jira attachment present | `fetch_jira_testplan.py` downloads Excel from issue (`.env` creds) — primary path |

| `no_testplan` | Script first: `generate_testcases_from_requirements.py` → `testcases/{KEY}-testcases.xlsx` → re-fetch (**not** auto `@Spec2Test`) |

| Attached plan with uncovered R/L | Gap supplement → `testcases/{KEY}-gap-supplement.xlsx` merged at fetch → re-fetch; attached % excludes supplement; effective % in §3 when merged |

| Auto-generate disabled / zero cases | Exit **2** + `needs_testcase_writer` → invoke `@Spec2Test {KEY}` manually → re-run orchestrator |



Flags: `--no-auto-generate-testplan`, `--no-fill-testplan-gaps`. Manifest/defaults: `generateTestPlanIfMissing`, `fillTestPlanGaps`, `skipTestcaseGeneration`.



Manual gap-only: `python scripts/generate_testcases_from_requirements.py {KEY} --gap-only R4,L5 --write-excel`



**MCP fallback:** `python scripts/fetch_jira_story.py {KEY} --from-mcp-json /tmp/issue.json` then orchestrator with `--no-fetch-jira`.



## Auto-run (mandatory)



| Rule | Do |

|------|-----|

| Pipeline | Single `run_coverage_validator.py` call; on exit **2** only then `@Spec2Test` |

| Preflight | Auto on invoke; on auth errors → `preflight_coverage_validator.py {KEY} --verify-jira` |

| GitHub | One prefetch in orchestrator; `--skip-if-fresh` when PR URLs unchanged |

| Never | Separate ad-hoc `gh` calls; edit `SUMMARY_METRIC_INFO` for content changes |



**Developed by:** Mayur Gunjal
