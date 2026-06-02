"""Pytest fixtures for coverage validator scripts (portable cache samples)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURE_CACHE = Path(__file__).parent / "test_fixtures" / "cache"


@pytest.fixture
def fixture_repo_root(tmp_path, monkeypatch):
    """Copy minimal reports/.cache JSON into a temp repo root for link tests."""
    cache_dir = tmp_path / "reports" / ".cache"
    cache_dir.mkdir(parents=True)
    for src in FIXTURE_CACHE.glob("*.json"):
        shutil.copy(src, cache_dir / src.name)

    import confluence_requirements as cr

    monkeypatch.setattr(cr, "repo_root", lambda: tmp_path)

    yield tmp_path
