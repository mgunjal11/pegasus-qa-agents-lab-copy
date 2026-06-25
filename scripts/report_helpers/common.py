"""Shared constants and escaping for coverage report HTML."""

from __future__ import annotations

import html
import re
from typing import Any

REPORT_AGENT_NAME = "Req2Release"
REPORT_DEVELOPER = "Mayur Gunjal"

SUMMARY_MAPS_RE = re.compile(r"\(maps\s+([RL\d,\s]+)\)", re.IGNORECASE)
AUTO_GENERATED_SUMMARY_RE = re.compile(r"^MSC-\d+_.*\(maps\s+[RL\d]", re.IGNORECASE)


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def _requirement_text_lookup(
    jira_requirements: list[dict[str, str]] | None,
    ladr_requirements: list[dict[str, Any]] | None,
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for req in jira_requirements or []:
        rid = str(req.get("id") or "").strip().upper()
        text = str(req.get("text") or "").strip()
        if rid and text:
            lookup[rid] = text
    for req in ladr_requirements or []:
        rid = str(req.get("id") or "").strip().upper()
        if not rid or rid in lookup:
            continue
        text = str(req.get("text") or req.get("task") or "").strip()
        if text:
            lookup[rid] = text
    return lookup


def _primary_mapped_requirement_id(summary: str, mapped: list[Any]) -> str | None:
    match = SUMMARY_MAPS_RE.search(summary or "")
    if match:
        parts = [p.strip().upper() for p in re.split(r"[,\s]+", match.group(1)) if p.strip()]
        if parts:
            return parts[0]
    for item in mapped:
        rid = str(item).strip().upper()
        if rid:
            return rid
    return None


def format_testplan_scenario(
    tc: dict[str, Any],
    jira_requirements: list[dict[str, str]] | None = None,
    ladr_requirements: list[dict[str, Any]] | None = None,
) -> str:
    """Full scenario label for §3 Attached test plan validation (not truncated slug text)."""
    section = (tc.get("section") or "").strip()
    summary = (tc.get("summary") or "").strip()

    if section and summary:
        return f"{section} · {summary}"
    if section:
        return section

    if summary and AUTO_GENERATED_SUMMARY_RE.match(summary):
        lookup = _requirement_text_lookup(jira_requirements, ladr_requirements)
        primary = _primary_mapped_requirement_id(summary, tc.get("mapped_requirements") or [])
        if primary and lookup.get(primary):
            return lookup[primary]

    if summary:
        return summary

    return str(tc.get("id") or "")
