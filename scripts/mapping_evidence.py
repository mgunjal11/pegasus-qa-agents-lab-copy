"""Stronger requirement-to-PR evidence: symbols, test names, ranked file paths."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiffContext:
    blob: str
    symbols: set[str] = field(default_factory=set)
    test_functions: set[str] = field(default_factory=set)


def extract_diff_context(
    diff_blob: str,
    prod_files: list[str],
    test_files: list[str],
) -> DiffContext:
    """Parse added lines for def/class/test names plus test module stems."""
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
    for path in test_files:
        stem = Path(path).stem
        if stem.startswith("test_"):
            tests.add(stem)
    return DiffContext(blob=diff_blob, symbols=symbols, test_functions=tests)


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
    matched: list[str] = []
    for name in sorted(test_functions):
        hay = name.replace("_", " ")
        if _overlap_score(req_tokens, hay) >= 0.2 or _overlap_score(req_tokens, name) >= 0.15:
            matched.append(name)
    return matched


def _is_weak_evidence_path(path: str) -> bool:
    low = path.lower()
    name = Path(path).name.lower()
    if name == "conftest.py":
        return True
    if name.endswith(".json"):
        return True
    return "samples/" in low or "/fixtures/" in low


def rank_matched_files(paths: list[str], *, limit: int = 5) -> list[str]:
    """Prefer src/ and real test modules over fixtures/samples/conftest."""
    seen: set[str] = set()
    unique: list[str] = []
    for p in paths:
        if p and p not in seen:
            seen.add(p)
            unique.append(p)

    def sort_key(p: str) -> tuple[int, str]:
        low = p.lower()
        if _is_weak_evidence_path(p):
            return (2, p)
        if "/src/" in low or low.startswith("src/"):
            return (0, p)
        if "/unit/" in low or "/integration/" in low or "/test" in low:
            return (0, p)
        return (1, p)

    return sorted(unique, key=sort_key)[:limit]


def score_requirement_evidence(
    text: str,
    req_tokens: list[str],
    ctx: DiffContext,
    prod_files: list[str],
    test_files: list[str],
    path_tokens: list[str],
) -> dict[str, object]:
    """Blend token overlap with symbol and pytest-name matches."""
    token_code = _overlap_score(req_tokens, ctx.blob)
    token_test = _overlap_score(req_tokens, "\n".join(test_files))
    symbol_score = _symbol_match_score(req_tokens, ctx.symbols)
    matched_tests = _match_test_functions(req_tokens, ctx.test_functions)
    test_name_score = min(1.0, len(matched_tests) * 0.35)

    code_score = min(1.0, token_code * 0.5 + symbol_score * 0.5)
    test_score = min(1.0, token_test * 0.4 + test_name_score * 0.6)

    path_hits = [
        f for f in prod_files + test_files if any(t in f.lower() for t in path_tokens)
    ]
    for tn in matched_tests:
        for f in test_files:
            if tn in Path(f).name.lower() and f not in path_hits:
                path_hits.append(f)

    matched_files = rank_matched_files(path_hits, limit=5)

    return {
        "codeScore": code_score,
        "testScore": test_score,
        "matchedFiles": matched_files,
        "matchedTests": matched_tests[:5],
        "matchedSymbols": sorted(
            s for s in ctx.symbols if any(t in s.lower() for t in req_tokens if len(t) >= 4)
        )[:5],
    }
