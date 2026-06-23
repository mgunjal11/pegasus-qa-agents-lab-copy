#!/usr/bin/env python3
"""Jira REST auth helpers for coverage-validator scripts (.env + Basic auth)."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_gitignore_env(root: Path | None = None) -> dict[str, Any]:
    """Ensure repo .gitignore lists .env (credentials must not be committed)."""
    base = root or repo_root()
    ignore_path = base / ".gitignore"
    entry = ".env"
    if not ignore_path.exists():
        ignore_path.write_text(f"{entry}\n", encoding="utf-8")
        return {"path": str(ignore_path), "added": True, "created": True}
    text = ignore_path.read_text(encoding="utf-8")
    lines = {ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")}
    if entry in lines:
        return {"path": str(ignore_path), "added": False, "created": False}
    suffix = "" if text.endswith("\n") or not text else "\n"
    ignore_path.write_text(f"{text}{suffix}{entry}\n", encoding="utf-8")
    return {"path": str(ignore_path), "added": True, "created": False}


def ensure_env_from_example(root: Path | None = None) -> dict[str, Any]:
    """
    Copy .env.example → .env when .env is missing (never overwrite existing .env).

    Returns {"created": bool, "envPath": str, "examplePath": str | None, "message": str}.
    """
    import shutil

    base = root or repo_root()
    env_path = base / ".env"
    example_path = base / ".env.example"
    ensure_gitignore_env(base)

    if env_path.exists():
        return {
            "created": False,
            "envPath": str(env_path),
            "examplePath": str(example_path) if example_path.exists() else None,
            "message": ".env already exists — edit credentials in place (not committed to git)",
        }
    if not example_path.exists():
        return {
            "created": False,
            "envPath": str(env_path),
            "examplePath": None,
            "message": ".env.example missing — create .env manually with ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN",
        }
    shutil.copy2(example_path, env_path)
    return {
        "created": True,
        "envPath": str(env_path),
        "examplePath": str(example_path),
        "message": "Created .env from .env.example — set ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN",
    }


def load_dotenv(path: Path | None = None) -> bool:
    """Load KEY=VALUE pairs from repo .env into os.environ (does not override existing)."""
    env_path = path or repo_root() / ".env"
    if not env_path.exists():
        return False
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    return True


def jira_email() -> str | None:
    return os.environ.get("ATLASSIAN_EMAIL") or os.environ.get("JIRA_EMAIL")


def jira_token() -> str | None:
    return os.environ.get("ATLASSIAN_API_TOKEN") or os.environ.get("JIRA_API_TOKEN")


def jira_auth_header() -> dict[str, str] | None:
    email = jira_email()
    token = jira_token()
    if not email or not token:
        return None
    raw = f"{email}:{token}".encode()
    return {"Authorization": f"Basic {base64.b64encode(raw).decode()}"}


def jira_token_expires() -> str | None:
    return os.environ.get("ATLASSIAN_API_TOKEN_EXPIRES") or os.environ.get("JIRA_API_TOKEN_EXPIRES")


def jira_token_expiry_status() -> dict[str, Any] | None:
    """Return expiry metadata from .env (optional reminder fields)."""
    raw = jira_token_expires()
    if not raw:
        return None
    from datetime import date

    try:
        expires = date.fromisoformat(raw.strip())
    except ValueError:
        return {"expires": raw, "valid": False, "message": f"Invalid ATLASSIAN_API_TOKEN_EXPIRES: {raw!r} (use YYYY-MM-DD)"}
    today = date.today()
    days_left = (expires - today).days
    if days_left < 0:
        return {
            "expires": raw,
            "valid": False,
            "expired": True,
            "daysLeft": days_left,
            "message": f"ATLASSIAN_API_TOKEN expired on {raw}. Create a new token (365 days) at id.atlassian.com.",
        }
    if days_left <= 30:
        return {
            "expires": raw,
            "valid": True,
            "expired": False,
            "daysLeft": days_left,
            "message": f"Token expires in {days_left} day(s) on {raw}. Plan renewal at id.atlassian.com.",
        }
    return {"expires": raw, "valid": True, "expired": False, "daysLeft": days_left}


def credentials_hint() -> str:
    return (
        "Set ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN in .env (copy .env.example) "
        "or export them in your shell."
    )


def jira_get(url: str, timeout: int = 120) -> bytes:
    headers = jira_auth_header()
    if not headers:
        raise RuntimeError(f"Jira credentials missing. {credentials_hint()}")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"Jira HTTP {exc.code}: {body[:400]}") from exc


def jira_request(
    url: str,
    method: str = "GET",
    data: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
    timeout: int = 120,
) -> bytes:
    headers = jira_auth_header() or {}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"Jira HTTP {exc.code}: {body[:400]}") from exc


def probe_github_repo(org: str, repo: str) -> dict[str, Any]:
    """Return whether the current gh auth can read org/repo (multi-org prefetch preflight)."""
    import shutil
    import subprocess

    full = f"{org}/{repo}"
    if not shutil.which("gh"):
        return {"repo": full, "ok": False, "detail": "GitHub CLI not installed"}
    result = subprocess.run(
        ["gh", "api", f"repos/{org}/{repo}", "--jq", ".full_name"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0 and result.stdout.strip():
        return {"repo": full, "ok": True, "detail": result.stdout.strip()}
    err = (result.stderr or result.stdout or "").strip()
    hint = ""
    low = err.lower()
    if "not found" in low or "404" in low:
        hint = (
            f" Authorize org access: gh auth refresh -h github.com -s read:org,repo "
            f"then approve SSO for {org} at https://github.com/orgs/{org}"
        )
    return {"repo": full, "ok": False, "detail": err or "repository not accessible", "hint": hint}


def fetch_issue_attachments(issue_key: str, site: str = "wbdstreaming.atlassian.net") -> list[dict[str, Any]]:
    url = f"https://{site}/rest/api/3/issue/{issue_key}?fields=attachment"
    data = json.loads(jira_get(url).decode())
    return data.get("fields", {}).get("attachment") or []


def download_attachment(att: dict[str, Any], dest_dir: Path) -> Path:
    content_url = att.get("content")
    filename = att.get("filename") or f"attachment-{att.get('id', 'unknown')}"
    if not content_url:
        raise RuntimeError(f"No content URL for attachment {filename}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(jira_get(content_url))
    return dest


def upload_attachment(
    issue_key: str,
    file_path: Path,
    site: str = "wbdstreaming.atlassian.net",
) -> list[dict[str, Any]]:
    """Upload a file to a Jira issue; returns attachment metadata from Jira."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)
    headers = jira_auth_header()
    if not headers:
        raise RuntimeError(f"Jira credentials missing. {credentials_hint()}")

    boundary = f"----CursorBoundary{uuid.uuid4().hex}"
    filename = path.name
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if path.suffix.lower() == ".tsv":
        content_type = "text/tab-separated-values"
    elif path.suffix.lower() == ".csv":
        content_type = "text/csv"

    file_bytes = path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"https://{site}/rest/api/3/issue/{issue_key}/attachments"
    headers = dict(headers)
    headers["X-Atlassian-Token"] = "no-check"
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

    raw = jira_request(url, method="POST", data=body, extra_headers=headers)
    result = json.loads(raw.decode())
    if not isinstance(result, list):
        raise RuntimeError(f"Unexpected upload response: {raw[:200]!r}")
    return result


def verify_credentials(issue_key: str = "MSC-205625", site: str = "wbdstreaming.atlassian.net") -> dict[str, Any]:
    """Smoke-test Jira API auth; returns issue summary + attachment count."""
    load_dotenv()
    url = f"https://{site}/rest/api/3/issue/{issue_key}?fields=summary,attachment"
    data = json.loads(jira_get(url).decode())
    fields = data.get("fields") or {}
    attachments = fields.get("attachment") or []
    result: dict[str, Any] = {
        "ok": True,
        "issueKey": data.get("key", issue_key),
        "summary": fields.get("summary"),
        "attachmentCount": len(attachments),
        "attachments": [{"filename": a.get("filename"), "size": a.get("size")} for a in attachments],
        "email": jira_email(),
    }
    expiry = jira_token_expiry_status()
    if expiry:
        result["tokenExpiry"] = expiry
        if expiry.get("expired"):
            result["ok"] = False
            result["error"] = expiry.get("message")
    return result
