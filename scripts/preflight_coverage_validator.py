#!/usr/bin/env python3
"""
One-shot preflight for msc-dev-code-and-qa-test-coverage-validator.

  python scripts/preflight_coverage_validator.py
  python scripts/preflight_coverage_validator.py MSC-205625 --verify-jira
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from coverage_validator_config import load_coverage_defaults  # noqa: E402
from jira_env import credentials_hint, jira_email, jira_token, load_dotenv  # noqa: E402


def _check_python() -> dict[str, Any]:
    ok = sys.version_info >= (3, 10)
    return {
        "id": "python",
        "label": "Python 3.10+",
        "ok": ok,
        "detail": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


def _check_openpyxl() -> dict[str, Any]:
    ok = importlib.util.find_spec("openpyxl") is not None
    return {
        "id": "openpyxl",
        "label": "openpyxl (Excel test plans)",
        "ok": ok,
        "detail": "pip install -r requirements.txt" if not ok else "installed",
    }


def _check_gh() -> dict[str, Any]:
    if not shutil.which("gh"):
        return {
            "id": "gh",
            "label": "GitHub CLI",
            "ok": False,
            "detail": "Install from https://cli.github.com then gh auth login",
        }
    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    ok = result.returncode == 0
    detail = "authenticated" if ok else (result.stderr.strip() or "run gh auth login")
    return {"id": "gh", "label": "GitHub CLI auth", "ok": ok, "detail": detail}


def _check_jira_env() -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    email = jira_email()
    token = jira_token()
    ok = bool(email and token)
    return {
        "id": "jira_env",
        "label": "Jira REST .env (attachment download)",
        "ok": ok,
        "required": False,
        "detail": credentials_hint() if not ok else f"email set ({email})",
    }


def _check_jira_verify(issue_key: str) -> dict[str, Any]:
    from jira_env import verify_credentials

    try:
        result = verify_credentials(issue_key)
    except RuntimeError as exc:
        return {
            "id": "jira_verify",
            "label": f"Jira API smoke test ({issue_key})",
            "ok": False,
            "detail": str(exc),
        }
    ok = bool(result.get("ok"))
    detail = f"attachments={result.get('attachmentCount', 0)}"
    expiry = result.get("tokenExpiry") or {}
    if expiry.get("message"):
        detail = f"{detail}; {expiry['message']}"
    return {
        "id": "jira_verify",
        "label": f"Jira API smoke test ({issue_key})",
        "ok": ok,
        "detail": detail,
    }


def _check_defaults() -> dict[str, Any]:
    defaults = load_coverage_defaults(ROOT)
    path = ROOT / ".coverage-validator.defaults.json"
    ok = path.exists()
    return {
        "id": "defaults",
        "label": ".coverage-validator.defaults.json",
        "ok": ok,
        "required": False,
        "detail": "optional — copy validator.defaults.example.json" if not ok else "present",
    }


def _check_permissions() -> dict[str, Any]:
    user_path = Path.home() / ".cursor" / "permissions.json"
    lab_path = ROOT / ".cursor" / "permissions.json"
    if not user_path.exists():
        return {
            "id": "permissions",
            "label": "Cursor auto-run allowlist",
            "ok": False,
            "required": False,
            "detail": "run python scripts/install_coverage_validator_permissions.py",
        }
    try:
        data = json.loads(user_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    needed = []
    if lab_path.exists():
        try:
            lab = json.loads(lab_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            lab = {}
        for key in ("mcpAllowlist", "terminalAllowlist"):
            for item in lab.get(key) or []:
                if item not in (data.get(key) or []):
                    needed.append(item)
    ok = len(needed) == 0
    detail = "merged" if ok else f"missing {len(needed)} allowlist entries — run install script"
    return {
        "id": "permissions",
        "label": "Cursor auto-run allowlist",
        "ok": ok,
        "required": False,
        "detail": detail,
    }


def _check_template() -> dict[str, Any]:
    tpl = ROOT / ".cursor/skills/coverage-validator/report-template.html"
    ok = tpl.exists()
    return {
        "id": "template",
        "label": "Report template",
        "ok": ok,
        "detail": str(tpl.relative_to(ROOT)) if ok else "missing skill template",
    }


def run_preflight(issue_key: str | None = None, *, verify_jira: bool = False) -> dict[str, Any]:
    checks = [
        _check_python(),
        _check_openpyxl(),
        _check_gh(),
        _check_jira_env(),
        _check_defaults(),
        _check_permissions(),
        _check_template(),
    ]
    if verify_jira and issue_key:
        checks.append(_check_jira_verify(issue_key.upper()))

    required_fail = [c for c in checks if c.get("required") is not False and not c["ok"]]
    optional_fail = [c for c in checks if c.get("required") is False and not c["ok"]]

    return {
        "ok": len(required_fail) == 0,
        "ready": len([c for c in checks if not c["ok"]]) == 0,
        "checks": checks,
        "requiredFailures": [c["id"] for c in required_fail],
        "optionalFailures": [c["id"] for c in optional_fail],
        "next": (
            f"/msc-dev-code-and-qa-test-coverage-validator {issue_key}"
            if issue_key and len(required_fail) == 0
            else "Fix required failures above, then re-run preflight"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight checks for coverage validator")
    parser.add_argument("issue_key", nargs="?", help="Optional issue key for Jira verify")
    parser.add_argument(
        "--verify-jira",
        action="store_true",
        help="Smoke-test Jira REST credentials against issue_key",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    report = run_preflight(args.issue_key, verify_jira=args.verify_jira or bool(args.issue_key))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps(report, indent=2))
        for check in report["checks"]:
            mark = "OK" if check["ok"] else "FAIL"
            req = "" if check.get("required") is False else " (required)"
            print(f"  [{mark}] {check['label']}{req}: {check['detail']}")
        print(report["next"])

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
