#!/usr/bin/env python3
"""Given/When/Then parsing — content-based, not tied to QMetry column names."""

from __future__ import annotations

import re
from typing import Any

# Common spreadsheet typos for Then (e.g. MSC-195138 TC11 uses "Than:")
GWT_TYPO_RE = re.compile(r"\b(Than|Tehn|Them)\s*:", re.IGNORECASE)
GWT_MARKER_RE = re.compile(r"(Given|When|Then)\s*:?\s*", re.IGNORECASE)
GWT_LINE_RE = re.compile(r"^(Given|When|Then|Than|Tehn|Them)\s*:?\s*", re.IGNORECASE)


def normalize_gwt_typos(text: str) -> str:
    """Normalize frequent Then misspellings before GWT parsing."""
    return GWT_TYPO_RE.sub("Then:", text)


def gwt_key_from_marker(marker: str) -> str:
    lower = marker.lower()
    if lower in {"than", "tehn", "them"}:
        return "then"
    return lower

STEP_BLOB_ALIASES: tuple[str, ...] = (
    "step summary",
    "test steps",
    "test step",
    "steps",
    "step",
    "actions",
    "procedure",
    "execution steps",
)


def is_step_blob_column(header_name: str) -> bool:
    lower = header_name.lower().strip()
    return lower in STEP_BLOB_ALIASES or any(a in lower for a in STEP_BLOB_ALIASES)


def parse_gwt_from_text(text: str) -> dict[str, str]:
    """Split free-form step text into given/when/then (any column layout)."""
    text = normalize_gwt_typos((text or "").strip())
    if not text:
        return {}

    markers = list(GWT_MARKER_RE.finditer(text))
    if not markers:
        return {}

    parsed: dict[str, str] = {}
    for i, match in enumerate(markers):
        key = gwt_key_from_marker(match.group(1))
        start = match.start()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            parsed[key] = chunk
    return parsed


def merge_steps(existing: dict[str, str], incoming: dict[str, str]) -> dict[str, str]:
    """Merge parsed steps; incoming non-empty values win."""
    out = dict(existing)
    for key, val in incoming.items():
        if val and val.strip():
            out[key] = val.strip()
    return out


def normalize_steps(steps: dict[str, str]) -> dict[str, str]:
    """Expand combined step blobs (e.g. all GWT in one 'when' cell) into given/when/then."""
    if all(steps.get(k, "").strip() for k in ("given", "when", "then")):
        return {k: steps[k].strip() for k in ("given", "when", "then") if steps.get(k, "").strip()}

    combined = "\n".join(v for v in steps.values() if v and str(v).strip())
    parsed = parse_gwt_from_text(combined)
    if parsed:
        return merge_steps(steps, parsed)

    # Single-key blob with multiple GWT markers inside one field
    for val in steps.values():
        if not val:
            continue
        parsed = parse_gwt_from_text(str(val))
        if len(parsed) >= 2:
            return merge_steps(steps, parsed)
    return {k: v.strip() for k, v in steps.items() if v and str(v).strip()}


def has_complete_gwt(steps: dict[str, str]) -> bool:
    """True when Given, When, and Then are present (any column or combined cell)."""
    normalized = normalize_steps(steps)
    if all(normalized.get(k, "").strip() for k in ("given", "when", "then")):
        return True
    combined = "\n".join(normalized.values())
    if not combined:
        combined = "\n".join(str(v) for v in steps.values() if v)
    combined = normalize_gwt_typos(combined)
    keys = {gwt_key_from_marker(m.group(1)) for m in GWT_MARKER_RE.finditer(combined)}
    return {"given", "when", "then"}.issubset(keys)


def steps_for_display(steps: dict[str, str]) -> dict[str, str]:
    """Normalize for HTML Given/When/Then column."""
    return normalize_steps(steps)
