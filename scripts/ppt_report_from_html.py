"""Parse MSC coverage validation HTML into slide-friendly structures."""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReportSection:
    num: str
    title: str
    lead: str = ""
    bullets: list[str] = field(default_factory=list)
    table_headers: list[str] = field(default_factory=list)
    table_rows: list[list[str]] = field(default_factory=list)


def _strip_tags(fragment: str, *, br: str = " ") -> str:
    t = re.sub(r"<br\s*/?>", br, fragment, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return html_lib.unescape(re.sub(r"\s+", " ", t)).strip()


def _section_body(html: str, class_name: str) -> str:
    m = re.search(
        rf'<section class="report-section {re.escape(class_name)}">(.*?)</section>',
        html,
        re.S | re.I,
    )
    return m.group(1) if m else ""


def _section_title(body: str, default: str) -> str:
    m = re.search(r'class="heading-label-row">([^<]+)<', body)
    return _strip_tags(m.group(1)) if m else default


def _metric_cards(body: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(
        r'class="label">([^<]+)</div>.*?class="metric-value">([^<]+)</div>'
        r'(?:.*?class="note">([^<]*)</div>)?',
        body,
        re.S,
    ):
        label = _strip_tags(m.group(1))
        val = _strip_tags(m.group(2))
        note = _strip_tags(m.group(3)) if m.lastindex and m.group(3) else ""
        line = f"{label}: {val}"
        if note:
            line += f" — {note[:70]}"
        out.append(line)
    return out


def _table_rows(body: str, *, max_rows: int = 6) -> tuple[list[str], list[list[str]]]:
    thead = re.search(r"<thead>.*?<tr>(.*?)</tr>", body, re.S | re.I)
    headers: list[str] = []
    if thead:
        headers = [_strip_tags(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", thead.group(1), re.S)]
        headers = [h for h in headers if h][:7]
    rows: list[list[str]] = []
    tbody = re.search(r"<tbody>(.*?)</tbody>", body, re.S | re.I)
    if tbody:
        for tr in re.findall(r"<tr>(.*?)</tr>", tbody.group(1), re.S | re.I)[:max_rows]:
            cells = [_strip_tags(c)[:80] for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if cells:
                rows.append(cells[: len(headers) or 7])
    return headers, rows


def _list_items(body: str, *, panel_class: str | None = None) -> list[str]:
    if panel_class:
        m = re.search(rf'class="review-panel {panel_class}"[^>]*>.*?<ul>(.*?)</ul>', body, re.S | re.I)
        if not m:
            return []
        body = m.group(1)
    else:
        m = re.search(r"<ul>(.*?)</ul>", body, re.S | re.I)
        if not m:
            m = re.search(r"<ol>(.*?)</ol>", body, re.S | re.I)
        if not m:
            return []
        body = m.group(1)
    items = []
    for li in re.findall(r"<li[^>]*>(.*?)</li>", body, re.S | re.I):
        t = _strip_tags(li)
        if t:
            items.append(t[:120])
    return items


def parse_msc_report_html(path: Path | str) -> dict:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    key_m = re.search(r"Coverage validation: (MSC-\d+)", text)
    issue_key = key_m.group(1) if key_m else "MSC-205625"
    title_m = re.search(rf"Coverage validation: {issue_key} — ([^<]+)<", text)
    story_title = _strip_tags(title_m.group(1)) if title_m else issue_key

    verdict_m = re.search(r'class="verdict[^"]*">.*?Pass[^<]{0,40}', text, re.S | re.I)
    verdict_raw = _strip_tags(verdict_m.group(0)) if verdict_m else "Pass with gaps"
    verdict = "Pass with gaps" if "gaps" in verdict_raw.lower() else (
        "Pass" if verdict_raw.lower().startswith("pass") else verdict_raw[:40]
    )

    readiness_m = re.search(
        r'Release readiness score</div>.*?class="metric-value">([^<]+)',
        text,
        re.S | re.I,
    )
    readiness = _strip_tags(readiness_m.group(1)) if readiness_m else "—"

    rb = re.search(r'class="jira-readiness-block".*?<ul>(.*?)</ul>', text, re.S | re.I)
    readiness_items = []
    if rb:
        readiness_items = [
            _strip_tags(li)[:90]
            for li in re.findall(r"<li[^>]*>(.*?)</li>", rb.group(1), re.S | re.I)
        ]

    note_m = re.search(r'class="note-box[^"]*">([^<]+(?:<[^>]+>[^<]*)*)</div>', text, re.S | re.I)
    testplan_note = _strip_tags(note_m.group(1))[:100] if note_m else ""

    sections: list[ReportSection] = []

    # §1 Coverage summary
    b1 = _section_body(text, "section-summary")
    s1_bullets = _metric_cards(b1)
    if not s1_bullets or not s1_bullets[0].lower().startswith("release readiness"):
        rs_m = re.search(r'Release readiness score</div>.*?class="metric-value">([^<]+)', b1, re.S)
        if rs_m:
            s1_bullets.insert(0, f"Release readiness score: {_strip_tags(rs_m.group(1))}")
    sections.append(
        ReportSection("1", _section_title(b1, "Coverage summary"), bullets=s1_bullets[:10])
    )

    # §2 Linked PR(s)
    b2 = _section_body(text, "section-pr")
    h2, r2 = _table_rows(b2, max_rows=4)
    sections.append(
        ReportSection("2", _section_title(b2, "Linked PR(s)"), table_headers=h2, table_rows=r2)
    )

    # §3 Test plan
    b3 = _section_body(text, "section-testplan")
    h3, r3 = _table_rows(b3, max_rows=5)
    s3_bullets: list[str] = []
    if testplan_note:
        s3_bullets.append(testplan_note)
    ladr_m = re.search(r'class="ladr-section-lead">([^<]+)', b3, re.S)
    if ladr_m:
        s3_bullets.append(_strip_tags(ladr_m.group(1))[:110])
    s3_bullets.extend(_list_items(b3, panel_class="review-gaps")[:4])
    sections.append(
        ReportSection(
            "3",
            _section_title(b3, "Attached test plan validation"),
            bullets=s3_bullets,
            table_headers=h3[:5] if h3 else ["TC", "Scenario", "Mapped req", "GWT", "PR alignment"],
            table_rows=[[c[:35] for c in row[:5]] for row in r3],
        )
    )

    # §4 Dev vs QA
    b4 = _section_body(text, "section-ownership")
    lead4_m = re.search(r'class="section-lead[^"]*">([^<]+)', b4, re.S)
    lead4 = _strip_tags(lead4_m.group(1))[:100] if lead4_m else ""
    dev_chunk, qa_chunk = b4, ""
    if "metric-card metric-qa" in b4:
        dev_chunk, qa_chunk = b4.split("metric-card metric-qa", 1)
    s4_bullets = ["Dev-owned (unit / integration in PR):"]
    s4_bullets.extend(
        f"  • {_strip_tags(li)[:95]}"
        for li in re.findall(r"<li[^>]*>(.*?)</li>", dev_chunk, re.S | re.I)[:4]
    )
    s4_bullets.append("QA handoff:")
    s4_bullets.extend(
        f"  • {_strip_tags(li)[:95]}"
        for li in re.findall(r"<li[^>]*>(.*?)</li>", qa_chunk, re.S | re.I)[:4]
    )
    sections.append(
        ReportSection("4", _section_title(b4, "Dev vs QA test ownership"), lead=lead4, bullets=s4_bullets)
    )

    # §5 Traceability
    b5 = _section_body(text, "section-trace")
    lead5_m = re.search(r'class="trace-section-lead">([^<]+)', b5, re.S)
    h5, r5 = _table_rows(b5, max_rows=5)
    compact5 = []
    for row in r5:
        if len(row) >= 6:
            compact5.append([row[0], row[1][:55], row[2], row[3], row[4], row[5]])
        else:
            compact5.append(row)
    sections.append(
        ReportSection(
            "5",
            _section_title(b5, "Requirements traceability"),
            lead=_strip_tags(lead5_m.group(1)) if lead5_m else "",
            table_headers=["ID", "Requirement", "Code", "Dev tests", "Owner", "QA scope"][: len(h5) or 6],
            table_rows=compact5,
        )
    )

    # §6 Implementation review
    b6 = _section_body(text, "section-review")
    pos = _list_items(b6, panel_class="review-positive")
    gaps = _list_items(b6, panel_class="review-gaps")
    s6_bullets = ["✓ Correctly implemented:"] + [f"  {p}" for p in pos[:3]]
    s6_bullets += ["⚠ Gaps and concerns:"] + [f"  {g}" for g in gaps[:5]]
    sections.append(
        ReportSection("6", _section_title(b6, "Implementation review"), bullets=s6_bullets)
    )

    # §7 Assumptions
    b7 = _section_body(text, "section-assumptions")
    sections.append(
        ReportSection("7", _section_title(b7, "Assumptions and open questions"), bullets=_list_items(b7)[:6])
    )

    # §8 Actions
    b8 = _section_body(text, "section-actions")
    ol_m = re.search(r"<ol>(.*?)</ol>", b8, re.S)
    actions = []
    if ol_m:
        actions = [_strip_tags(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", ol_m.group(1), re.S)]
    sections.append(
        ReportSection("8", _section_title(b8, "Recommended actions"), bullets=actions or _list_items(b8))
    )

    gen_m = re.search(r"Generated:\s*([^<\n]+)", text)
    generated = _strip_tags(gen_m.group(1)) if gen_m else ""

    return {
        "issue_key": issue_key,
        "story_title": story_title,
        "verdict": verdict,
        "readiness": readiness,
        "generated": generated,
        "readiness_items": readiness_items[:4],
        "sections": sections,
        "report_file": Path(path).name,
    }
