# Documentation

| File | How to generate |
|------|-----------------|
| `MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx` | `python scripts/generate_coverage_validator_ppt.py` |

**Management deck (~20 slides)** — WBD QBR brand + executive visuals (KPI cards, workflow pipeline, architecture diagram, personas, metrics dashboard, case-study table):

- Title with KPI strip · Visual agenda · Executive summary
- Challenge silos · Idea Generation · Personas · 5-step workflow · Architecture
- Report 8-section grid · Metrics dashboard · Test plan · Dev/QA split
- Setup checklist · MSC case studies table · Closing

Also written to `reports/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Guide.pptx`. Regenerate after skill updates.

**Word directory guide:** `python scripts/generate_coverage_validator_directory_guide.py` → `docs/MSC-Dev-Code-and-QA-Test-Coverage-Validator-Directory-Guide.docx`

Recent metric logic (deck + doc): LADR `dedupe_ladr_requirements()`, unique test-plan coverage %, Sonar PR comment CI fallback, report tooltips v22 (unchanged by metric fixes).
