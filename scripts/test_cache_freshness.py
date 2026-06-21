"""Tests for mapping cache freshness."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cache_freshness import is_mapping_stale  # noqa: E402


def test_mapping_stale_when_prefetch_newer(tmp_path):
    key = "MSC-TEST"
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    new = datetime.now(timezone.utc)
    (cache / f"{key}-mapping.json").write_text(
        json.dumps({"fetchedAt": old.isoformat()}),
        encoding="utf-8",
    )
    (cache / f"{key}-prefetch.json").write_text(
        json.dumps({"fetchedAt": new.isoformat()}),
        encoding="utf-8",
    )
    stale, reason = is_mapping_stale(key, tmp_path)
    assert stale
    assert "prefetch" in reason


def test_mapping_fresh_when_newest(tmp_path):
    key = "MSC-TEST"
    cache = tmp_path / "reports" / ".cache"
    cache.mkdir(parents=True)
    now = datetime.now(timezone.utc)
    (cache / f"{key}-mapping.json").write_text(
        json.dumps({"fetchedAt": now.isoformat()}),
        encoding="utf-8",
    )
    (cache / f"{key}-prefetch.json").write_text(
        json.dumps({"fetchedAt": (now - timedelta(hours=1)).isoformat()}),
        encoding="utf-8",
    )
    stale, reason = is_mapping_stale(key, tmp_path, max_age_hours=24)
    assert not stale
    assert "fresh" in reason
