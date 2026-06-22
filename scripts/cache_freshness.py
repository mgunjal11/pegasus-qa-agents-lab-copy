"""Validate coverage-validator cache freshness (mapping vs upstream inputs)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UPSTREAM_CACHE_SUFFIXES = ("prefetch", "jira", "testplan", "confluence")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_fetched_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def cache_timestamp(path: Path) -> datetime | None:
    """Best-effort cache time from JSON fetchedAt or file mtime."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    parsed = _parse_fetched_at(str(data.get("fetchedAt") or ""))
    if parsed:
        return parsed
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def is_mapping_stale(
    issue_key: str,
    root: Path | None = None,
    *,
    max_age_hours: int = 24,
) -> tuple[bool, str]:
    """
    Mapping is stale when missing, older than any upstream cache, or past max_age_hours.
    """
    base = root or repo_root()
    key = issue_key.upper()
    cache_dir = base / "reports" / ".cache"
    mapping_path = cache_dir / f"{key}-mapping.json"
    if not mapping_path.exists():
        return True, "mapping cache missing"

    mapping_at = cache_timestamp(mapping_path)
    if not mapping_at:
        return True, "mapping cache unreadable"

    now = datetime.now(timezone.utc)
    age_h = (now - mapping_at).total_seconds() / 3600
    if age_h > max_age_hours:
        return True, f"mapping older than {max_age_hours}h"

    for suffix in UPSTREAM_CACHE_SUFFIXES:
        up_path = cache_dir / f"{key}-{suffix}.json"
        up_at = cache_timestamp(up_path)
        if up_at and up_at > mapping_at:
            return True, f"{suffix} cache newer than mapping"

    return False, "mapping cache fresh"


def ensure_fresh_mapping(
    issue_key: str,
    root: Path | None = None,
    *,
    force: bool = False,
    max_age_hours: int = 24,
) -> str:
    """Re-run map_requirements_to_diff when stale or force=True. Returns action note."""
    stale, reason = is_mapping_stale(issue_key, root, max_age_hours=max_age_hours)
    if not force and not stale:
        return f"skipped mapping ({reason})"

    from map_requirements_to_diff import map_requirements, mapping_cache_path

    payload = map_requirements(issue_key.upper(), root=root)
    out = mapping_cache_path(issue_key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    action = "remapped (forced)" if force else f"remapped ({reason})"
    return action


def load_manifest_max_age(issue_key: str, root: Path | None = None) -> int:
    base = root or repo_root()
    path = base / "reports" / ".cache" / f"{issue_key.upper()}-manifest.json"
    if not path.exists():
        return 24
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 24
    try:
        return int(data.get("cacheMaxAgeHours") or 24)
    except (TypeError, ValueError):
        return 24


def is_prefetch_fresh(
    issue_key: str,
    pr_urls: list[str],
    root: Path | None = None,
    *,
    max_age_hours: int = 24,
) -> tuple[bool, str]:
    """Prefetch cache matches PR URLs and is within max_age_hours."""
    base = root or repo_root()
    key = issue_key.upper()
    path = base / "reports" / ".cache" / f"{key}-prefetch.json"
    if not path.exists():
        return False, "prefetch cache missing"

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "prefetch cache unreadable"

    cached_urls = sorted(str(u).strip() for u in (data.get("prUrls") or []) if u)
    wanted = sorted(str(u).strip() for u in pr_urls if u)
    if cached_urls != wanted:
        return False, "prefetch PR URL list changed"

    fetched = cache_timestamp(path)
    if not fetched:
        return False, "prefetch timestamp missing"

    age_h = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
    if age_h > max_age_hours:
        return False, f"prefetch older than {max_age_hours}h"

    return True, "prefetch cache fresh"
