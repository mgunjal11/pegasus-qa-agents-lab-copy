# Documentation

| File | How to generate |
|------|-----------------|
| `MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx` | `python scripts/generate_coverage_validator_ppt.py` |
| `MSC-Dev-Code-and-QA-Test-Coverage-Validator-Directory-Guide.docx` | `python scripts/generate_coverage_validator_directory_guide.py` |

**Management deck (~20 slides)** — WBD QBR brand: workflow, personas, 8-section report walkthrough, Dev/QA split, §8 recommended actions.

Also copied to `reports/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx` when generated.

**Recent report features (deck + HTML):**

- §3 honest test-plan note (`build_testplan_summary_note()`); Evidence **No execution evidence** for `workspace_generated` plans
- §8 **Dev** and **QA** recommended actions (`build_recommended_actions_list()`)
- Testcase writer fallback: `write_testcase_excel.py` + cache TSV only in `reports/.cache/`
- LADR dedupe in test-plan %; Sonar PR comment CI fallback
- Report tooltips layout **v22** — do not edit `SUMMARY_METRIC_INFO` when changing metrics (see `coverage-validator/references/content-vs-tooltips.md`)

**Word directory guide** — agent/skill/script tree aligned with `.cursor/agents/` + `.cursor/skills/coverage-validator/`.
