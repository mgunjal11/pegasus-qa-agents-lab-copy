"""
Report filename timestamp for Req2Release.

Uses the worker's local timezone by default (IST, EST, etc.).
Override via .coverage-validator.defaults.json:

  "timezone": "Asia/Kolkata",
  "timezoneLabel": "IST"
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULTS_FILE = ".coverage-validator.defaults.json"


def _load_defaults(root: Path | None = None) -> dict:
    root = root or Path.cwd()
    path = root / DEFAULTS_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def local_now(defaults: dict | None = None, root: Path | None = None) -> datetime:
    """Current time in configured IANA zone, or the laptop's local timezone."""
    cfg = defaults if defaults is not None else _load_defaults(root)
    name = cfg.get("timezone")
    if name:
        return datetime.now(ZoneInfo(name))
    # astimezone() uses OS local TZ; on Windows tzinfo is datetime.timezone (no IANA key)
    return datetime.now().astimezone()


def timezone_label(now: datetime, defaults: dict | None = None, root: Path | None = None) -> str:
    cfg = defaults if defaults is not None else _load_defaults(root)
    if cfg.get("timezoneLabel"):
        return str(cfg["timezoneLabel"]).strip()
    raw = now.tzname() or "LOCAL"
    # "India Standard Time" → IST, "Eastern Standard Time" → EST
    if " " in raw and len(raw) > 5:
        return "".join(word[0] for word in raw.split()).upper()
    return raw.replace(" ", "")


def _safe_label(label: str) -> str:
    return re.sub(r"[^\w+-]", "", label) or "LOCAL"


def report_paths(
    issue_key: str,
    defaults: dict | None = None,
    root: Path | None = None,
    reports_dir: str = "reports",
) -> tuple[Path, str, str]:
    """
    Returns (full_path, generated_date_display, timezone_label_used).
    Filename: {KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html
    """
    root = root or Path.cwd()
    cfg = defaults if defaults is not None else _load_defaults(root)
    now = local_now(cfg, root)
    ts = now.strftime("%m-%d-%Y-%H-%M-%S")
    label = _safe_label(timezone_label(now, cfg, root))
    filename = f"{issue_key.upper()}-{ts}-{label}.html"
    path = root / reports_dir / filename
    generated = f"{now.strftime('%Y-%m-%d %H:%M:%S')} {label}"
    return path, generated, label


if __name__ == "__main__":
    import sys

    key = sys.argv[1] if len(sys.argv) > 1 else "MSC-000000"
    path, generated, label = report_paths(key)
    print(path)
    print(generated)
    print(label)
