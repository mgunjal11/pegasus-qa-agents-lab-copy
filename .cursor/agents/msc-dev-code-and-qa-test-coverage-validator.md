---

name: msc-dev-code-and-qa-test-coverage-validator

description: >-

  MSC Jira-to-PR and QMetry test plan validator for WBD Streaming. One-command pipeline via

  run_coverage_validator.py (auto Jira fetch, preflight, semantic mapping, auto test-plan

  generation). Dev vs QA scope, NFR SIT caps, optional --execute-tests. Invoke via

  @msc-dev-code-and-qa-test-coverage-validator MSC-1234 or /msc-dev-code-and-qa-test-coverage-validator MSC-1234.

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

| **4** | `/msc-dev-code-and-qa-test-coverage-validator MSC-1234` |



Preflight and Jira fetch run **automatically** inside `run_coverage_validator.py`.



## Slash invoke (`--auto --write`)



**One command** (auto-generates missing/partial test plans unless opted out):



```bash

python scripts/run_coverage_validator.py {KEY} --auto --write --skip-if-fresh --verify-jira

```



Runs preflight → **fetch_jira_story** → confluence → test plan → **auto-generate QMetry cases when needed** → prefetch → map → build.



| Situation | Orchestrator behavior (default) |

|-----------|----------------------------------|

| `no_testplan` | `generate_testcases_from_requirements.py` → `testcases/{KEY}-testcases.xlsx` → re-fetch |

| Attached plan with uncovered R/L | Gap supplement → `testcases/{KEY}-gap-supplement.xlsx` merged at fetch → re-fetch |

| Auto-generate disabled / failed | Exit **2** + `needs_testcase_writer` → invoke `@msc-testcase-writer {KEY}` → re-run |



Flags: `--no-auto-generate-testplan`, `--no-fill-testplan-gaps`. Manifest/defaults: `generateTestPlanIfMissing`, `fillTestPlanGaps`, `skipTestcaseGeneration`.



Manual gap-only: `python scripts/generate_testcases_from_requirements.py {KEY} --gap-only R4,L5 --write-excel`



**MCP fallback:** `python scripts/fetch_jira_story.py {KEY} --from-mcp-json /tmp/issue.json` then orchestrator with `--no-fetch-jira`.



## Auto-run (mandatory)



| Rule | Do |

|------|-----|

| Pipeline | Single `run_coverage_validator.py` call; on exit **2** only then `@msc-testcase-writer` |

| Preflight | Auto on invoke; on auth errors → `preflight_coverage_validator.py {KEY} --verify-jira` |

| GitHub | One prefetch in orchestrator; `--skip-if-fresh` when PR URLs unchanged |

| Never | Separate ad-hoc `gh` calls; edit `SUMMARY_METRIC_INFO` for content changes |



**Developed by:** Mayur Gunjal

