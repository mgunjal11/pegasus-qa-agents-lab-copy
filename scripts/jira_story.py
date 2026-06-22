#!/usr/bin/env python3
"""Build coverage-validator Jira cache ({KEY}-jira.json) from REST, MCP JSON, or issue text."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fetch_jira_testplan import (
    adf_to_text,
    collect_comment_texts,
    extract_testplan_references,
)
from jira_env import jira_get, load_dotenv

PR_URL_RE = re.compile(
    r"https://github\.com/[^/\s]+/[^/\s]+/pull/\d+",
    re.IGNORECASE,
)
CONFLUENCE_VIEWPAGE_RE = re.compile(r"pageId=(\d+)", re.IGNORECASE)
CONFLUENCE_PAGE_RE = re.compile(
    r"https://(?:[a-z0-9-]+\.)?atlassian\.net/wiki/spaces/[^/\s]+/pages/(\d+)",
    re.IGNORECASE,
)
EXPLICIT_R_RE = re.compile(
    r"^(?:[-*•]\s*)?(R\d+)\s*[:\-–]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
SECTION_RE = re.compile(
    r"^#{1,4}\s*(.+?)\s*$",
    re.MULTILINE,
)
AC_HEADING_RE = re.compile(
    r"acceptance\s+criteria|acceptance\s+conditions",
    re.IGNORECASE,
)
AC_NUMBERED_RE = re.compile(r"(?<![a-zA-Z0-9])AC(\d+)\s*:", re.IGNORECASE)
BULLET_RE = re.compile(r"^(?:[-*•]|\d+[.)])\s+(.+)$")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def jira_cache_path(issue_key: str, root: Path | None = None) -> Path:
    base = root or repo_root()
    return base / "reports" / ".cache" / f"{issue_key.upper()}-jira.json"


def _field_name(name: str | None) -> str:
    return str(name or "").strip()


def _adf_plain(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return adf_to_text(value).strip()
    if isinstance(value, list):
        return "\n".join(_adf_plain(v) for v in value if v).strip()
    return ""


def _markdown_section(text: str, heading: str) -> str:
    if not text:
        return ""
    target = heading.strip().lower()
    lines = text.splitlines()
    capture: list[str] = []
    in_section = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip().lower()
            if in_section:
                break
            if title == target or target in title:
                in_section = True
            continue
        if in_section:
            if line.startswith("## ") and not line.lower().startswith(f"## {target}"):
                break
            capture.append(raw)
    if capture:
        return "\n".join(capture).strip()

    # ADF-flattened description: "Expected Behavior Content passport should..."
    next_heads = (
        "Actual Behavior",
        "Impact",
        "Environment",
        "Test Data",
        "Related Issues",
        "Steps to Reproduce",
        "Summary",
    )
    stop = "|".join(re.escape(h) for h in next_heads if h.lower() != target.lower())
    pattern = re.compile(
        rf"{re.escape(heading)}\s+(.+?)(?=(?:{stop})\b|$)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _bullets_from_text(text: str) -> list[str]:
    items: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        m = BULLET_RE.match(line)
        if m:
            body = m.group(1).strip()
            if len(body) > 12:
                items.append(body)
    return items


def _dedupe_requirements(reqs: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for req in reqs:
        rid = str(req.get("id") or "").upper()
        text = str(req.get("text") or "").strip()
        if not rid or not text:
            continue
        key = f"{rid}|{text[:80].lower()}"
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": rid, "text": text})
    out.sort(key=lambda r: (int(r["id"][1:]) if r["id"][1:].isdigit() else 999, r["id"]))
    return out


def _extract_explicit_requirements(texts: list[str]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for blob in texts:
        for m in EXPLICIT_R_RE.finditer(blob or ""):
            found.append({"id": m.group(1).upper(), "text": m.group(2).strip()})
    return _dedupe_requirements(found)


def _extract_ac_custom_fields(fields: dict[str, Any]) -> list[dict[str, str]]:
    reqs: list[dict[str, str]] = []
    for key, val in fields.items():
        if not str(key).startswith("customfield"):
            continue
        plain = _adf_plain(val)
        if not plain:
            continue
        if not AC_HEADING_RE.search(plain) and not EXPLICIT_R_RE.search(plain):
            if not re.search(r"\b(given|when|then|acceptance)\b", plain, re.I):
                continue
        explicit = _extract_explicit_requirements([plain])
        if explicit:
            reqs.extend(explicit)
            continue
        bullets = _bullets_from_text(plain)
        if bullets:
            for i, bullet in enumerate(bullets, start=1):
                reqs.append({"id": f"R{i}", "text": bullet})
    return _dedupe_requirements(reqs)


def _extract_ac_numbered(texts: list[str]) -> list[dict[str, str]]:
    """Extract AC1:, AC2:, … blocks from ADF-flattened or inline Jira descriptions."""
    found: list[dict[str, str]] = []
    for blob in texts:
        if not blob or not AC_NUMBERED_RE.search(blob):
            continue
        parts = AC_NUMBERED_RE.split(blob)
        for i in range(1, len(parts), 2):
            num = parts[i]
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if len(body) > 12:
                found.append({"id": f"R{num}", "text": body[:800]})
    return _dedupe_requirements(found)


def _extract_ac_section(description: str) -> list[dict[str, str]]:
    if not description:
        return []
    lines = description.splitlines()
    reqs: list[dict[str, str]] = []
    in_ac = False
    idx = 0
    for raw in lines:
        line = raw.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            in_ac = bool(AC_HEADING_RE.search(title))
            continue
        if not in_ac:
            continue
        m = BULLET_RE.match(line)
        if m:
            idx += 1
            reqs.append({"id": f"R{idx}", "text": m.group(1).strip()})
    return _dedupe_requirements(reqs)


def _platform_from_text(*blobs: str) -> str:
    joined = " ".join(blobs).lower()
    if "pft clear" in joined:
        return "PFT Clear"
    if "tmc" in joined:
        return "TMC"
    if "ce mam" in joined:
        return "CE MAM"
    return "Domino"


def _infer_bug_requirements(
    description: str,
    comments: list[dict[str, Any]],
    summary: str,
) -> list[dict[str, str]]:
    """Structured inference for MSC-style bugs when no explicit R-items exist."""
    reqs: list[dict[str, str]] = []
    expected = _markdown_section(description, "Expected Behavior")
    test_data = _markdown_section(description, "Test Data")
    platform = _platform_from_text(description, summary)

    if expected and re.search(r"passport", expected, re.I):
        reqs.append(
            {
                "id": "R1",
                "text": (
                    f"Content passport retained in cumulative output manifestation for "
                    f"{platform} incremental-as-full (not dropped like pre-fix)"
                ),
            }
        )
    elif expected:
        first = re.split(r"[.\n]", expected)[0].strip()
        if len(first) > 20:
            reqs.append({"id": "R1", "text": first[:240]})

    for comment in comments:
        body = str(comment.get("body") or comment.get("text") or "")
        low = body.lower()
        if "full fulfillment" in low and "passport" in low:
            reqs.append(
                {
                    "id": "R2",
                    "text": (
                        "When metadata-update becomes full fulfillment, pack passport must be "
                        "delivered as expected for incremental-as-full scenario"
                    ),
                }
            )
            break

    desc_low = description.lower()
    if any(term in desc_low for term in ("fmam", "pick-genie", "pick genie", "fulfillmenttype", "fulfillment type")):
        reqs.append(
            {
                "id": "R3",
                "text": (
                    f"Pick-genie must not drop passport re-fetch from FMAM when incremental "
                    f"workflow resolves as fulfillmentType full for {platform}"
                ),
            }
        )

    edit_match = re.search(
        r"Edit ID:\s*([a-f0-9-]{8,})",
        test_data or description,
        re.IGNORECASE,
    )
    mr_match = re.search(
        r"Media Request ID:\s*([a-f0-9-]{8,})",
        test_data or description,
        re.IGNORECASE,
    )
    if edit_match or mr_match or re.search(r"\bsit\b", description, re.I):
        text = "Fix must be validated in SIT using provided test data"
        if edit_match:
            text += f" (Edit ID {edit_match.group(1)}"
            if mr_match:
                text += f", Media Request {mr_match.group(1)}"
            text += ")"
        elif mr_match:
            text += f" (Media Request {mr_match.group(1)})"
        reqs.append({"id": "R4", "text": text})

    return _dedupe_requirements(reqs)


def extract_requirements_from_issue(data: dict[str, Any]) -> list[dict[str, str]]:
    """Layered R1…Rn extraction from normalized jira cache payload."""
    existing = data.get("requirements") or []
    if existing and all(isinstance(r, dict) and r.get("id") for r in existing):
        return _dedupe_requirements(
            [{"id": str(r["id"]), "text": str(r.get("text") or "")} for r in existing]
        )

    fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
    description = str(data.get("description") or fields.get("description") or "")
    if isinstance(fields.get("description"), dict):
        description = _adf_plain(fields["description"]) or description
    summary = str(data.get("summary") or fields.get("summary") or "")

    texts = collect_comment_texts(data)
    if description:
        texts.append(description)
    if summary:
        texts.append(summary)

    reqs = _extract_explicit_requirements(texts)
    if reqs:
        return reqs

    reqs = _extract_ac_custom_fields(fields)
    if reqs:
        return reqs

    reqs = _extract_ac_numbered([description])
    if reqs:
        return reqs

    reqs = _extract_ac_section(description)
    if reqs:
        return reqs

    comments = data.get("comments") or []
    if not comments and isinstance(fields.get("comment"), dict):
        comments = fields["comment"].get("comments") or []

    issuetype = str(data.get("issuetype") or (fields.get("issuetype") or {}).get("name") or "")
    if issuetype.lower() == "bug" or re.search(r"\bbug\b", issuetype, re.I):
        return _infer_bug_requirements(description, comments, summary)

    expected = _markdown_section(description, "Expected Behavior")
    if expected:
        return [{"id": "R1", "text": expected[:240]}]
    return []


def extract_pr_urls(data: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for blob in collect_comment_texts(data):
        for url in PR_URL_RE.findall(blob or ""):
            norm = url.rstrip(".,)")
            if norm not in seen:
                seen.add(norm)
                urls.append(norm)
    for url in data.get("prUrls") or []:
        norm = str(url).strip()
        if norm and norm not in seen:
            seen.add(norm)
            urls.append(norm)
    return urls


def _normalize_comments(raw_comments: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in raw_comments:
        if isinstance(item, str):
            out.append({"id": "", "body": item, "author": {}})
            continue
        if not isinstance(item, dict):
            continue
        body = item.get("body")
        if isinstance(body, dict):
            body = adf_to_text(body)
        out.append(
            {
                "id": str(item.get("id") or ""),
                "body": str(body or item.get("text") or ""),
                "author": item.get("author") if isinstance(item.get("author"), dict) else {},
            }
        )
    return out


def _normalize_attachments(fields: dict[str, Any], top: dict[str, Any]) -> list[dict[str, Any]]:
    raw = top.get("attachments")
    if isinstance(raw, list) and raw:
        return raw
    att = fields.get("attachment")
    if not isinstance(att, list):
        return []
    out: list[dict[str, Any]] = []
    for a in att:
        if not isinstance(a, dict):
            continue
        out.append(
            {
                "id": str(a.get("id") or ""),
                "filename": a.get("filename") or "",
                "mimeType": a.get("mimeType") or "",
                "source": "jira_attachment",
                "content": a.get("content") or "",
            }
        )
    return out


def _confluence_from_url(url: str, title: str = "") -> dict[str, str] | None:
    if not url:
        return None
    page_id = ""
    m = CONFLUENCE_PAGE_RE.search(url) or CONFLUENCE_VIEWPAGE_RE.search(url)
    if m:
        page_id = m.group(1)
    if "atlassian.net/wiki" not in url.lower():
        return None
    return {"pageId": page_id, "title": title, "url": url}


def extract_confluence_links(data: dict[str, Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(link: dict[str, str]) -> None:
        pid = link.get("pageId") or link.get("url") or ""
        if not pid or pid in seen:
            return
        seen.add(pid)
        links.append(link)

    for link in data.get("confluenceLinks") or []:
        if isinstance(link, dict):
            add(dict(link))
    for link in data.get("remoteLinks") or []:
        if not isinstance(link, dict):
            continue
        url = str(link.get("url") or (link.get("object") or {}).get("url") or "")
        title = str(link.get("title") or (link.get("object") or {}).get("title") or "")
        ref = _confluence_from_url(url, title)
        if ref:
            add(ref)

    for blob in collect_comment_texts(data):
        for url in re.findall(r"https://[^\s\"']*atlassian\.net/wiki[^\s\"']*", blob or ""):
            ref = _confluence_from_url(unquote(url))
            if ref:
                add(ref)

    return links


def normalize_rest_issue(issue: dict[str, Any], issue_key: str) -> dict[str, Any]:
    """Normalize Jira REST GET /issue response to validator cache shape."""
    key = str(issue.get("key") or issue_key).upper()
    fields = issue.get("fields") or {}
    description = fields.get("description")
    if isinstance(description, dict):
        description = _adf_plain(description)
    summary = str(fields.get("summary") or "")
    status = (fields.get("status") or {}).get("name") or ""
    issuetype = (fields.get("issuetype") or {}).get("name") or ""
    comments_raw = (fields.get("comment") or {}).get("comments") or []
    comments = _normalize_comments(comments_raw)
    attachments = _normalize_attachments(fields, issue)
    field_attachments = payload_attachments(fields) or attachments

    payload: dict[str, Any] = {
        "issueKey": key,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "status": status,
        "issuetype": issuetype,
        "description": str(description or ""),
        "attachments": attachments,
        "comments": comments,
        "fields": {
            "summary": summary,
            "description": str(description or ""),
            "status": fields.get("status"),
            "issuetype": fields.get("issuetype"),
            "attachment": field_attachments,
            "comment": {"comments": comments},
        },
    }
    for fk, fv in fields.items():
        if str(fk).startswith("customfield"):
            payload["fields"][fk] = fv

    payload["prUrls"] = extract_pr_urls(payload)
    payload["remoteLinks"] = []
    payload["confluenceLinks"] = extract_confluence_links(payload)
    payload["requirements"] = extract_requirements_from_issue(payload)
    refs = extract_testplan_references(payload, key)
    if refs:
        payload["testPlanReferences"] = refs
        payload["testPlanReference"] = refs[0]
    return payload


def payload_attachments(fields: dict[str, Any]) -> list[dict[str, Any]]:
    att = fields.get("attachment")
    if not isinstance(att, list):
        return []
    out = []
    for a in att:
        if isinstance(a, dict):
            out.append(
                {
                    "id": str(a.get("id") or ""),
                    "filename": a.get("filename") or "",
                    "mimeType": a.get("mimeType") or "",
                    "source": "jira_attachment",
                    "content": a.get("content") or "",
                }
            )
    return out


def normalize_mcp_issue(mcp_issue: dict[str, Any], issue_key: str) -> dict[str, Any]:
    """Normalize Atlassian MCP getJiraIssue response to validator cache shape."""
    key = str(mcp_issue.get("key") or issue_key).upper()
    fields = mcp_issue.get("fields") or {}
    description = mcp_issue.get("description")
    if not description:
        description = fields.get("description")
    if isinstance(description, dict):
        description = _adf_plain(description)

    comments = _normalize_comments(mcp_issue.get("comments") or [])
    if not comments and isinstance(fields.get("comment"), dict):
        comments = _normalize_comments(fields["comment"].get("comments") or [])

    payload: dict[str, Any] = {
        "issueKey": key,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "summary": str(mcp_issue.get("summary") or fields.get("summary") or ""),
        "status": str((fields.get("status") or {}).get("name") or mcp_issue.get("status") or ""),
        "issuetype": str((fields.get("issuetype") or {}).get("name") or ""),
        "description": str(description or ""),
        "attachments": _normalize_attachments(fields, mcp_issue),
        "comments": comments,
        "fields": dict(fields),
    }
    payload["fields"]["attachment"] = payload_attachments(fields) or payload["attachments"]
    payload["fields"]["comment"] = {"comments": comments}
    if isinstance(description, str):
        payload["fields"]["description"] = description

    payload["prUrls"] = extract_pr_urls(payload)
    payload["remoteLinks"] = list(mcp_issue.get("remoteLinks") or [])
    payload["confluenceLinks"] = extract_confluence_links(payload)
    payload["requirements"] = extract_requirements_from_issue(payload)
    refs = extract_testplan_references(payload, key)
    if refs:
        payload["testPlanReferences"] = refs
        payload["testPlanReference"] = refs[0]
    return payload


def fetch_remote_links(issue_key: str, site: str = "wbdstreaming.atlassian.net") -> list[dict[str, Any]]:
    url = f"https://{site}/rest/api/3/issue/{issue_key.upper()}/remotelink"
    try:
        data = json.loads(jira_get(url).decode())
    except RuntimeError:
        return []
    links: list[dict[str, Any]] = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        obj = item.get("object") or {}
        url_val = obj.get("url") or item.get("url") or ""
        title = obj.get("title") or item.get("title") or ""
        page_id = ""
        m = CONFLUENCE_VIEWPAGE_RE.search(str(url_val))
        if m:
            page_id = m.group(1)
        links.append({"title": title, "url": url_val, "pageId": page_id})
    return links


def fetch_issue_rest(
    issue_key: str,
    *,
    site: str = "wbdstreaming.atlassian.net",
    extra_fields: list[str] | None = None,
) -> dict[str, Any]:
    fields = [
        "summary",
        "description",
        "status",
        "issuetype",
        "priority",
        "comment",
        "attachment",
        "labels",
        "components",
    ]
    if extra_fields:
        fields.extend(extra_fields)
    field_param = ",".join(dict.fromkeys(fields))
    url = f"https://{site}/rest/api/3/issue/{issue_key.upper()}?fields={field_param}"
    issue = json.loads(jira_get(url).decode())
    payload = normalize_rest_issue(issue, issue_key)
    payload["remoteLinks"] = fetch_remote_links(issue_key, site=site)
    payload["confluenceLinks"] = extract_confluence_links(payload)
    return payload


def merge_requirements(
    new_reqs: list[dict[str, str]],
    prior_reqs: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """Keep prior agent-refined requirements when new extraction is thinner."""
    if not prior_reqs:
        return new_reqs
    prior = _dedupe_requirements(
        [{"id": str(r["id"]), "text": str(r.get("text") or "")} for r in prior_reqs if r.get("id")]
    )
    if len(new_reqs) >= len(prior):
        return new_reqs
    return prior


def build_jira_cache(
    issue_key: str,
    *,
    root: Path | None = None,
    site: str = "wbdstreaming.atlassian.net",
    mcp_json: Path | None = None,
    merge_prior: bool = True,
) -> dict[str, Any]:
    base = root or repo_root()
    key = issue_key.upper()
    prior: dict[str, Any] = {}
    out_path = jira_cache_path(key, base)
    if merge_prior and out_path.exists():
        try:
            prior = json.loads(out_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prior = {}

    if mcp_json and mcp_json.exists():
        raw = json.loads(mcp_json.read_text(encoding="utf-8"))
        payload = normalize_mcp_issue(raw, key)
    else:
        load_dotenv(base / ".env")
        payload = fetch_issue_rest(key, site=site)

    if merge_prior and prior.get("requirements"):
        payload["requirements"] = merge_requirements(
            payload.get("requirements") or [],
            prior.get("requirements") or [],
        )

    if merge_prior:
        if not payload.get("prUrls") and prior.get("prUrls"):
            payload["prUrls"] = list(prior["prUrls"])
        if not payload.get("testPlanReferences") and prior.get("testPlanReferences"):
            payload["testPlanReferences"] = prior["testPlanReferences"]
            payload["testPlanReference"] = prior.get("testPlanReference") or prior["testPlanReferences"][0]
        if not payload.get("remoteLinks") and prior.get("remoteLinks"):
            payload["remoteLinks"] = prior["remoteLinks"]
        if not payload.get("confluenceLinks") and prior.get("confluenceLinks"):
            payload["confluenceLinks"] = prior["confluenceLinks"]

    if prior.get("remoteLinks") and not payload.get("remoteLinks"):
        payload["remoteLinks"] = prior["remoteLinks"]
    if prior.get("confluenceLinks") and not payload.get("confluenceLinks"):
        payload["confluenceLinks"] = prior["confluenceLinks"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
