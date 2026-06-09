#!/usr/bin/env python3
"""
Build testcases/{KEY}-testcases.xlsx from a cache TSV (not stored in testcases/).

Default input: reports/.cache/{KEY}-testcases-source.tsv
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def cache_tsv_path(issue_key: str, root: Path | None = None) -> Path:
    base = root or repo_root()
    return base / "reports" / ".cache" / f"{issue_key.upper()}-testcases-source.tsv"


def xlsx_path(issue_key: str, root: Path | None = None) -> Path:
    base = root or repo_root()
    return base / "testcases" / f"{issue_key.upper()}-testcases.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write QMetry Excel only (no testcases/*.tsv)")
    parser.add_argument("issue_key", help="Jira issue key, e.g. MSC-209330")
    parser.add_argument(
        "--tsv",
        help="Source TSV path (default: reports/.cache/{KEY}-testcases-source.tsv)",
    )
    parser.add_argument(
        "--output",
        help="Output xlsx path (default: testcases/{KEY}-testcases.xlsx)",
    )
    args = parser.parse_args()
    key = args.issue_key.upper()
    root = repo_root()
    tsv = Path(args.tsv) if args.tsv else cache_tsv_path(key, root)
    out = Path(args.output) if args.output else xlsx_path(key, root)

    if not tsv.exists():
        print(
            f"Error: source TSV not found: {tsv}\n"
            f"Write QMetry rows to reports/.cache/{key}-testcases-source.tsv first.",
            file=sys.stderr,
        )
        return 1

    cmd = [
        sys.executable,
        str(root / "scripts" / "generate_qmetry_excel.py"),
        str(tsv),
        str(out),
    ]
    result = subprocess.run(cmd, cwd=root)
    if result.returncode == 0:
        print(str(out.resolve()))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
