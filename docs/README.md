# Documentation

Coverage validator and testcase writer deliverables are **HTML reports** and **QMetry Excel** — see the main [README.md](../README.md).

**Recent report features (HTML):**

- §3 honest test-plan note (`build_testplan_summary_note()`); Evidence **No execution evidence** for `workspace_generated` plans
- §8 **Dev** and **QA** recommended actions (`build_recommended_actions_list()`)
- Testcase writer fallback: `write_testcase_excel.py` + cache TSV only in `reports/.cache/`
- LADR dedupe in test-plan %; Sonar PR comment CI fallback
- Report tooltips layout **v22** — do not edit `SUMMARY_METRIC_INFO` when changing metrics (see `coverage-validator/references/content-vs-tooltips.md`)
