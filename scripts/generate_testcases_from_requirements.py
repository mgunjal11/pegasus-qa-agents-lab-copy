#!/usr/bin/env python3
"""
Deterministic QMetry test case generation from Jira + LADR requirement caches.

Used by run_coverage_validator.py for Step 5a (no_testplan) and partial gap fill.
LLM @Spec2Test remains optional for richer scenarios; this script is one-shot safe.

  python scripts/generate_testcases_from_requirements.py MSC-213475 --write-excel
  python scripts/generate_testcases_from_requirements.py MSC-205625 --gap-only R4,L5 --write-excel
  python scripts/generate_testcases_from_requirements.py MSC-205625 --gap-only from-testplan --write-excel
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from confluence_requirements import dedupe_ladr_requirements
from prepare_testcase_writer_context import extract_jira_requirements, load_json, repo_root

QMETRY_COLUMNS = [
    "Summary",
    "Automatable",
    "Automation Status",
    "Priority",
    "Folders",
    "Step Summary",
    "Test Type",
    "Status",
    "Regression Test (Y/N)",
    "Story",
    "TestData Dependent",
]

MAP_RE = re.compile(r"\(maps\s+([RL\d,\s]+)\)", re.IGNORECASE)
DECISION_TABLE_RE = re.compile(r"decision\s+table", re.IGNORECASE)

DT_ROWS = [
    ("DT1", "needByDate disabled, byMarkets disabled, byContentType disabled", "50"),
    ("DT2", "needByDate enabled, needByDate within ±48h", "100"),
    ("DT3", "needByDate enabled, outside ±48h; byMarkets disabled", "50"),
    ("DT4", "needByDate outside window; byMarkets enabled; market not in activeMarkets", "25"),
    ("DT5", "needByDate outside window; market in activeMarkets; byContentType disabled", "50"),
    ("DT6", "rules 1-2 no match; byContentType enabled; content type AD", "75"),
    ("DT7", "rules 1-2 no match; byContentType enabled; content type PROMO", "50"),
    ("DT8", "rules 1-2 no match; byContentType enabled; content type PROGRAM", "50"),
]


def cache_dir(root: Path) -> Path:
    return root / "reports" / ".cache"


def _slug(text: str, max_len: int = 55) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    clean = re.sub(r"[^\w\s-]", "", clean)
    words = clean.split()[:8]
    slug = "_".join(words) if words else "scenario"
    return slug[:max_len].rstrip("_")


def _truncate(text: str, max_len: int = 220) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _mapped_ids_from_summary(summary: str) -> set[str]:
    match = MAP_RE.search(summary or "")
    if not match:
        return set()
    return {p.strip().upper() for p in re.split(r"[,\s]+", match.group(1)) if p.strip()}


def read_tsv_cases(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        return QMETRY_COLUMNS[:], []
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if not rows:
        return QMETRY_COLUMNS[:], []
    header = [c.strip() for c in rows[0]]
    if header != QMETRY_COLUMNS:
        header = QMETRY_COLUMNS
        body = rows[1:]
    else:
        body = rows[1:]
    return header, body


def write_tsv(path: Path, header: list[str], body: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(body)


def existing_mapped_ids(tsv_path: Path) -> set[str]:
    _, body = read_tsv_cases(tsv_path)
    ids: set[str] = set()
    for i in range(0, len(body), 3):
        if i >= len(body):
            break
        row = body[i]
        if row:
            ids.update(_mapped_ids_from_summary(row[0] if row else ""))
    return ids


def _case_rows(
    issue_key: str,
    *,
    summary: str,
    given: str,
    when: str,
    then: str,
    priority: str = "P0",
    test_data: str = "Yes",
) -> list[list[str]]:
    meta = [
        summary,
        "Yes",
        "Not Started",
        priority,
        "",
        given,
        "End to End",
        "",
        "Yes",
        issue_key,
        test_data,
    ]
    when_row = [""] * len(QMETRY_COLUMNS)
    when_row[QMETRY_COLUMNS.index("Step Summary")] = when
    then_row = [""] * len(QMETRY_COLUMNS)
    then_row[QMETRY_COLUMNS.index("Step Summary")] = then
    return [meta, when_row, then_row]


def _jira_cases(issue_key: str, req: dict[str, str]) -> list[list[list[str]]]:
    rid = str(req.get("id") or "").upper()
    text = str(req.get("text") or "")
    blocks: list[list[list[str]]] = []

    if rid == "R6" and DECISION_TABLE_RE.search(text):
        for dt_id, config, expected in DT_ROWS:
            summary = (
                f"{issue_key}_Decision table {dt_id} expected priority {expected} (maps R6)"
            )
            given = f"Given: LADR decision table row {dt_id} — {config}"
            when = "When: MR is ingested and partner priority rules are evaluated"
            then = f"Then: payload.mediaRequest.priority is {expected} per decision table"
            blocks.append(_case_rows(issue_key, summary=summary, given=given, when=when, then=then))
        return blocks

    slug = _slug(text)
    summary = f"{issue_key}_{slug} (maps {rid})"
    given = f"Given: {_truncate(text, 240)}"
    when = f"When: Acceptance criterion {rid} is exercised per Jira story {issue_key}"
    then = f"Then: Observable outcome matches {rid} in Jira acceptance criteria"
    pri = "P1" if re.search(r"\b(sit|manual|invalid|failure|error)\b", text, re.I) else "P0"
    blocks.append(_case_rows(issue_key, summary=summary, given=given, when=when, then=then, priority=pri))
    return blocks


def _ladr_cases(issue_key: str, req: dict[str, Any]) -> list[list[list[str]]]:
    rid = str(req.get("id") or "").upper()
    task = str(req.get("task") or "milestone")
    status = str(req.get("status") or "Completed")
    text = str(req.get("text") or "")
    summary = f"{issue_key}_E2E {task} {status} (maps {rid})"
    given = f"Given: FF2.0 workflow preconditions for LADR ESS {rid}; {_truncate(text, 120)}"
    when = f"When: Workflow reaches {task} milestone"
    then = f"Then: {task} status is {status}; priority field retained per story requirements"
    return [_case_rows(issue_key, summary=summary, given=given, when=when, then=then)]


def load_requirement_context(issue_key: str, root: Path | None = None) -> dict[str, Any]:
    base = root or repo_root()
    cache = cache_dir(base)
    key = issue_key.upper()
    jira = load_json(cache / f"{key}-jira.json")
    conf = load_json(cache / f"{key}-confluence.json")
    return {
        "issueKey": key,
        "jiraRequirements": extract_jira_requirements(jira),
        "ladrRequirements": dedupe_ladr_requirements(conf.get("ladrRequirements") or []),
    }


def uncovered_from_testplan(issue_key: str, root: Path | None = None) -> list[str]:
    base = root or repo_root()
    tp = load_json(cache_dir(base) / f"{issue_key.upper()}-testplan.json")
    cov = tp.get("coverage") if isinstance(tp.get("coverage"), dict) else {}
    ids: list[str] = []
    for key in ("uncoveredRequirements", "uncoveredJiraRequirements", "uncoveredLadrRequirements"):
        for item in cov.get(key) or []:
            rid = str(item).strip().upper()
            if rid and rid not in ids:
                ids.append(rid)
    return ids


def parse_gap_ids(raw: str | None, issue_key: str, root: Path | None = None) -> list[str]:
    if not raw:
        return []
    if raw.strip().lower() in {"from-testplan", "from-testplan-cache", "auto"}:
        return uncovered_from_testplan(issue_key, root)
    out: list[str] = []
    for part in re.split(r"[,\\s]+", raw):
        rid = part.strip().upper()
        if rid and rid not in out:
            out.append(rid)
    return out


def select_requirements(
    ctx: dict[str, Any],
    target_ids: list[str] | None,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    jira_all = ctx.get("jiraRequirements") or []
    ladr_all = ctx.get("ladrRequirements") or []
    if not target_ids:
        return list(jira_all), list(ladr_all)
    target = set(target_ids)
    jira = [r for r in jira_all if str(r.get("id", "")).upper() in target]
    ladr = [r for r in ladr_all if str(r.get("id", "")).upper() in target]
    return jira, ladr


def generate_blocks(
    issue_key: str,
    jira_reqs: list[dict[str, str]],
    ladr_reqs: list[dict[str, Any]],
    *,
    skip_ids: set[str] | None = None,
) -> list[list[str]]:
    skip = skip_ids or set()
    out: list[list[str]] = []
    for req in jira_reqs:
        rid = str(req.get("id") or "").upper()
        if rid in skip:
            continue
        for block in _jira_cases(issue_key, req):
            out.extend(block)
    for req in ladr_reqs:
        rid = str(req.get("id") or "").upper()
        if rid in skip:
            continue
        for block in _ladr_cases(issue_key, req):
            out.extend(block)
    return out


def output_paths(
    issue_key: str,
    *,
    gap_only: bool,
    root: Path | None = None,
) -> tuple[Path, Path]:
    base = root or repo_root()
    key = issue_key.upper()
    if gap_only:
        tsv = cache_dir(base) / f"{key}-gap-testcases-source.tsv"
        xlsx = base / "testcases" / f"{key}-gap-supplement.xlsx"
    else:
        tsv = cache_dir(base) / f"{key}-testcases-source.tsv"
        xlsx = base / "testcases" / f"{key}-testcases.xlsx"
    return tsv, xlsx


def write_excel(issue_key: str, tsv: Path, xlsx: Path, root: Path) -> int:
    cmd = [
        sys.executable,
        str(root / "scripts" / "write_testcase_excel.py"),
        issue_key.upper(),
        "--tsv",
        str(tsv),
        "--output",
        str(xlsx),
    ]
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate QMetry cases from requirement caches")
    parser.add_argument("issue_key")
    parser.add_argument(
        "--gap-only",
        help="Comma-separated R/L ids, or from-testplan to use uncovered ids from testplan cache",
    )
    parser.add_argument("--write-excel", action="store_true", help="Build xlsx after TSV")
    parser.add_argument(
        "--merge",
        action="store_true",
        default=True,
        help="Merge with existing TSV and skip already-mapped ids (default: on)",
    )
    parser.add_argument("--no-merge", action="store_false", dest="merge")
    args = parser.parse_args()
    key = args.issue_key.upper()
    root = repo_root()
    gap_only = bool(args.gap_only)
    target_ids = parse_gap_ids(args.gap_only, key, root) if gap_only else None

    ctx = load_requirement_context(key, root)
    jira_reqs, ladr_reqs = select_requirements(ctx, target_ids)
    if gap_only and not jira_reqs and not ladr_reqs:
        print(json.dumps({"issueKey": key, "generated": 0, "reason": "no matching gap requirements"}))
        return 0

    tsv_path, xlsx_path = output_paths(key, gap_only=gap_only, root=root)
    header, existing = read_tsv_cases(tsv_path) if args.merge and tsv_path.exists() else (QMETRY_COLUMNS[:], [])
    skip_ids = existing_mapped_ids(tsv_path) if args.merge else set()

    new_rows = generate_blocks(key, jira_reqs, ladr_reqs, skip_ids=skip_ids)
    if not new_rows and gap_only:
        print(json.dumps({"issueKey": key, "generated": 0, "reason": "gaps already covered in TSV"}))
        return 0

    merged = existing + new_rows
    write_tsv(tsv_path, header, merged)
    case_count = len(merged) // 3

    payload: dict[str, Any] = {
        "issueKey": key,
        "mode": "gap_only" if gap_only else "full",
        "generatedCases": len(new_rows) // 3,
        "totalCases": case_count,
        "tsv": str(tsv_path.resolve()),
        "targetIds": target_ids or "all",
    }

    if args.write_excel:
        rc = write_excel(key, tsv_path, xlsx_path, root)
        if rc != 0:
            return rc
        payload["xlsx"] = str(xlsx_path.resolve())

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
