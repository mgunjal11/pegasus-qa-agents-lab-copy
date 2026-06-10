# Documentation

| File | How to generate |
|------|-----------------|
| `MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx` | `python scripts/generate_coverage_validator_ppt.py` |
| `MSC-Dev-Code-and-QA-Test-Coverage-Validator-Directory-Guide.docx` | `python scripts/generate_coverage_validator_directory_guide.py` |

**Management deck (22 slides)** — WBD QBR brand. Keep polished slides 1–10 from `reports/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx`; regenerate tail: `python scripts/generate_coverage_validator_ppt.py --report-html reports/{KEY}-<latest>.html`. Use `--full` only when intentionally rebuilding prefix from script.

Also copied to `reports/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx` when generated.

**Recent report features (deck + HTML):**

- §3 honest test-plan note (`build_testplan_summary_note()`); Evidence **No execution evidence** for `workspace_generated` plans
- §8 **Dev** and **QA** recommended actions (`build_recommended_actions_list()`)
- Testcase writer fallback: `write_testcase_excel.py` + cache TSV only in `reports/.cache/`
- LADR dedupe in test-plan %; Sonar PR comment CI fallback
- Report tooltips layout **v22** — do not edit `SUMMARY_METRIC_INFO` when changing metrics (see `coverage-validator/references/content-vs-tooltips.md`)

**Word directory guide** — agent/skill/script tree aligned with `.cursor/agents/` + `.cursor/skills/coverage-validator/`. Includes **Step 4b** missing-test-plan fallback (`references/testplan-missing-fallback.md`), `write_testcase_excel.py`, `testcases/{KEY}-testcases.xlsx`, and manifest flags `generateTestPlanIfMissing` / `skipTestcaseGeneration`.
