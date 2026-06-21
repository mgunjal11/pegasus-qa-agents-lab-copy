#!/usr/bin/env python3
"""Extract LADR / Confluence requirements and map test cases to Jira + LADR scope."""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from jira_env import jira_get, load_dotenv

CONFLUENCE_PAGE_URL_RE = re.compile(
    r"https://(?:[a-z0-9-]+\.)?atlassian\.net/wiki/spaces/[^/\s]+/pages/(\d+)",
    re.IGNORECASE,
)
CONFLUENCE_SHORT_URL_RE = re.compile(
    r"https://(?:[a-z0-9-]+\.)?atlassian\.net/wiki/x/([A-Za-z0-9]+)",
    re.IGNORECASE,
)
CONFLUENCE_VIEWPAGE_RE = re.compile(
    r"pageId=(\d+)",
    re.IGNORECASE,
)
LADR_URL_HINT_RE = re.compile(r"\bLADR\b", re.IGNORECASE)
# Confluence pages that mention ESS/LADR tables but are not LADR design docs (quick links).
NON_LADR_PAGE_TITLE_RE = re.compile(
    r"\b(deployment|grooming|go\s*live|learnings|refactor|pvc\s+go)\b",
    re.IGNORECASE,
)

ESS_TASKS = (
    "demandAcknowledgment",
    "manifestationAvailability",
    "orderStatus",
    "registrationStatus",
)

ESS_STATUSES = ("Completed", "Failure", "Pending", "Processing", "Skipped")

TASK_ALIASES: dict[str, tuple[str, ...]] = {
    "demandacknowledgment": (
        "demand acknowledged",
        "demandacknowledgment",
        "demand acknowledgment",
    ),
    "manifestationavailability": (
        "manifestation availability",
        "manifestationavailability",
        "proxy/manifestation",
        "manifestation / proxy",
    ),
    "orderstatus": ("orderstatus", "caption order", "order status"),
    "registrationstatus": (
        "registrationstatus",
        "caption registration",
        "registration status",
    ),
}

STATUS_ALIASES: dict[str, tuple[str, ...]] = {
    "completed": ("completed", "complete"),
    "failure": ("failure", "failed", "fail"),
    "pending": ("pending",),
    "processing": ("processing", "in progress"),
    "skipped": ("skipped", "skip"),
}

JIRA_AC_INFERENCE: dict[str, tuple[str, ...]] = {
    "R1": ("v2", "ess", "demandacknowledgment", "manifestationavailability", "orderstatus", "registrationstatus"),
    "R2": (
        "caption status",
        "status is",
        "milestone",
        "demandacknowledgment",
        "manifestationavailability",
        "orderstatus",
        "registrationstatus",
    ),
    "R3": ("8000", "9000", "status_failure", "status_error", "failure", "status failure"),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def confluence_cache_path(issue_key: str) -> Path:
    return repo_root() / "reports" / ".cache" / f"{issue_key.upper()}-confluence.json"


def extract_confluence_urls(texts: list[str]) -> list[dict[str, str]]:
    """Find Confluence page URLs (prefer LADR-titled links when present)."""
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: str, context: str = "", title: str = "") -> None:
        url = url.rstrip(").,]")
        page_match = CONFLUENCE_PAGE_URL_RE.search(url)
        if page_match:
            page_id = page_match.group(1)
            key = f"page:{page_id}"
            if key not in seen:
                seen.add(key)
                found.append({"url": url, "pageId": page_id, "context": context, "title": title})
            return
        view_match = CONFLUENCE_VIEWPAGE_RE.search(url)
        if view_match and "atlassian.net/wiki" in url.lower():
            page_id = view_match.group(1)
            key = f"page:{page_id}"
            if key not in seen:
                seen.add(key)
                found.append({"url": url, "pageId": page_id, "context": context, "title": title})
            return
        short_match = CONFLUENCE_SHORT_URL_RE.search(url)
        if short_match:
            tiny = short_match.group(1)
            key = f"tiny:{tiny}"
            if key not in seen:
                seen.add(key)
                found.append({"url": url, "pageId": tiny, "context": context, "title": title})

    for text in texts:
        if not text:
            continue
        for url in re.findall(r"https://[^\s\"'<>]+", text):
            if "atlassian.net/wiki" in url.lower():
                add(url, text[:200])
        if LADR_URL_HINT_RE.search(text):
            for url in re.findall(r"https://[^\s\"'<>]+", text):
                if "atlassian.net/wiki" in url.lower():
                    add(url, text[:200])

    found.sort(key=lambda r: (0 if "ladr" in (r.get("context") or "").lower() else 1, r["url"]))
    return found


def extract_confluence_from_jira_links(jira_data: dict[str, Any]) -> list[dict[str, str]]:
    """Collect Confluence page refs from Jira remote links and confluenceLinks (not only description text)."""
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_ref(url: str, page_id: str | None = None, title: str = "") -> None:
        if not url and not page_id:
            return
        pid = page_id or ""
        if not pid and url:
            m = CONFLUENCE_PAGE_URL_RE.search(url) or CONFLUENCE_VIEWPAGE_RE.search(url)
            if m:
                pid = m.group(1)
        if not pid:
            return
        key = f"page:{pid}"
        if key in seen:
            return
        seen.add(key)
        full_url = url or f"https://wbdstreaming.atlassian.net/wiki/pages/viewpage.action?pageId={pid}"
        ctx = title or "remote link"
        found.append({"url": full_url, "pageId": pid, "context": ctx, "title": title})

    for link in jira_data.get("remoteLinks") or []:
        if not isinstance(link, dict):
            continue
        url = link.get("url") or (link.get("object") or {}).get("url") or ""
        title = link.get("title") or (link.get("object") or {}).get("title") or ""
        page_id = link.get("pageId")
        if url or page_id:
            add_ref(str(url), str(page_id) if page_id else None, str(title))

    for link in jira_data.get("confluenceLinks") or []:
        if not isinstance(link, dict):
            continue
        add_ref(
            str(link.get("url") or ""),
            str(link.get("pageId")) if link.get("pageId") else None,
            str(link.get("title") or ""),
        )

    return found


def merge_confluence_url_lists(*lists: list[dict[str, str]]) -> list[dict[str, str]]:
    """Deduplicate Confluence URL refs by pageId."""
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for items in lists:
        for ref in items:
            pid = ref.get("pageId") or ""
            key = f"page:{pid}"
            if not pid or key in seen:
                continue
            seen.add(key)
            merged.append(ref)
    return merged


def collect_jira_texts(jira_data: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in ("description", "summary"):
        val = jira_data.get(key)
        if isinstance(val, str):
            texts.append(val)
    for comment in jira_data.get("comments") or []:
        if isinstance(comment, str):
            texts.append(comment)
        elif isinstance(comment, dict):
            for field in ("body", "text", "markdown"):
                if isinstance(comment.get(field), str):
                    texts.append(comment[field])
    fields = jira_data.get("fields") or {}
    for field in ("description", "summary"):
        val = fields.get(field)
        if isinstance(val, str):
            texts.append(val)
    comment_block = fields.get("comment") or {}
    if isinstance(comment_block, dict):
        for item in comment_block.get("comments") or []:
            if isinstance(item, dict) and isinstance(item.get("body"), str):
                texts.append(item["body"])
    return texts


def _strip_html(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"</?(?:p|div|tr|li|h[1-6])[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return unescape(re.sub(r"\s+", " ", text)).strip()


def fetch_confluence_page_body(page_id: str, site: str = "wbdstreaming.atlassian.net") -> dict[str, Any]:
    """Fetch Confluence page via REST (same Basic auth as Jira)."""
    load_dotenv()
    url = (
        f"https://{site}/wiki/rest/api/content/{page_id}"
        f"?expand=body.storage,body.view,space,version"
    )
    raw = json.loads(jira_get(url).decode())
    storage = ((raw.get("body") or {}).get("storage") or {}).get("value") or ""
    view = ((raw.get("body") or {}).get("view") or {}).get("value") or ""
    body = _strip_html(storage or view)
    links = raw.get("_links") or {}
    web_ui = links.get("webui") or links.get("base") or ""
    web_url = f"https://{site}/wiki{web_ui}" if web_ui.startswith("/") else web_ui
    return {
        "id": str(raw.get("id") or page_id),
        "title": raw.get("title") or "",
        "webUrl": web_url,
        "bodyText": body,
        "bodyHtml": storage or view,
    }


def parse_passport_confluence_requirements(
    body_text: str, source: str = "ladr"
) -> list[dict[str, str]]:
    """Parse passport workflow scenarios from Confluence design pages (non-ESS LADR)."""
    lower = body_text.lower()
    if "passport" not in lower:
        return []
    if re.search(r"\bdemandacknowledgment\b", lower):
        return []

    scenario_markers = (
        ("mvp full", "MVP Full — passport always gets attached"),
        (
            "incremental to full on pick",
            "Incremental to Full on PICK — passport must attach when pick evaluates full",
        ),
        ("mdu to full in pack", "MDU to Full in Pack — passport must attach in pack"),
        ("incremental", "Incremental — passport attached when stamp change audit present"),
        ("mdu in pick", "MDU in Pick — passport not attached (expected)"),
    )
    reqs: list[dict[str, str]] = []
    for marker, text in scenario_markers:
        if marker in lower:
            reqs.append(
                {
                    "id": f"L{len(reqs) + 1}",
                    "text": text,
                    "source": source,
                    "kind": "passport_scenario",
                }
            )
    return reqs


def parse_ladr_ess_requirements(body_text: str, source: str = "ladr") -> list[dict[str, str]]:
    """
    Parse ESS milestone rows from LADR Confluence body.
    Yields L1…Ln requirements aligned to Caption Monitoring test scenarios.
    """
    lower = body_text.lower()
    has_ess_context = bool(re.search(r"\bess\b", lower)) or any(
        re.search(rf"\b{re.escape(t.lower())}\b", lower) for t in ESS_TASKS
    )
    if not has_ess_context:
        return []

    milestone_statuses: dict[str, tuple[str, ...]] = {
        "demandAcknowledgment": ("Completed", "Failure"),
        "manifestationAvailability": ("Pending", "Completed"),
        "orderStatus": ("Pending", "Processing", "Completed", "Failure", "Skipped"),
        "registrationStatus": ("Pending", "Completed", "Failure"),
    }

    reqs: list[dict[str, str]] = []
    for task, statuses in milestone_statuses.items():
        for status in statuses:
            reqs.append(
                {
                    "id": f"L{len(reqs) + 1}",
                    "text": f"{task} — {status} status (LADR ESS)",
                    "task": task,
                    "status": status,
                    "source": source,
                }
            )

    if re.search(r"\b8000\b", body_text) or "status_failure" in lower:
        reqs.append(
            {
                "id": f"L{len(reqs) + 1}",
                "text": "STATUS_FAILURE code 8000",
                "source": source,
                "kind": "status_code",
            }
        )
    if re.search(r"\b9000\b", body_text) or "status_error" in lower:
        reqs.append(
            {
                "id": f"L{len(reqs) + 1}",
                "text": "STATUS_ERROR code 9000",
                "source": source,
                "kind": "status_code",
            }
        )
    return reqs


GENERIC_SECTION_HEADING_RE = re.compile(
    r"^#{1,4}\s*(?:\d+\.?\s*)?"
    r"(requirements|acceptance criteria|scenarios|design scenarios|use cases|"
    r"ladr|ess|test scenarios|verification scenarios)\b",
    re.I,
)


def parse_generic_confluence_requirements(
    body_text: str, source: str = "ladr"
) -> list[dict[str, str]]:
    """
    Parse bullet/numbered items under requirement-like Confluence headings.
    Fallback when ESS/passport parsers find nothing.
    """
    if not body_text or len(body_text.strip()) < 40:
        return []

    reqs: list[dict[str, str]] = []
    in_section = False
    for raw in body_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^#{1,4}\s", line):
            in_section = bool(GENERIC_SECTION_HEADING_RE.match(line))
            continue
        if not in_section:
            continue
        bullet = re.sub(r"^[-*•]\s*", "", line)
        bullet = re.sub(r"^\d+[.)]\s*", "", bullet)
        if len(bullet) < 18:
            continue
        if bullet.lower().startswith(("see ", "refer ", "note:", "todo:")):
            continue
        reqs.append(
            {
                "id": f"L{len(reqs) + 1}",
                "text": bullet.strip(),
                "source": source,
                "kind": "confluence_bullet",
            }
        )
    return reqs


def load_confluence_cache(issue_key: str) -> dict[str, Any]:
    path = confluence_cache_path(issue_key)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _page_dict_to_link(page: dict[str, Any]) -> dict[str, str] | None:
    """Normalize a Confluence page record to {url, title} for quick links."""
    url = (page.get("webUrl") or page.get("url") or "").strip()
    page_id = str(page.get("id") or page.get("pageId") or "").strip()
    if not url and page_id:
        url = f"https://wbdstreaming.atlassian.net/wiki/pages/viewpage.action?pageId={page_id}"
    if not url:
        return None
    title = (page.get("title") or page.get("context") or "Confluence").strip() or "Confluence"
    return {"url": url, "title": title}


def page_id_from_confluence_url(url: str) -> str:
    """Extract numeric Confluence pageId from a wiki URL."""
    if not url:
        return ""
    match = CONFLUENCE_PAGE_URL_RE.search(url) or CONFLUENCE_VIEWPAGE_RE.search(url)
    return match.group(1) if match else ""


def ladr_page_ids_from_confluence_cache(conf: dict[str, Any]) -> set[str]:
    """Page IDs that produced L1…Ln requirements (ESS or passport/design scenarios)."""
    ids: set[str] = set()
    for page in conf.get("pages") or []:
        if not isinstance(page, dict):
            continue
        pid = str(page.get("id") or page.get("pageId") or "").strip()
        if pid and page.get("ladrRequirements"):
            ids.add(pid)
    return ids


def is_ladr_confluence_link(
    url: str,
    title: str = "",
    *,
    ladr_page_ids: set[str] | None = None,
) -> bool:
    """
    True when a Confluence URL is an LADR / design-requirements source (not grooming notes).

    Includes title/URL with LADR, or cached pages with ladrRequirements that are design docs
    (excludes deployment/grooming pages that only embed ESS tables).
    """
    label = f"{url} {title}"
    if NON_LADR_PAGE_TITLE_RE.search(title or ""):
        return False
    if LADR_URL_HINT_RE.search(label):
        return True
    pid = page_id_from_confluence_url(url)
    if pid and ladr_page_ids and pid in ladr_page_ids:
        return True
    return False


def collect_ladr_page_links(issue_key: str, root: Path | None = None) -> list[dict[str, str]]:
    """
    Confluence wiki URLs for quick navigation — LADR / design pages only.

    Filters out Jira remote links such as grooming notes, deployment pages, and ADRs
    that are not LADR requirement sources.
    """
    key = issue_key.upper()
    conf = load_confluence_cache(key)
    ladr_page_ids = ladr_page_ids_from_confluence_cache(conf)
    return [
        link
        for link in collect_confluence_page_links(key, root)
        if is_ladr_confluence_link(
            link.get("url") or "",
            link.get("title") or "",
            ladr_page_ids=ladr_page_ids,
        )
    ]


def collect_confluence_page_links(issue_key: str, root: Path | None = None) -> list[dict[str, str]]:
    """
    Collect all Confluence wiki URLs referenced by caches (internal / traceability use).

    For report quick navigation, use collect_ladr_page_links() instead.

    Sources (deduped): confluence cache, test plan cache, Jira cache remote links / text,
    and any reports/.cache/{KEY}*.json file (e.g. analysis.json with embedded wiki hrefs).
    """
    base = root or repo_root()
    key = issue_key.upper()
    cache_dir = base / "reports" / ".cache"
    seen_urls: set[str] = set()
    links: list[dict[str, str]] = []

    def add(url: str, title: str = "Confluence") -> None:
        url = url.rstrip(").,]\"\\").strip()
        if not url or url in seen_urls:
            return
        seen_urls.add(url)
        links.append({"url": url, "title": (title or "Confluence").strip() or "Confluence"})

    conf = load_confluence_cache(key) if (cache_dir / f"{key}-confluence.json").exists() else {}
    for ref in conf.get("confluenceUrls") or []:
        if isinstance(ref, dict) and ref.get("url"):
            add(str(ref["url"]), str(ref.get("title") or ref.get("context") or "Confluence"))
    for page in conf.get("pages") or []:
        if isinstance(page, dict):
            link = _page_dict_to_link(page)
            if link:
                add(link["url"], link["title"])

    tp_path = cache_dir / f"{key}-testplan.json"
    if tp_path.exists():
        try:
            tp = json.loads(tp_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            tp = {}
        for page in (tp.get("confluence") or {}).get("pages") or []:
            if isinstance(page, dict):
                link = _page_dict_to_link(page)
                if link:
                    add(link["url"], link["title"])

    jira_path = cache_dir / f"{key}-jira.json"
    jira_data: dict[str, Any] = {}
    if jira_path.exists():
        try:
            jira_data = json.loads(jira_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            jira_data = {}
    for ref in merge_confluence_url_lists(
        extract_confluence_urls(collect_jira_texts(jira_data)),
        extract_confluence_from_jira_links(jira_data),
    ):
        add(ref["url"], str(ref.get("title") or ref.get("context") or "Confluence"))

    blob_texts: list[str] = []
    if cache_dir.is_dir():
        for path in sorted(cache_dir.glob(f"{key}*.json")):
            try:
                blob_texts.append(path.read_text(encoding="utf-8"))
            except OSError:
                continue
    for ref in extract_confluence_urls(blob_texts):
        add(ref["url"], str(ref.get("title") or ref.get("context") or "Confluence"))

    return links


def dedupe_ladr_requirements(ladr_reqs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse duplicate LADR rows (same id or task+status) from multiple Confluence pages."""
    seen_ids: set[str] = set()
    seen_task_status: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for req in ladr_reqs:
        rid = str(req.get("id") or "")
        task = str(req.get("task") or "").strip().lower()
        status = str(req.get("status") or "").strip().lower()
        task_status = (task, status) if task and status else None
        if rid and rid in seen_ids:
            continue
        if task_status and task_status in seen_task_status:
            continue
        if rid:
            seen_ids.add(rid)
        if task_status:
            seen_task_status.add(task_status)
        out.append(dict(req))
    return out


def merge_requirement_sets(
    jira_requirements: list[dict[str, str]],
    ladr_requirements: list[dict[str, str]],
) -> list[dict[str, str]]:
    merged = [dict(r) for r in jira_requirements]
    seen = {r["id"] for r in merged}
    for req in dedupe_ladr_requirements(ladr_requirements):
        if req["id"] not in seen:
            merged.append(dict(req))
            seen.add(req["id"])
    return merged


def _unique_requirement_ids(ids: list[str]) -> list[str]:
    """Preserve order; drop blanks and duplicate ids (e.g. repeated L1 from merged Confluence pages)."""
    seen: set[str] = set()
    unique: list[str] = []
    for rid in ids:
        if not rid or rid in seen:
            continue
        seen.add(rid)
        unique.append(rid)
    return unique


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("–", "-").replace("—", "-")).strip()


def _detect_task_status(haystack: str) -> tuple[str | None, str | None]:
    norm = _normalize(haystack)
    task_hit: str | None = None
    status_hit: str | None = None
    for task in ESS_TASKS:
        aliases = TASK_ALIASES.get(task.lower(), (task.lower(),))
        if any(alias in norm or task.lower() in norm for alias in aliases):
            task_hit = task
            break
    for status in ESS_STATUSES:
        aliases = STATUS_ALIASES.get(status.lower(), (status.lower(),))
        if any(re.search(rf"\b{re.escape(alias)}\b", norm) for alias in aliases):
            status_hit = status
            break
    return task_hit, status_hit


def map_testcases_to_requirements(
    cases: list[Any],
    requirements: list[dict[str, str]],
) -> None:
    """Map test cases to Jira AC and LADR requirements using semantic ESS matching."""
    jira_reqs = [r for r in requirements if not str(r.get("source", "")).lower().startswith("ladr") and r["id"].startswith("R")]
    ladr_reqs = [r for r in requirements if r["id"].startswith("L") or r.get("source") == "ladr"]

    for tc in cases:
        haystack = " ".join(
            [
                getattr(tc, "summary", "") or "",
                getattr(tc, "story", "") or "",
                " ".join((getattr(tc, "steps", None) or {}).values()),
            ]
        )
        norm = _normalize(haystack)
        mapped: set[str] = set()

        # Explicit R# in summary
        for req in requirements:
            rid = req["id"]
            num = rid[1:] if len(rid) > 1 and rid[0] in "RL" else ""
            if num.isdigit() and re.search(rf"\b{rid}\b", haystack, re.IGNORECASE):
                mapped.add(rid)

        task, status = _detect_task_status(haystack)

        # LADR milestone requirements
        for req in ladr_reqs:
            if req.get("kind") == "passport_scenario":
                txt = _normalize(req.get("text", ""))
                if "mvp full" in txt and ("mvp" in norm or "full package" in norm):
                    mapped.add(req["id"])
                elif "incremental to full" in txt and "incremental" in norm and "full" in norm:
                    mapped.add(req["id"])
                elif "mdu to full" in txt and "mdu" in norm and "full" in norm:
                    mapped.add(req["id"])
                elif "mdu in pick" in txt and "mdu" in norm and "pick" in norm:
                    mapped.add(req["id"])
                elif txt.startswith("incremental") and "incremental" in norm:
                    mapped.add(req["id"])
                continue
            req_task = req.get("task")
            req_status = req.get("status")
            if req_task and req_status:
                if task == req_task and status == req_status:
                    mapped.add(req["id"])
                    continue
                req_norm = _normalize(f"{req_task} {req_status}")
                if req_norm.replace(" ", "") in norm.replace(" ", "") or (
                    req_task.lower() in norm and req_status.lower() in norm
                ):
                    mapped.add(req["id"])
            elif req.get("kind") == "status_code":
                if "8000" in norm or ("failure" in norm and "order" in norm):
                    if "8000" in req.get("text", "") or "failure" in req.get("text", "").lower():
                        mapped.add(req["id"])
                if "9000" in norm or "status_error" in norm or "status error" in norm:
                    if "9000" in req.get("text", "") or "error" in req.get("text", "").lower():
                        mapped.add(req["id"])

        # Token overlap for Jira AC (legacy path)
        for req in jira_reqs:
            rid = req["id"]
            if rid in mapped:
                continue
            tokens = [t for t in re.split(r"\W+", req.get("text", "").lower()) if len(t) > 4]
            if tokens and sum(1 for t in tokens if t in norm) >= max(2, len(tokens) // 3):
                mapped.add(rid)

        # Infer Jira AC from LADR / ESS coverage
        for rid, hints in JIRA_AC_INFERENCE.items():
            if rid in mapped:
                continue
            if any(h in norm for h in hints):
                if rid == "R1" and task:
                    mapped.add(rid)
                elif rid == "R2" and (task or "status" in norm):
                    mapped.add(rid)
                elif rid == "R3" and (
                    status == "Failure"
                    or "8000" in norm
                    or "9000" in norm
                    or ("failure" in norm and any(t in norm for t in ("order", "registration")))
                ):
                    mapped.add(rid)

        if not mapped and len(jira_reqs) == 1:
            mapped.add(jira_reqs[0]["id"])

        tc.mapped_requirements = sorted(
            mapped,
            key=lambda x: (0 if x.startswith("R") else 1, int(x[1:]) if x[1:].isdigit() else 0),
        )


def build_ladr_traceability(
    cases: list[Any],
    ladr_requirements: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Map each LADR requirement (L1…Ln) to test case IDs for report traceability."""
    ladr_requirements = dedupe_ladr_requirements(ladr_requirements)
    if not ladr_requirements:
        return []

    tc_by_req: dict[str, list[str]] = {r["id"]: [] for r in ladr_requirements if r.get("id")}
    for tc in cases:
        if isinstance(tc, dict):
            tc_id = str(tc.get("id") or tc.get("summary") or "")
            mapped = tc.get("mapped_requirements") or []
        else:
            tc_id = str(getattr(tc, "id", None) or getattr(tc, "summary", "") or "")
            mapped = getattr(tc, "mapped_requirements", []) or []
        for rid in mapped:
            if rid.startswith("L") and rid in tc_by_req and tc_id:
                if tc_id not in tc_by_req[rid]:
                    tc_by_req[rid].append(tc_id)

    rows: list[dict[str, Any]] = []
    for req in ladr_requirements:
        rid = req.get("id") or ""
        if not rid.startswith("L"):
            continue
        test_ids = tc_by_req.get(rid) or []
        rows.append(
            {
                "id": rid,
                "text": req.get("text") or "",
                "task": req.get("task"),
                "status": req.get("status"),
                "testCaseIds": test_ids,
                "mapped": bool(test_ids),
            }
        )
    return rows


def compute_testplan_coverage(
    cases: list[Any],
    requirements: list[dict[str, str]],
    *,
    jira_requirements: list[dict[str, str]] | None = None,
    ladr_requirements: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    from testplan_gwt import has_complete_gwt

    jira_reqs = jira_requirements or [r for r in requirements if r["id"].startswith("R")]
    ladr_reqs = ladr_requirements or [r for r in requirements if r["id"].startswith("L")]

    covered: set[str] = set()
    for tc in cases:
        covered.update(getattr(tc, "mapped_requirements", []) or [])

    jira_ids = _unique_requirement_ids([r["id"] for r in jira_reqs if r.get("id")])
    ladr_ids = _unique_requirement_ids([r["id"] for r in dedupe_ladr_requirements(ladr_reqs) if r.get("id")])
    all_ids = jira_ids + ladr_ids
    all_id_set = set(all_ids)

    jira_covered = len(covered & set(jira_ids))
    ladr_covered = len(covered & set(ladr_ids))

    if all_ids:
        pct = round(100 * len(covered & all_id_set) / len(all_ids), 1)
    elif jira_ids:
        pct = round(100 * jira_covered / len(jira_ids), 1)
    else:
        pct = "NA"

    complete_gwt = sum(1 for tc in cases if has_complete_gwt(getattr(tc, "steps", {}) or {}))

    detail_parts = [f"{len(cases)} test cases", f"{complete_gwt}/{len(cases)} full Given When Then" if cases else "0 Given When Then"]
    if ladr_ids:
        detail_parts.append(f"{ladr_covered}/{len(ladr_ids)} LADR scenarios covered")
    if jira_ids:
        detail_parts.append(f"{jira_covered}/{len(jira_ids)} Jira acceptance criteria covered")

    uncovered_jira = [r for r in jira_ids if r not in covered]
    uncovered_ladr = [r for r in ladr_ids if r not in covered]

    return {
        "testplanCoveragePct": pct,
        "requirementCount": len(all_ids) or len(jira_ids),
        "requirementsCovered": len(covered & all_id_set) if all_ids else jira_covered,
        "jiraRequirementCount": len(jira_ids),
        "jiraRequirementsCovered": jira_covered,
        "ladrRequirementCount": len(ladr_ids),
        "ladrRequirementsCovered": ladr_covered,
        "testCaseCount": len(cases),
        "completeGwtCount": complete_gwt,
        "uncoveredRequirements": uncovered_jira + uncovered_ladr,
        "uncoveredJiraRequirements": uncovered_jira,
        "uncoveredLadrRequirements": uncovered_ladr,
    }


def format_testplan_coverage_detail(coverage: dict[str, Any], source_hint: str = "") -> str:
    parts: list[str] = []
    tc_count = coverage.get("testCaseCount", 0)
    gwt_complete = coverage.get("completeGwtCount", 0)
    parts.append(f"{tc_count} test cases")
    parts.append(f"{gwt_complete}/{tc_count} full Given When Then" if tc_count else "0 Given When Then")
    ladr_total = coverage.get("ladrRequirementCount", 0)
    ladr_covered = coverage.get("ladrRequirementsCovered", 0)
    jira_total = coverage.get("jiraRequirementCount", 0)
    jira_covered = coverage.get("jiraRequirementsCovered", 0)
    if ladr_total:
        parts.append(f"{ladr_covered}/{ladr_total} LADR scenarios covered")
    if jira_total:
        parts.append(f"{jira_covered}/{jira_total} Jira acceptance criteria covered")
    elif coverage.get("requirementCount"):
        parts.append(
            f"{coverage.get('requirementsCovered', 0)}/{coverage.get('requirementCount', 0)} acceptance criteria covered"
        )
    if source_hint:
        parts.append(source_hint)
    return " · ".join(parts)


def infer_ladr_requirements_from_jira(jira_data: dict[str, Any]) -> list[dict[str, str]]:
    """When Confluence is not linked but comments reference LADR, use the standard ESS table."""
    texts = collect_jira_texts(jira_data)
    if not any(LADR_URL_HINT_RE.search(t or "") for t in texts):
        return []
    blob = "ESS " + " ".join(texts)
    return parse_ladr_ess_requirements(blob, source="ladr")


def fetch_and_cache_confluence_for_issue(
    issue_key: str,
    jira_data: dict[str, Any] | None = None,
    *,
    site: str = "wbdstreaming.atlassian.net",
) -> dict[str, Any]:
    """Resolve Confluence URLs from Jira cache, fetch pages, extract LADR requirements."""
    load_dotenv()
    if jira_data is None:
        jira_path = repo_root() / "reports" / ".cache" / f"{issue_key.upper()}-jira.json"
        jira_data = json.loads(jira_path.read_text(encoding="utf-8")) if jira_path.exists() else {}

    texts = collect_jira_texts(jira_data)
    urls = merge_confluence_url_lists(
        extract_confluence_urls(texts),
        extract_confluence_from_jira_links(jira_data),
    )
    pages: list[dict[str, Any]] = []
    all_ladr: list[dict[str, str]] = []

    for ref in urls:
        page_id = ref["pageId"]
        try:
            page = fetch_confluence_page_body(page_id, site=site)
            body = page.get("bodyText") or ""
            ladr_reqs = parse_ladr_ess_requirements(body, source="ladr")
            if not ladr_reqs:
                ladr_reqs = parse_passport_confluence_requirements(body, source="ladr")
            if not ladr_reqs:
                ladr_reqs = parse_generic_confluence_requirements(body, source="ladr")
            page["ladrRequirements"] = ladr_reqs
            pages.append(page)
            all_ladr.extend(ladr_reqs)
        except RuntimeError as exc:
            pages.append(
                {
                    "pageId": page_id,
                    "url": ref["url"],
                    "error": str(exc),
                    "ladrRequirements": [],
                }
            )

    if not all_ladr and jira_data:
        all_ladr = infer_ladr_requirements_from_jira(jira_data)

    all_ladr = dedupe_ladr_requirements(all_ladr)

    payload = {
        "issueKey": issue_key.upper(),
        "confluenceUrls": urls,
        "pages": pages,
        "ladrRequirements": all_ladr,
        "status": (
            "ok"
            if all_ladr
            else ("ok" if pages and not all(p.get("error") for p in pages) else ("no_links" if not urls else "partial"))
        ),
    }
    out = confluence_cache_path(issue_key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
