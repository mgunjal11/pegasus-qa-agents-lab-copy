"""Tests for functional vs non-functional requirement classification."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from map_requirements_to_diff import (  # noqa: E402
    build_section_hints,
    classify_requirement_type,
    resolve_requirement_type,
    section_hints_from_text,
)
from coverage_report_helpers import (  # noqa: E402
    TRACE_TABLE_COLUMN_INFO,
    _render_requirement_type_badge,
    render_requirement_rows_from_mapping,
)


def test_nfr_from_keyword():
    rtype, cat = classify_requirement_type(
        "API response latency must stay under 200ms at p99 under load test"
    )
    assert rtype == "non_functional"
    assert cat == "performance"


def test_sit_validation_is_nfr():
    rtype, cat = classify_requirement_type(
        "Fix must be validated in SIT using provided test data (Edit ID abc)"
    )
    assert rtype == "non_functional"
    assert cat == "validation"


def test_msc205625_r4_text():
    r4 = (
        "Fix must be validated in SIT using provided test data "
        "(Edit ID 37ea180e-77cc-413f-95cf-9dfcebf08cd2, Media Request fc919602-2a91-49c9-ac61-1444a5889e6a)"
    )
    rtype, cat = classify_requirement_type(r4)
    assert rtype == "non_functional"
    assert cat == "validation"


def test_behavior_in_sit_stays_functional():
    rtype, _ = classify_requirement_type(
        "Content passport retained in cumulative output manifestation for PFT Clear incremental-as-full"
    )
    assert rtype == "functional"


def test_ladr_scenario_defaults_functional():
    rtype, _ = classify_requirement_type(
        "MVP Full — passport always gets attached",
        source="ladr",
        kind="passport_scenario",
    )
    assert rtype == "functional"


def test_jira_nfr_section_heading():
    text = """## Functional requirements
- R1: Passport retained in cumulative output
## Non-functional requirements
- R2: Structured logging for passport merge failures
"""
    hints = section_hints_from_text(text)
    assert hints["R1"] == "functional"
    assert hints["R2"] == "non_functional"
    rtype, cat = classify_requirement_type(
        "Structured logging for passport merge failures",
        section_hint=hints["R2"],
    )
    assert rtype == "non_functional"
    assert cat == "observability"


def test_build_section_hints_from_jira_requirement_section_field():
    jira = {
        "requirements": [
            {"id": "R1", "text": "User can export report", "section": "functional"},
            {"id": "R2", "text": "Encrypt data at rest", "section": "non-functional"},
        ]
    }
    hints = build_section_hints(jira)
    assert hints["R2"] == "non_functional"
    rtype, cat = classify_requirement_type(
        "Encrypt data at rest using encryption", section_hint=hints["R2"]
    )
    assert rtype == "non_functional"
    assert cat == "security"


def test_render_nfr_badge_without_new_table_column(tmp_path):
    key = "MSC-NFR"
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    (cache / f"{key}-mapping.json").write_text(
        """{
  "requirements": [
    {
      "id": "R1",
      "text": "Encrypt PII at rest using KMS encryption",
      "requirementType": "non_functional",
      "nfrCategory": "security",
      "codeStatus": "partial",
      "devTestStatus": "missing",
      "owner": "qa",
      "qaScope": "manual",
      "confidence": "low",
      "matchedFiles": []
    }
  ]
}""",
        encoding="utf-8",
    )
    html = render_requirement_rows_from_mapping(key, tmp_path)
    assert "badge-nfr" in html
    assert "NFR" in html
    assert len(re.findall(r"<td[\s>]", html)) == 7


def test_trace_table_tooltips_unchanged():
    assert len(TRACE_TABLE_COLUMN_INFO) == 7
    assert "ID" in TRACE_TABLE_COLUMN_INFO
    assert "Non-functional" not in str(TRACE_TABLE_COLUMN_INFO)


def test_resolve_requirement_type_from_jira_explicit():
    rtype, cat = resolve_requirement_type(
        {
            "text": "Encrypt data at rest using encryption",
            "requirementType": "non_functional",
            "requirementTypeSource": "jira",
        }
    )
    assert rtype == "non_functional"
    assert cat == "security"


def test_stale_mapping_cache_reclassified_on_render():
    """Report render re-applies rules; old functional cache entry for R4 still shows NFR."""
    rtype, cat = resolve_requirement_type(
        {
            "id": "R4",
            "text": "Fix must be validated in SIT using provided test data (Edit ID abc)",
            "requirementType": "functional",
        }
    )
    assert rtype == "non_functional"
    assert cat == "validation"


def test_process_requirement_badge():
    html = _render_requirement_type_badge(
        {"text": "Update runbook for on-call", "requirementType": "process"}
    )
    assert "Process" in html
    assert "badge-na" in html


def test_functional_requirement_shows_fr_badge():
    html = _render_requirement_type_badge(
        {"text": "Passport retained in cumulative output manifestation"}
    )
    assert "badge-fr" in html
    assert ">FR</span>" in html
