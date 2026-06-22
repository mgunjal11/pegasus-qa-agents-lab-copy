"""Shared coverage-validator workspace config (.coverage-validator.defaults.json)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULTS_FILE = ".coverage-validator.defaults.json"
VALID_VERDICT_MODES = frozenset({"pragmatic", "strict"})


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_coverage_defaults(root: Path | None = None) -> dict[str, Any]:
    base = root or repo_root()
    path = base / DEFAULTS_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_verdict_mode(root: Path | None = None, manifest: dict[str, Any] | None = None) -> str:
    """pragmatic (default) | strict — manifest overrides defaults."""
    mode = ""
    if manifest:
        mode = str(manifest.get("verdictMode") or "").strip().lower()
    if not mode:
        mode = str(load_coverage_defaults(root).get("verdictMode") or "pragmatic").strip().lower()
    if mode not in VALID_VERDICT_MODES:
        return "pragmatic"
    return mode
