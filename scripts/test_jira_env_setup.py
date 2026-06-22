"""Tests for .env bootstrap from .env.example."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from jira_env import ensure_env_from_example, ensure_gitignore_env  # noqa: E402


def test_ensure_gitignore_env_adds_dotenv(tmp_path: Path):
    status = ensure_gitignore_env(tmp_path)
    assert status["added"] is True
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text


def test_ensure_env_from_example_creates_file(tmp_path: Path):
    (tmp_path / ".env.example").write_text(
        "ATLASSIAN_EMAIL=test@example.com\nATLASSIAN_API_TOKEN=secret\n",
        encoding="utf-8",
    )
    status = ensure_env_from_example(tmp_path)
    assert status["created"] is True
    assert (tmp_path / ".env").exists()
    assert (tmp_path / ".gitignore").exists()
    assert "secret" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_ensure_env_from_example_does_not_overwrite(tmp_path: Path):
    (tmp_path / ".env.example").write_text("ATLASSIAN_EMAIL=a@b.com\n", encoding="utf-8")
    (tmp_path / ".env").write_text("ATLASSIAN_EMAIL=keep@me.com\n", encoding="utf-8")
    status = ensure_env_from_example(tmp_path)
    assert status["created"] is False
    assert "keep@me.com" in (tmp_path / ".env").read_text(encoding="utf-8")
