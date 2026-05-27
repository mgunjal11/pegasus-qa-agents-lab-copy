#!/usr/bin/env python3
"""HTML helpers for msc-code-coverage-validator reports."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from testplan_gwt import steps_for_display


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def render_mascot_links(links: list[dict[str, str]]) -> str:
    if not links:
        return '<span class="badge badge-not-verified">No Mascot links in test plan</span>'
    parts = []
    for link in links:
        label = esc(link.get("label") or "Mascot")
        url = esc(link.get("url") or "")
        if not url:
            continue
        parts.append(f'<a href="{url}" target="_blank">{label}</a>')
    return "<br>".join(parts) if parts else '<span class="badge badge-not-verified">No Mascot links</span>'


def render_gwt_steps(steps: dict[str, str]) -> str:
    normalized = steps_for_display(steps)
    chunks = []
    for key in ("given", "when", "then"):
        val = normalized.get(key, "")
        if val:
            chunks.append(esc(val))
    if chunks:
        return "<br>".join(chunks)
    # Fallback: show combined step text when GWT is present but not split
    combined = "\n".join(str(v) for v in steps.values() if v)
    return esc(combined) if combined.strip() else "—"


def pr_alignment_for_tc(mapped: list[str]) -> str:
    if not mapped:
        return '<span class="badge badge-not-verified">Unmapped</span>'
    reqs = ", ".join(mapped)
    return f'<span class="badge badge-implemented">Aligns</span> {esc(reqs)}'


def render_testplan_rows(test_cases: list[dict[str, Any]]) -> str:
    rows = []
    for tc in test_cases:
        steps = tc.get("steps") or {}
        section = tc.get("section") or ""
        summary = tc.get("summary") or ""
        scenario = f"{section} · {summary}" if section and summary else (section or summary or tc.get("id", ""))
        rows.append(
            f"<tr>"
            f"<td>{esc(tc.get('id', ''))}</td>"
            f"<td>{esc(scenario)}</td>"
            f"<td>{esc(', '.join(tc.get('mapped_requirements') or []) or '—')}</td>"
            f"<td>{render_gwt_steps(steps)}</td>"
            f"<td>{pr_alignment_for_tc(tc.get('mapped_requirements') or [])}</td>"
            f"<td>{render_mascot_links(tc.get('mascot_links') or [])}</td>"
            f"</tr>"
        )
    return "\n".join(rows) if rows else '<tr><td colspan="6">—</td></tr>'


def load_testplan_cache(issue_key: str, root: Path | None = None) -> dict[str, Any]:
    base = root or Path(__file__).resolve().parents[1]
    path = base / "reports" / ".cache" / f"{issue_key.upper()}-testplan.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
