#!/usr/bin/env python3
"""
Optional semantic evidence boost for requirement-to-diff mapping.

Re-scores requirements using comment/docstring lines in the diff, Confluence ESS
scenario text, and test-plan step overlap — beyond token/symbol heuristics.

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


def _status_from_score(score: float) -> str:
    if score >= 0.55:
        return "implemented"
    if score >= 0.25:
        return "partial"
    return "missing"


def _test_status(score: float, has_test: bool) -> str:
    if score >= 0.5 and has_test:
        return "covered"
    if score >= 0.2 and has_test:
        return "partial"
    return "missing"


def apply_semantic_boost(
    mapping: dict[str, Any],
    *,
    diff_blob: str,
    confluence: dict[str, Any] | None = None,
    testplan: dict[str, Any] | None = None,
    min_boost: float = 0.08,
) -> dict[str, Any]:
    """Boost code/test scores when semantic haystacks exceed token-only scores."""
    confluence = confluence or {}
    testplan = testplan or {}
    comments = _comment_lines(diff_blob)
    out = dict(mapping)
    reqs: list[dict[str, Any]] = []
    boosted = 0

    for req in mapping.get("requirements") or []:
        r = dict(req)
        text = str(r.get("text") or "")
        rid = str(r.get("id") or "")
        phrases = _phrases(text)
        req_tokens = _tokens(text)

        haystacks = [
            ("diff_comments", comments),
            ("confluence", _confluence_haystack(confluence, rid)),
            ("testplan", _testplan_haystack(testplan, rid)),
        ]
        semantic_code = max(
            _overlap_phrases(phrases, h) * 0.9 + _overlap_phrases(req_tokens, h) * 0.4
            for _, h in haystacks
            if h.strip()
        ) if any(h.strip() for _, h in haystacks) else 0.0

        old_code = float(r.get("codeScore") or 0)
        old_test = float(r.get("devTestScore") or 0)
        new_code = max(old_code, min(1.0, semantic_code))
        new_test = old_test
        if _overlap_phrases(phrases, haystacks[2][1]) >= 0.15:
            new_test = max(old_test, min(1.0, _overlap_phrases(phrases, haystacks[2][1]) * 0.85))

        notes: list[str] = []
        if new_code - old_code >= min_boost:
            boosted += 1
            for label, hay in haystacks:
                if _overlap_phrases(phrases, hay) >= 0.12:
                    notes.append(f"semantic:{label}")
            r["codeScore"] = round(new_code, 3)
            r["codeStatus"] = _status_from_score(new_code)
            if notes:
                prev = str(r.get("evidenceNote") or "")
                extra = "Semantic boost (" + ", ".join(notes) + ")"
                r["evidenceNote"] = f"{prev}; {extra}".strip("; ") if prev else extra

        if new_test - old_test >= min_boost:
            r["devTestScore"] = round(new_test, 3)
            has_test = bool(r.get("matchedTests")) or new_test > 0.2
            r["devTestStatus"] = _test_status(new_test, has_test)

        if new_code > old_code or new_test > old_test:
            r["semanticBoost"] = True
        reqs.append(r)

    jira_scores = [
        1.0 if r.get("codeStatus") == "implemented" else 0.5 if r.get("codeStatus") == "partial" else 0.0
        for r in reqs
        if str(r.get("source") or "") == "jira"
    ]
    dev_scores = [
        1.0 if r.get("devTestStatus") == "covered" else 0.5 if r.get("devTestStatus") == "partial" else 0.0
        for r in reqs
        if r.get("owner") != "qa"
    ]
    out["requirements"] = reqs
    out["semanticBoostApplied"] = boosted > 0
    out["semanticBoostCount"] = boosted
    if jira_scores:
        out["reqCoveragePct"] = round(100 * sum(jira_scores) / len(jira_scores), 1)
    if dev_scores:
        out["devTestCoveragePct"] = round(100 * sum(dev_scores) / len(dev_scores), 1)
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
    print(json.dumps({"output": str(out_path.resolve()), "semanticBoostCount": payload.get("semanticBoostCount")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
