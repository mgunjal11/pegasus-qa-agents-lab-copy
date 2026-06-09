#!/usr/bin/env python3
"""Extract test-plan evidence IDs when Mascot links are absent."""

from __future__ import annotations

import re
from typing import Any

UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

LABELED_ID_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?:edit\s*id|editid)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")", re.I), "Edit ID"),
    (
        re.compile(
            r"(?:media\s*request(?:\s*id)?|mediarequest)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")",
            re.I,
        ),
        "Media Request",
    ),
    (re.compile(r"(?:job\s*id|jobid)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")", re.I), "Job ID"),
    (re.compile(r"(?:request\s*id|requestid)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")", re.I), "Request ID"),
    (
        re.compile(
            r"(?:fulfillment(?:\s*id)?|fulfilment(?:\s*id)?)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")",
            re.I,
        ),
        "Fulfillment ID",
    ),
    (re.compile(r"(?:manifestation\s*id)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")", re.I), "Manifestation ID"),
    (re.compile(r"(?:asset\s*id)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")", re.I), "Asset ID"),
    (re.compile(r"(?:work\s*order\s*id)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")", re.I), "Work Order ID"),
    (
        re.compile(
            r"(?:caption\s*group\s*id|captiongroupid)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")",
            re.I,
        ),
        "Caption Group ID",
    ),
    (
        re.compile(r"(?:pegasus\s*id|pegasusid)\s*[:=\-]?\s*(" + UUID_RE.pattern + r")", re.I),
        "Pegasus ID",
    ),
)


def _add_item(items: list[dict[str, str]], seen: set[str], label: str, value: str) -> None:
    key = value.lower()
    if key in seen:
        return
    seen.add(key)
    items.append({"label": label, "value": value})


def extract_labeled_ids(text: str) -> list[dict[str, str]]:
    """Parse Edit ID, Job ID, Media Request, and other labeled UUIDs from free text."""
    if not text or not str(text).strip():
        return []
    blob = str(text)
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern, label in LABELED_ID_RULES:
        for match in pattern.finditer(blob):
            _add_item(items, seen, label, match.group(1))
    return items


def extract_bare_uuids(text: str, *, exclude_mascot_urls: bool = True) -> list[dict[str, str]]:
    """Collect standalone UUIDs not already captured with a label."""
    if not text:
        return []
    blob = str(text)
    if exclude_mascot_urls:
        blob = re.sub(r"https?://[^\s\"']+", " ", blob)
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in UUID_RE.findall(blob):
        _add_item(items, seen, "ID", value)
    return items


EVIDENCE_TEXT_COLUMN_HINTS: tuple[str, ...] = (
    "sit jobs",
    "qa jobs",
    "sit job",
    "qa job",
    "edit id",
    "job id",
    "request id",
    "media request",
    "test data",
    "evidence",
    "comments",
    "comment",
    "mascot",
    "execution",
    "sit status",
    "qa status",
)


def evidence_column_indices(header: list[str]) -> list[int]:
    """Column indexes that may hold Edit/Job/UUID evidence (e.g. SIT Jobs on Caption Monitoring)."""
    indices: list[int] = []
    seen: set[int] = set()
    for idx, name in enumerate(header):
        lower = re.sub(r"\s+", " ", (name or "").strip().lower())
        if not lower:
            continue
        if any(hint in lower for hint in EVIDENCE_TEXT_COLUMN_HINTS):
            if idx not in seen:
                seen.add(idx)
                indices.append(idx)
    return indices


def row_evidence_text(header: list[str], row: list[str], extra_indices: list[int] | None = None) -> str:
    """Join evidence-bearing cells from a spreadsheet row for ID extraction."""
    indices = list(extra_indices or evidence_column_indices(header))
    comment_idx = next((i for i, h in enumerate(header) if h.strip().lower() == "comment"), None)
    comments_idx = next((i for i, h in enumerate(header) if h.strip().lower() == "comments"), None)
    for idx in (comment_idx, comments_idx):
        if idx is not None and idx not in indices:
            indices.append(idx)
    parts: list[str] = []
    for idx in indices:
        if idx >= len(row):
            continue
        val = str(row[idx] or "").strip()
        if not val:
            continue
        col = (header[idx] if idx < len(header) else "").strip()
        parts.append(val if not col or val.lower().startswith(col.lower()) else f"{col}: {val}")
    return "\n".join(parts)


def testcase_haystack(tc: Any, *, include_steps: bool = True) -> str:
    if isinstance(tc, dict):
        parts = [
            tc.get("summary") or "",
            tc.get("comment") or "",
            tc.get("evidence_text") or "",
            tc.get("section") or "",
            tc.get("story") or "",
        ]
        if include_steps:
            steps = tc.get("steps") or {}
            parts.extend(str(v) for v in steps.values() if v)
        return " ".join(parts)
    parts = [
        getattr(tc, "summary", "") or "",
        getattr(tc, "comment", "") or "",
        getattr(tc, "evidence_text", "") or "",
        getattr(tc, "section", "") or "",
        getattr(tc, "story", "") or "",
    ]
    if include_steps:
        steps = getattr(tc, "steps", None) or {}
        parts.extend(str(v) for v in steps.values() if v)
    return " ".join(parts)


def extract_testcase_evidence_ids(
    tc: Any,
    jira_requirements: list[dict[str, str]] | None = None,
    *,
    include_steps: bool = True,
) -> list[dict[str, str]]:
    """
    Evidence IDs from test plan evidence columns / text, then mapped Jira AC text.
    When include_steps is False (locally generated QMetry plans), step/summary UUIDs
    are ignored — only evidence_text, comment, and Jira AC fallback apply.
    """
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    haystack = testcase_haystack(tc, include_steps=include_steps)
    for item in extract_labeled_ids(haystack):
        _add_item(items, seen, item["label"], item["value"])
    for item in extract_bare_uuids(haystack):
        _add_item(items, seen, item["label"], item["value"])

    mapped = tc.get("mapped_requirements") if isinstance(tc, dict) else getattr(tc, "mapped_requirements", None)
    mapped = mapped or []
    if jira_requirements and mapped:
        req_by_id = {r.get("id"): r.get("text") or "" for r in jira_requirements if r.get("id")}
        for rid in mapped:
            req_text = req_by_id.get(rid) or ""
            for item in extract_labeled_ids(req_text):
                _add_item(items, seen, f'{item["label"]} ({rid})', item["value"])
            for item in extract_bare_uuids(req_text):
                _add_item(items, seen, f'ID ({rid})', item["value"])
    return items


def has_mascot_links(tc: Any) -> bool:
    links = tc.get("mascot_links") if isinstance(tc, dict) else getattr(tc, "mascot_links", None)
    return bool(links and any((lnk.get("url") if isinstance(lnk, dict) else "") for lnk in links or []))
