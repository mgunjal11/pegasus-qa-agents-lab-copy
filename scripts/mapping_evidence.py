"""Stronger requirement-to-PR evidence: symbols, pytest names, ranked file paths."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiffContext:
    blob: str
    symbols: set[str] = field(default_factory=set)
    test_functions: set[str] = field(default_factory=set)
    changed_test_files: list[str] = field(default_factory=list)


def extract_diff_context(
    diff_blob: str,
    prod_files: list[str],
    test_files: list[str],
) -> DiffContext:
    """Parse PR diff: production symbols and pytest functions from added lines only."""
    symbols: set[str] = set()
    tests: set[str] = set()
    for line in diff_blob.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for m in re.finditer(r"^\+\s*(?:async\s+)?def\s+(\w+)", line):
            name = m.group(1)
            if name.startswith("test_"):
                tests.add(name)
            else:
                symbols.add(name)
        for m in re.finditer(r"^\+\s*class\s+(\w+)", line):
            symbols.add(m.group(1))
    return DiffContext(
        blob=diff_blob,
        symbols=symbols,
        test_functions=tests,
        changed_test_files=list(dict.fromkeys(test_files)),
    )


def _overlap_score(req_tokens: list[str], haystack: str) -> float:
    if not req_tokens or not haystack:
        return 0.0
    norm = haystack.lower()
    hits = sum(1 for t in req_tokens if t in norm)
    return hits / max(len(req_tokens), 1)


def _symbol_match_score(req_tokens: list[str], symbols: set[str]) -> float:
    if not symbols or not req_tokens:
        return 0.0
    hits = 0
    for sym in symbols:
        low = sym.lower()
        parts = re.split(r"[_\W]+", low)
        if any(t in low or t in parts for t in req_tokens if len(t) >= 4):
            hits += 1
    return min(1.0, hits * 0.25)


def _match_test_functions(req_tokens: list[str], test_functions: set[str]) -> list[str]:
    """Match requirement tokens to pytest functions added/changed in the PR diff."""
    matched: list[str] = []
    for name in sorted(test_functions):
        hay = name.replace("_", " ")
        if _overlap_score(req_tokens, hay) >= 0.25 or _overlap_score(req_tokens, name) >= 0.2:
            matched.append(name)
    return matched


def _is_weak_evidence_path(path: str) -> bool:
    low = path.lower()
    name = Path(path).name.lower()
    if name == "conftest.py":
        return True
    if name.endswith(".json"):
        return True
    return "samples/" in low or "/fixtures/" in low or "/data/" in low


def _is_production_path(path: str) -> bool:
    if _is_weak_evidence_path(path):
        return False
    low = path.replace("\\", "/").lower()
    if "/tests/" in low or "/test/" in low or low.startswith("tests/"):
        return False
    if "/src/" in low or low.startswith("src/"):
        return True
    name = Path(path).name.lower()
    return not (name.startswith("test_") or name.endswith("_test.py"))


def _is_test_module_path(path: str) -> bool:
    if _is_weak_evidence_path(path):
        return False
    low = path.replace("\\", "/").lower()
    return "/tests/" in low or "/test/" in low or Path(path).stem.startswith("test_")


def rank_matched_files(paths: list[str], *, limit: int = 5) -> list[str]:
    """Prefer src/ and real test modules over fixtures/samples/conftest."""
    seen: set[str] = set()
    unique: list[str] = []
    for p in paths:
        if p and p not in seen:
            seen.add(p)
            unique.append(p)

    def sort_key(p: str) -> tuple[int, str]:
        if _is_production_path(p):
            return (0, p)
        if _is_test_module_path(p):
            return (1, p)
        if _is_weak_evidence_path(p):
            return (3, p)
        return (2, p)

    return sorted(unique, key=sort_key)[:limit]


def _negative_requirement(text: str) -> bool:
    return bool(
        re.search(
            r"\b(not attached|must not|shall not|without|no longer|expected\)|not expected to)\b",
            text or "",
            re.I,
        )
    )


def _filter_tests_for_requirement_polarity(text: str, matched_tests: list[str]) -> list[str]:
    """For 'passport not attached' style AC, generic passport tests are not proof."""
    if not _negative_requirement(text):
        return matched_tests
    markers = ("not", "skip", "without", "missing", "absent", "no_", "deny", "exclude", "drop")
    filtered = [t for t in matched_tests if any(m in t.lower() for m in markers)]
    return filtered


def score_requirement_evidence(
    text: str,
    req_tokens: list[str],
    ctx: DiffContext,
    prod_files: list[str],
    test_files: list[str],
    path_tokens: list[str],
) -> dict[str, object]:
    """Score requirement against PR diff — production code and pytest bodies in diff."""
    token_code = _overlap_score(req_tokens, ctx.blob)
    symbol_score = _symbol_match_score(req_tokens, ctx.symbols)
    matched_tests = _match_test_functions(req_tokens, ctx.test_functions)
    matched_tests = _filter_tests_for_requirement_polarity(text, matched_tests)

    test_name_score = min(1.0, len(matched_tests) * 0.4)
    test_path_hay = "\n".join(test_files)
    token_test_paths = _overlap_score(req_tokens, test_path_hay) * 0.35

    code_score = min(1.0, token_code * 0.5 + symbol_score * 0.5)
    test_score = min(1.0, test_name_score * 0.75 + token_test_paths * 0.25)

    path_hits: list[str] = []
    for f in prod_files:
        if any(t in f.lower() for t in path_tokens):
            path_hits.append(f)
    for f in test_files:
        if any(t in f.lower() for t in path_tokens) and f not in path_hits:
            path_hits.append(f)
    for tn in matched_tests:
        for f in test_files:
            if tn in Path(f).name.lower() and f not in path_hits:
                path_hits.append(f)

    matched_files = rank_matched_files(path_hits, limit=5)
    prod_hits = [f for f in matched_files if _is_production_path(f)]
    test_hits = [f for f in matched_files if _is_test_module_path(f)]

    return {
        "codeScore": code_score,
        "testScore": test_score,
        "matchedFiles": matched_files,
        "matchedTests": matched_tests[:5],
        "matchedSymbols": sorted(
            s for s in ctx.symbols if any(t in s.lower() for t in req_tokens if len(t) >= 4)
        )[:5],
        "prodFileHits": prod_hits,
        "testModuleHits": test_hits,
        "testsInDiff": bool(matched_tests),
        "testFilesInPr": bool(test_files),
    }


def pr_gated_code_status(code_score: float, prod_file_hits: list[str]) -> str:
    """Implemented requires at least one production file from the PR in matched evidence."""
    if not prod_file_hits:
        if code_score >= 0.2:
            return "partial"
        return "missing"
    if code_score >= 0.35:
        return "implemented"
    if code_score >= 0.15:
        return "partial"
    return "missing"


def pr_gated_dev_test_status(
    test_score: float,
    *,
    matched_tests: list[str],
    test_module_hits: list[str],
    test_files_in_pr: bool,
) -> str:
    """Covered requires a matching pytest function added/changed in the PR diff."""
    if matched_tests:
        if test_score >= 0.3:
            return "covered"
        return "partial"
    if test_module_hits or test_files_in_pr:
        if test_score >= 0.12:
            return "partial"
    return "missing"
