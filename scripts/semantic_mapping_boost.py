#!/usr/bin/env python3
"""
Optional second-pass evidence for requirement-to-diff mapping.

**Scoring rule:** Code and Dev test statuses/scores may only rise from PR diff
comment/docstring lines — never from Confluence/LADR or QMetry test-plan text.

LADR and test-plan overlap is recorded as advisory `designContextOverlap` only.

  python scripts/semantic_mapping_boost.py MSC-205625
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(text: str, min_len: int = 4) -> list[str]:
    return [t.lower() for t in re.split(r"\W+", text) if len(t) >= min_len]


def _phrases(text: str) -> list[str]:
    """Short phrases and acronyms for semantic overlap."""
    low = text.lower()
    phrases: list[str] = []
    for m in re.finditer(r"\b[A-Z]{2,}\b", text):
        phrases.append(m.group(0).lower())
    words = [w for w in re.split(r"\W+", low) if len(w) >= 3]
    for i in range(len(words) - 1):
        phrases.append(f"{words[i]} {words[i + 1]}")
    for term in (
        "ess",
        "kafka",
        "caption",
        "spotlight",
        "passport",
        "status code",
        "error code",
        "integration test",
        "unit test",
        "sit",
        "staging",
    ):
        if term in low and term not in phrases:
            phrases.append(term)
    return list(dict.fromkeys(phrases))


def _comment_lines(diff_blob: str) -> str:
    lines: list[str] = []
    for line in diff_blob.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        body = line[1:].strip()
        if body.startswith("#") or body.startswith("//") or '"""' in body or "'''" in body:
            lines.append(body)
    return "\n".join(lines)


def _overlap_phrases(phrases: list[str], haystack: str) -> float:
    if not phrases or not haystack:
        return 0.0
    norm = haystack.lower()
    hits = sum(1 for p in phrases if p in norm)
    return hits / max(len(phrases), 1)


def _confluence_haystack(confluence: dict[str, Any], req_id: str) -> str:
    parts: list[str] = []
    for page in confluence.get("pages") or []:
        parts.append(str(page.get("title") or ""))
        for ess in page.get("essScenarios") or []:
            if str(ess.get("id") or "").upper() == req_id.upper():
                parts.append(str(ess.get("title") or ""))
                parts.append(str(ess.get("description") or ""))
            parts.append(str(ess.get("title") or ""))
            parts.append(str(ess.get("description") or ""))
    return " ".join(parts)


def _testplan_haystack(testplan: dict[str, Any], req_id: str) -> str:
    parts: list[str] = []
    for tc in testplan.get("testCases") or []:
        mapped = {str(x).upper() for x in (tc.get("mapped_requirements") or [])}
        if req_id.upper() in mapped:
            parts.append(str(tc.get("summary") or ""))
            steps = tc.get("steps") or {}
            parts.extend(str(steps.get(k) or "") for k in ("given", "when", "then"))
    return " ".join(parts)


def _recalc_coverage_pcts(reqs: list[dict[str, Any]], out: dict[str, Any]) -> None:
    from map_requirements_to_diff import compute_coverage_pcts

    out.update(
        compute_coverage_pcts(
            reqs,
            jira_requirement_count=out.get("jiraRequirementCount"),
            ladr_requirement_count=out.get("ladrRequirementCount"),
        )
    )


def apply_semantic_boost(
    mapping: dict[str, Any],
    *,
    diff_blob: str,
    confluence: dict[str, Any] | None = None,
    testplan: dict[str, Any] | None = None,
    min_boost: float = 0.08,
) -> dict[str, Any]:
    """
    Second pass on mapping cache.

    - **Code / Dev test:** PR diff comment lines only (same thresholds as primary mapper).
    - **Confluence / test plan:** advisory overlap only — does not change scores or §5 badges.
    """
    from map_requirements_to_diff import _status_from_score

    confluence = confluence or {}
    testplan = testplan or {}
    pr_comments = _comment_lines(diff_blob)
    out = dict(mapping)
    reqs: list[dict[str, Any]] = []
    pr_boosted = 0
    design_context_count = 0

    for req in mapping.get("requirements") or []:
        r = dict(req)
        text = str(r.get("text") or "")
        rid = str(r.get("id") or "")
        phrases = _phrases(text)
        req_tokens = _tokens(text)

        old_code = float(r.get("codeScore") or 0)
        old_test = float(r.get("devTestScore") or 0)
        new_code = old_code
        new_test = old_test

        if pr_comments.strip():
            semantic_code = (
                _overlap_phrases(phrases, pr_comments) * 0.9
                + _overlap_phrases(req_tokens, pr_comments) * 0.4
            )
            new_code = max(old_code, min(1.0, semantic_code))

        pr_notes: list[str] = []
        if new_code - old_code >= min_boost:
            pr_boosted += 1
            pr_notes.append("semantic:diff_comments")
            r["codeScore"] = round(new_code, 3)
            r["codeStatus"] = _status_from_score(new_code)
            prev = str(r.get("evidenceNote") or "")
            extra = "PR comment overlap (" + ", ".join(pr_notes) + ")"
            r["evidenceNote"] = f"{prev}; {extra}".strip("; ") if prev else extra
            r["semanticBoost"] = True

        design_overlap: list[str] = []
        conf_hay = _confluence_haystack(confluence, rid)
        tp_hay = _testplan_haystack(testplan, rid)
        if conf_hay.strip() and _overlap_phrases(phrases, conf_hay) >= 0.12:
            design_overlap.append("confluence")
        if tp_hay.strip() and _overlap_phrases(phrases, tp_hay) >= 0.12:
            design_overlap.append("testplan")
        if design_overlap:
            design_context_count += 1
            r["designContextOverlap"] = design_overlap
            r["designContextNote"] = (
                "LADR or test-plan text aligns with requirement "
                "(not PR implementation proof — Code/Dev tests use PR diff only)."
            )

        reqs.append(r)

    out["requirements"] = reqs
    out["semanticBoostApplied"] = pr_boosted > 0
    out["semanticBoostCount"] = pr_boosted
    out["designContextOverlapCount"] = design_context_count
    _recalc_coverage_pcts(reqs, out)
    return out


def boost_mapping_for_issue(issue_key: str, root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    key = issue_key.upper()
    cache = base / "reports" / ".cache"
    mapping = _load_json(cache / f"{key}-mapping.json")
    if not mapping:
        raise FileNotFoundError(f"Missing mapping cache for {key}")
    prefetch = _load_json(cache / f"{key}-prefetch.json")
    diff_blob = "\n".join(str(pr.get("diff") or "") for pr in prefetch.get("prs") or [])
    bc = prefetch.get("branchCompare") or {}
    if bc.get("files"):
        diff_blob += "\n" + "\n".join(str(f) for f in bc.get("files") or [])
    confluence = _load_json(cache / f"{key}-confluence.json")
    testplan = _load_json(cache / f"{key}-testplan.json")
    return apply_semantic_boost(
        mapping,
        diff_blob=diff_blob,
        confluence=confluence,
        testplan=testplan,
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Apply semantic boost to mapping cache")
    parser.add_argument("issue_key")
    parser.add_argument("--write", action="store_true", default=True)
    args = parser.parse_args()
    key = args.issue_key.upper()
    out_path = ROOT / "reports" / ".cache" / f"{key}-mapping.json"
    payload = boost_mapping_for_issue(key)
    if args.write:
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(out_path.resolve()),
                "semanticBoostCount": payload.get("semanticBoostCount"),
                "designContextOverlapCount": payload.get("designContextOverlapCount"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
