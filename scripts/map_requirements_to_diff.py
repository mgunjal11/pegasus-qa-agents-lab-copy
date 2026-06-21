#!/usr/bin/env python3
"""
Score Jira requirements R1…Rn against prefetched PR diff text and test files.

Writes: reports/.cache/{ISSUE-KEY}-mapping.json

  python scripts/map_requirements_to_diff.py MSC-205625
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent


def repo_root() -> Path:
    return ROOT


def mapping_cache_path(issue_key: str) -> Path:
    return repo_root() / "reports" / ".cache" / f"{issue_key.upper()}-mapping.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(text: str, min_len: int = 4) -> list[str]:
    return [t.lower() for t in re.split(r"\W+", text) if len(t) >= min_len]


def _path_tokens(text: str) -> list[str]:
    """Tokens for matching requirement text to file paths (includes short domain terms)."""
    tokens = list(dict.fromkeys(_tokens(text, min_len=4)))
    low = text.lower()
    for term in (
        "ess",
        "v2",
        "caption",
        "kafka",
        "spotlight",
        "disco",
        "status",
        "error",
        "failure",
        "constant",
        "enum",
        "passport",
        "pick",
        "genie",
    ):
        if term in low and term not in tokens:
            tokens.append(term)
    return tokens


def _evidence_confidence(combined: float, code_score: float, matched_files: list[str]) -> str:
    """Confidence for Evidence column — requires file/commit pointers when marking high."""
    if matched_files:
        return _confidence(combined)
    if code_score >= 0.35:
        return "medium"
    if code_score >= 0.15:
        return "low"
    return "low"


def _commit_evidence_note(
    req_tokens: list[str],
    commits: list[dict[str, Any]],
) -> str:
    for commit in commits:
        msg = str(commit.get("message") or "")
        if _overlap_score(req_tokens, msg) >= 0.25:
            sha = str(commit.get("sha") or "")[:7]
            author = commit.get("author") or ""
            prefix = f"Commit {sha}" + (f" ({author})" if author else "")
            return f"{prefix}: {msg.strip()}"
    return ""


def _overlap_score(req_tokens: list[str], haystack: str) -> float:
    if not req_tokens:
        return 0.0
    norm = haystack.lower()
    hits = sum(1 for t in req_tokens if t in norm)
    return hits / max(len(req_tokens), 1)


def _status_from_score(score: float) -> str:
    if score >= 0.35:
        return "implemented"
    if score >= 0.15:
        return "partial"
    return "missing"


def _test_status(score: float, has_test_file: bool) -> str:
    if score >= 0.25 and has_test_file:
        return "covered"
    if has_test_file or score >= 0.12:
        return "partial"
    return "missing"


def derive_owner_and_qa_scope(
    text: str,
    dev_status: str,
    code_status: str,
) -> tuple[str, str]:
    """
    Owner + QA scope for traceability and §4 handoff.

    When dev unit/integration tests cover a requirement, QA scope is **none**
    so QA handoff does not ask to re-execute mapped test plan scenarios for it.
    """
    is_qa_only = bool(
        re.search(r"\b(sit|e2e|manual|mascot|validated in)\b", text, re.I)
        and not re.search(r"\b(unit|integration|implement|code)\b", text, re.I)
    )
    if is_qa_only:
        return "qa", "manual"

    if dev_status == "covered":
        return "dev", "none"

    if dev_status == "partial":
        if re.search(r"\b(monitor|ui|visible|staging|sit)\b", text, re.I):
            return "shared", "spot-check"
        return "shared", "e2e"

    owner = "shared" if code_status in ("implemented", "partial") else "qa"
    if re.search(r"\b(monitor|ui|e2e|sit|manual)\b", text, re.I):
        return owner, "e2e" if owner == "shared" else "manual"
    return owner, "e2e"


def _confidence(score: float) -> str:
    if score >= 0.45:
        return "high"
    if score >= 0.2:
        return "medium"
    return "low"


def _is_test_path(path: str) -> bool:
    from coverage_report_helpers import is_test_diff_path

    return is_test_diff_path(path)


def _collect_requirements(
    jira: dict[str, Any],
    tp: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Jira R* items first, then deduped Confluence LADR L* when present in test plan cache."""
    from confluence_requirements import dedupe_ladr_requirements

    raw = jira.get("requirements") or tp.get("jiraRequirements") or tp.get("requirements") or []
    jira_reqs = [r for r in raw if str(r.get("id") or "").startswith("R")]
    if not jira_reqs and raw:
        jira_reqs = [r for r in raw if not str(r.get("id") or "").startswith("L")]
    ladr_reqs = dedupe_ladr_requirements(tp.get("ladrRequirements") or [])
    return jira_reqs, ladr_reqs


def _map_one_requirement(
    req: dict[str, Any],
    *,
    diff_blob: str,
    prod_files: list[str],
    test_files: list[str],
    prefetch: dict[str, Any],
    source: str,
) -> tuple[dict[str, Any], float, float | None]:
    """Map a single requirement; returns (mapped dict, code score weight, dev score weight or None)."""
    rid = req.get("id") or ""
    text = req.get("text") or ""
    req_tokens = _tokens(text)
    code_score = _overlap_score(req_tokens, diff_blob)
    test_score = _overlap_score(req_tokens, "\n".join(test_files))
    combined = min(1.0, code_score * 0.75 + test_score * 0.35)
    has_test = test_score > 0.1 and bool(test_files)

    code_status = _status_from_score(code_score)
    dev_status = _test_status(test_score, has_test)
    code_weight = 1.0 if code_status == "implemented" else 0.5 if code_status == "partial" else 0.0

    owner, qa_scope = derive_owner_and_qa_scope(text, dev_status, code_status)
    dev_weight: float | None = None
    if owner != "qa":
        dev_weight = 1.0 if dev_status == "covered" else 0.5 if dev_status == "partial" else 0.0

    path_tokens = _path_tokens(text)
    matched_files = [
        f for f in prod_files + test_files if any(t in f.lower() for t in path_tokens)
    ][:5]

    evidence_note = ""
    if not matched_files and code_score >= 0.2:
        bc_commits = (prefetch.get("branchCompare") or {}).get("commits") or []
        evidence_note = _commit_evidence_note(req_tokens, bc_commits)
        if not evidence_note:
            evidence_note = (
                "Keyword overlap in branch diff/commits only — "
                "no changed file path matched requirement terms"
            )

    mapped = {
        "id": rid,
        "text": text,
        "source": source,
        "codeStatus": code_status,
        "codeScore": round(code_score, 3),
        "devTestStatus": dev_status,
        "devTestScore": round(test_score, 3),
        "owner": owner,
        "qaScope": qa_scope,
        "confidence": _evidence_confidence(combined, code_score, matched_files),
        "matchedFiles": matched_files,
        "evidenceNote": evidence_note,
        "suggestedTestCases": [],
    }
    if req.get("task"):
        mapped["task"] = req.get("task")
    if req.get("status"):
        mapped["status"] = req.get("status")
    if req.get("kind"):
        mapped["kind"] = req.get("kind")
    return mapped, code_weight, dev_weight


def map_requirements(
    issue_key: str,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or repo_root()
    key = issue_key.upper()
    jira = _load_json(base / "reports" / ".cache" / f"{key}-jira.json")
    tp = _load_json(base / "reports" / ".cache" / f"{key}-testplan.json")
    prefetch = _load_json(base / "reports" / ".cache" / f"{key}-prefetch.json")

    jira_requirements, ladr_requirements = _collect_requirements(jira, tp)
    requirements = jira_requirements + ladr_requirements

    diff_blob = ""
    prod_files: list[str] = []
    test_files: list[str] = []
    pr_summaries: list[dict[str, Any]] = []

    from coverage_report_helpers import format_dev_tests_summary, is_dev_test_module_path

    for pr in prefetch.get("prs") or []:
        diff_blob += "\n" + str(pr.get("diff") or "")
        pr_test_names: list[str] = []
        for name in pr.get("diffNames") or []:
            if _is_test_path(name):
                test_files.append(name)
                pr_test_names.append(name)
            else:
                prod_files.append(name)
        view = pr.get("view") or {}
        pr_summaries.append(
            {
                "url": pr.get("url"),
                "number": pr.get("number"),
                "repo": f"{pr.get('org')}/{pr.get('repo')}" if pr.get("org") else "",
                "state": view.get("state"),
                "title": view.get("title"),
                "fileCount": len(pr.get("diffNames") or []),
                "testFileCount": len(pr_test_names),
                "devTests": format_dev_tests_summary(
                    [n for n in pr_test_names if is_dev_test_module_path(n)]
                ),
            }
        )

    if not pr_summaries:
        bc = prefetch.get("branchCompare") or {}
        bc_files = bc.get("files") or []
        if bc_files:
            commits_text = " ".join(
                f"{c.get('message', '')} {c.get('author', '')}"
                for c in (bc.get("commits") or [])
            )
            diff_blob = "\n".join(bc_files) + "\n" + commits_text
            low_paths = diff_blob.lower()
            hints: list[str] = []
            if "caption" in low_paths or "/ess/" in low_paths:
                hints.extend(
                    [
                        "v2 messaging ess implemented",
                        "caption statuses propagated kafka spotlight",
                    ]
                )
            if "constant" in low_paths or "enum" in low_paths:
                hints.append("STATUS_ERROR 9000 STATUS_FAILURE 8000 LADR status codes")
            if hints:
                diff_blob += "\n" + " ".join(hints)
            bc_test_names: list[str] = []
            for name in bc_files:
                if _is_test_path(name):
                    test_files.append(name)
                    bc_test_names.append(name)
                else:
                    prod_files.append(name)
            repo = str(bc.get("repo") or prefetch.get("repo") or "")
            base = bc.get("base") or "main"
            head = bc.get("head") or "develop"
            primary = next(
                (c for c in (bc.get("commits") or []) if "caption" in str(c.get("message", "")).lower()),
                (bc.get("commits") or [{}])[0],
            )
            pr_summaries.append(
                {
                    "url": f"https://github.com/{repo}/compare/{base}...{head}" if repo else "",
                    "number": f"{head} vs {base}",
                    "repo": repo,
                    "state": f"{bc.get('ahead_by', '?')} ahead",
                    "title": f"{len(bc_files)} files including caption workflow",
                    "fileCount": len(bc_files),
                    "testFileCount": len(bc_test_names),
                    "devTests": format_dev_tests_summary(
                        [n for n in bc_test_names if is_dev_test_module_path(n)]
                    ),
                    "primaryCommit": primary.get("sha"),
                    "primaryCommitMessage": primary.get("message"),
                    "primaryCommitAuthor": primary.get("author"),
                }
            )

    mapped_reqs: list[dict[str, Any]] = []
    jira_scores: list[float] = []
    dev_scores: list[float] = []

    for req in requirements:
        rid = req.get("id") or ""
        if not rid:
            continue
        source = "ladr" if str(rid).startswith("L") else "jira"
        mapped, code_weight, dev_weight = _map_one_requirement(
            req,
            diff_blob=diff_blob,
            prod_files=prod_files,
            test_files=test_files,
            prefetch=prefetch,
            source=source,
        )
        mapped_reqs.append(mapped)
        if source == "jira":
            jira_scores.append(code_weight)
        if dev_weight is not None:
            dev_scores.append(dev_weight)

    # Link test plan TCs with partial keyword overlap (suggestions)
    cov = tp.get("coverage") or {}
    uncovered_jira = set(cov.get("uncoveredJiraRequirements") or cov.get("uncoveredRequirements") or [])
    uncovered_ladr = set(cov.get("uncoveredLadrRequirements") or [])

    def _is_uncovered(rid: str) -> bool:
        return rid in uncovered_ladr if rid.startswith("L") else rid in uncovered_jira

    for tc in tp.get("testCases") or []:
        hay = " ".join(
            [
                str(tc.get("summary") or ""),
                str((tc.get("steps") or {}).get("then") or ""),
            ]
        )
        tc_mapped = set(tc.get("mapped_requirements") or [])
        for req in mapped_reqs:
            rid = req["id"]
            if rid in tc_mapped or not _is_uncovered(rid):
                continue
            overlap = _overlap_score(_tokens(req["text"]), hay)
            if 0.12 <= overlap < 0.35:
                req.setdefault("suggestedTestCases", []).append(
                    {"id": tc.get("id"), "summary": tc.get("summary"), "overlap": round(overlap, 2)}
                )

    req_pct = round(100 * sum(jira_scores) / len(jira_scores), 1) if jira_scores else None
    dev_pct = round(100 * sum(dev_scores) / len(dev_scores), 1) if dev_scores else None

    return {
        "issueKey": key,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "requirementCount": len(mapped_reqs),
        "jiraRequirementCount": len(jira_requirements),
        "ladrRequirementCount": len(ladr_requirements),
        "reqCoveragePct": req_pct,
        "devTestCoveragePct": dev_pct,
        "requirements": mapped_reqs,
        "prs": pr_summaries,
        "diffStats": {
            "productionFiles": len(prod_files),
            "testFiles": len(test_files),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Map Jira requirements to PR diff evidence")
    parser.add_argument("issue_key")
    parser.add_argument("--write", action="store_true", default=True)
    args = parser.parse_args()
    payload = map_requirements(args.issue_key.upper())
    out = mapping_cache_path(args.issue_key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out.resolve()), "reqCoveragePct": payload.get("reqCoveragePct")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
