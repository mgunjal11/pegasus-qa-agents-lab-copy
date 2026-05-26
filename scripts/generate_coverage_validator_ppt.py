#!/usr/bin/env python3
"""Generate management PPT explaining msc-code-coverage-validator and report sections."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "MSC-Code-Coverage-Validator-Guide.pptx"

# Brand colors
NAVY = RGBColor(0x1E, 0x40, 0xAF)
BLUE = RGBColor(0x25, 0x63, 0xEB)
TEAL = RGBColor(0x0E, 0x74, 0x90)
PURPLE = RGBColor(0x5B, 0x21, 0xB6)
GREEN = RGBColor(0x15, 0x80, 0x3D)
ORANGE = RGBColor(0xEA, 0x58, 0x0C)
SLATE = RGBColor(0x33, 0x41, 0x55)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x64, 0x74, 0x8B)
DARK = RGBColor(0x0F, 0x17, 0x2A)


def set_slide_bg(slide, rgb: RGBColor):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = rgb


def add_title_bar(slide, title: str, accent: RGBColor, number: str | None = None):
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(1.05))
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent
    bar.line.fill.background()
    if number:
        circle = slide.shapes.add_shape(9, Inches(0.35), Inches(0.22), Inches(0.55), Inches(0.55))
        circle.fill.solid()
        circle.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        circle.fill.transparency = 0.15
        circle.line.fill.background()
        tf = circle.text_frame
        tf.text = number
        p = tf.paragraphs[0]
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        left = Inches(1.05)
    else:
        left = Inches(0.45)
    box = slide.shapes.add_textbox(left, Inches(0.18), Inches(8.5), Inches(0.7))
    tf = box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE


def add_bullets(slide, items: list[str | tuple[str, int]], top=1.35, left=0.55, width=8.8, height=5.5):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        text, size = item if isinstance(item, tuple) else (item, 18)
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.level = 0
        p.font.size = Pt(size)
        p.font.color.rgb = DARK
        p.space_after = Pt(10)
        if text.startswith("  •"):
            p.level = 1
            p.font.size = Pt(max(size - 2, 14))
            p.font.color.rgb = SLATE


def add_subtitle(slide, text: str, top=1.15):
    box = slide.shapes.add_textbox(Inches(0.55), Inches(top), Inches(8.8), Inches(0.45))
    tf = box.text_frame
    tf.text = text
    p = tf.paragraphs[0]
    p.font.size = Pt(14)
    p.font.italic = True
    p.font.color.rgb = MUTED


def title_slide(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, NAVY)
    box = slide.shapes.add_textbox(Inches(0.7), Inches(1.8), Inches(8.6), Inches(1.2))
    tf = box.text_frame
    tf.text = "MSC Code Coverage Validator"
    p = tf.paragraphs[0]
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = WHITE
    sub = slide.shapes.add_textbox(Inches(0.7), Inches(3.0), Inches(8.6), Inches(1.0))
    stf = sub.text_frame
    stf.text = "Automated Jira ↔ GitHub validation with\ndev/QA coverage reporting for MSC stories"
    sp = stf.paragraphs[0]
    sp.font.size = Pt(20)
    sp.font.color.rgb = RGBColor(0xBF, 0xDB, 0xFE)
    foot = slide.shapes.add_textbox(Inches(0.7), Inches(5.8), Inches(8.6), Inches(0.5))
    ftf = foot.text_frame
    ftf.text = "Media Supply Chain · wbdstreaming.atlassian.net · TestCursor"
    fp = ftf.paragraphs[0]
    fp.font.size = Pt(12)
    fp.font.color.rgb = RGBColor(0x93, 0xC5, 0xFD)


def content_slide(prs, title, accent, number, subtitle, bullets):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, WHITE)
    add_title_bar(slide, title, accent, number)
    if subtitle:
        add_subtitle(slide, subtitle)
    add_bullets(slide, bullets, top=1.55 if subtitle else 1.35)


def two_column_slide(prs, title, accent, number, left_title, left_items, right_title, right_items):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, WHITE)
    add_title_bar(slide, title, accent, number)
    lt = slide.shapes.add_textbox(Inches(0.55), Inches(1.25), Inches(4.2), Inches(0.4))
    lt.text_frame.text = left_title
    lt.text_frame.paragraphs[0].font.bold = True
    lt.text_frame.paragraphs[0].font.size = Pt(16)
    lt.text_frame.paragraphs[0].font.color.rgb = accent
    add_bullets(slide, left_items, top=1.65, left=0.55, width=4.2, height=4.8)
    rt = slide.shapes.add_textbox(Inches(5.1), Inches(1.25), Inches(4.2), Inches(0.4))
    rt.text_frame.text = right_title
    rt.text_frame.paragraphs[0].font.bold = True
    rt.text_frame.paragraphs[0].font.size = Pt(16)
    rt.text_frame.paragraphs[0].font.color.rgb = accent
    add_bullets(slide, right_items, top=1.65, left=5.1, width=4.2, height=4.8)


def build():
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    title_slide(prs)

    content_slide(
        prs, "What is it?", NAVY, None, None,
        [
            "An AI-powered validator for MSC Jira stories on wbdstreaming.atlassian.net",
            "Pulls acceptance criteria from Jira and compares them to linked GitHub PR(s)",
            "Maps each requirement to production code, dev tests, and QA handoff scope",
            "Produces a downloadable HTML report with coverage % and management-ready sections",
            "Separates what Development proves (unit/integration) from what QA must still verify (E2E, manual, regression)",
        ],
    )

    content_slide(
        prs, "Why use it?", BLUE, None, "Value for Engineering & QA leadership",
        [
            "Single view of requirement → code → test traceability before release",
            "Reduces manual AC review time and missed gaps between Jira and PR",
            "Clear dev vs QA ownership — avoids duplicate testing or untested handoffs",
            "Quantified metrics (dev code %, dev test %, CI coverage) for release decisions",
            "Actionable gaps, assumptions, and recommended next steps in one report",
        ],
    )

    content_slide(
        prs, "How to run", TEAL, None, "Slash command in Cursor (default: auto + write report)",
        [
            "/msc-code-coverage-validator MSC-204417",
            "  • Fetches Jira story + remote links (Atlassian MCP)",
            "  • Resolves GitHub PR or branch compare (gh CLI / cache)",
            "  • Analyzes code & tests, writes HTML report",
            "",
            "Reuse cached data:  @msc-code-coverage-validator MSC-204417 --from-cache --auto",
            "",
            "Output: reports/{KEY}-{MM-DD-YYYY-HH-MM-SS}-{TZ}.html  (laptop local time)",
        ],
    )

    content_slide(
        prs, "Workflow (8 steps)", SLATE, None, None,
        [
            "1. Parse run options (flags, manifest, defaults)",
            "2. Resolve Jira issue key",
            "3. Fetch Jira story & extract requirements (R1, R2, …)",
            "4. Resolve linked GitHub PR(s) or branch compare",
            "5. Fetch PR diff, tests, and CI status",
            "6. Map requirements → code, tests, dev/QA ownership",
            "7. Compute coverage percentages & verdict",
            "8. Write timestamped HTML report + update manifest cache",
        ],
    )

    content_slide(
        prs, "Report overview", NAVY, None, "Header + 7 numbered sections",
        [
            "Header: Story title, Jira link, status, generated date, overall verdict",
            "Verdict: Pass · Pass with gaps · Fail (with one-line rationale)",
            "",
            "Section 1 — Coverage summary        (metrics dashboard)",
            "Section 2 — Linked PR(s)            (source code traceability)",
            "Section 3 — Dev vs QA test ownership (who tests what)",
            "Section 4 — Requirements traceability (AC matrix)",
            "Section 5 — Implementation review     (strengths & gaps)",
            "Section 6 — Assumptions & open questions",
            "Section 7 — Recommended actions       (dev & QA to-do list)",
        ],
    )

    content_slide(
        prs, "1 · Coverage summary", BLUE, "1",
        "Executive dashboard — five metric cards",
        [
            "Dev code coverage % — Share of Jira AC with matching production code in the PR/branch",
            "  • Green ≥85% · Amber 70–84.9% · Red <70%",
            "Dev unit / integration test coverage % — Dev-owned AC covered by automated tests in PR",
            "QA scope remaining — Count of requirements still needing QA (E2E, manual, regression)",
            "CI line coverage % — Line coverage from PR checks (Codecov, SonarQube, pytest-cov); NA if no PR",
            "CI branch coverage % — Branch coverage from CI; NA when unavailable",
        ],
    )

    content_slide(
        prs, "2 · Linked PR(s)", RGBColor(0x4F, 0x46, 0xE5), "2",
        "Where the implementation lives in GitHub",
        [
            "Lists PR(s) linked to the Jira story (remote links, description, or search)",
            "Shows author, merge state, and CI status per PR",
            "If no PR is linked: notes branch compare (e.g. develop vs main) and key commits",
            "Helps leadership confirm traceability — every story should map to reviewable code",
            "Related PRs (fixes, dependencies) may appear with context notes",
        ],
    )

    two_column_slide(
        prs, "3 · Dev vs QA test ownership", TEAL, "3",
        "Covered by dev tests",
        [
            "Requirements proven by unit or integration tests already in the PR",
            "Lists requirement ID + test name / file evidence",
            "Dev responsibility — should pass in CI before merge",
        ],
        "QA handoff",
        [
            "Requirements NOT fully covered by dev automated tests",
            "E2E — end-to-end flows (UI, Monitor, staging)",
            "Manual / Spot-check — exploratory or payload verification",
            "Regression — confirm related fixes in QA build",
        ],
    )

    content_slide(
        prs, "4 · Requirements traceability", PURPLE, "4",
        "AC-by-AC matrix — the core audit table",
        [
            "ID — Requirement number (R1, R2, …) from Jira acceptance criteria",
            "Requirement — Text of the AC or derived scope item",
            "Code — Implemented · Partial · Missing · N/A",
            "Dev tests — Covered · Partial · Missing + Unit/Integration tier",
            "Owner — Dev · Shared · QA (who owns primary verification)",
            "QA scope — None · E2E · Manual · Spot-check · Regression",
            "Evidence — File paths, functions, test names cited from PR diff",
        ],
    )

    two_column_slide(
        prs, "5 · Implementation review", GREEN, "5",
        "✓ Correctly implemented",
        [
            "What matches the Jira story and is backed by code evidence",
            "Summarizes strengths: tests, architecture, completeness",
            "Green panel — positive findings for stakeholders",
        ],
        "⚠ Gaps and concerns",
        [
            "Missing PR links, untested AC, contradictions vs Jira",
            "Severity: High · Medium · Critical",
            "Amber panel — risks to address before release",
        ],
    )

    content_slide(
        prs, "6 · Assumptions & open questions", SLATE, "6",
        "Context and uncertainties the validator inferred",
        [
            "Repository assumed for implementation (when not explicit in Jira)",
            "Commit author ↔ assignee mapping assumptions",
            "Linked LADR / wiki docs used to interpret supplemental requirements",
            "Items needing human confirmation — not treated as pass/fail gates",
            "Useful for sprint review and clarification with product/dev",
        ],
    )

    content_slide(
        prs, "7 · Recommended actions", ORANGE, "7",
        "Prioritized to-do list for Dev and QA",
        [
            "Numbered actions derived from gaps and QA handoff items",
            "Dev actions — add tests, link PR, fix traceability gaps",
            "QA actions — E2E scenarios, staging spot-checks, regression passes",
            "Each action ties back to a requirement ID where applicable",
            "Orange panel — clear next steps for the team before sign-off",
        ],
    )

    content_slide(
        prs, "Verdicts & color coding", NAVY, None, None,
        [
            "Pass — Dev code coverage strong; dev tests and CI acceptable; minimal QA gaps",
            "Pass with gaps — Code largely complete; some dev test or QA handoff items remain",
            "Fail — Significant missing implementation, tests, or AC contradictions",
            "",
            "Metric card colors:  Green ≥85%  ·  Amber 70–84.9%  ·  Red <70%  ·  Gray NA",
            "Report filename uses laptop local time: MSC-204417-05-26-2026-22-12-00-IST.html",
        ],
    )

    content_slide(
        prs, "Example & next steps", BLUE, None, "MSC-204417 — V2 caption messaging in ESS",
        [
            "Run:  /msc-code-coverage-validator MSC-204417",
            "Sample report: reports/MSC-204417-*-IST.html",
            "Typical outcome: Pass with gaps — 100% dev code, 83% dev tests, 2 QA items",
            "",
            "Install permissions once:  python scripts/install_coverage_validator_permissions.py",
            "Questions? See .cursor/skills/msc-code-coverage-validator/SKILL.md",
        ],
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT))
    print(OUT.resolve())


if __name__ == "__main__":
    build()
