#!/usr/bin/env python3
"""Generate management PPT for msc-code-coverage-validator (updated 7-card report)."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]


def build(out: Path) -> None:
    NAVY = RGBColor(0x1E, 0x40, 0xAF)
    BLUE = RGBColor(0x25, 0x63, 0xEB)
    SLATE = RGBColor(0x33, 0x41, 0x55)
    GREEN = RGBColor(0x15, 0x80, 0x3D)
    ORANGE = RGBColor(0xC2, 0x41, 0x0C)
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    MUTED = RGBColor(0x64, 0x74, 0x8B)
    DARK = RGBColor(0x0F, 0x17, 0x2A)

    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    def title_slide():
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = NAVY
        t = s.shapes.add_textbox(Inches(0.7), Inches(2.0), Inches(8.6), Inches(1.2))
        t.text_frame.text = "MSC Code Coverage Validator"
        p = t.text_frame.paragraphs[0]
        p.font.size = Pt(38)
        p.font.bold = True
        p.font.color.rgb = WHITE
        sub = s.shapes.add_textbox(Inches(0.7), Inches(3.2), Inches(8.6), Inches(1.2))
        sub.text_frame.text = (
            "Jira acceptance criteria ↔ GitHub implementation\n"
            "Management-ready coverage report for MSC stories"
        )
        sub.text_frame.paragraphs[0].font.size = Pt(18)
        sub.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xBF, 0xDB, 0xFE)
        foot = s.shapes.add_textbox(Inches(0.7), Inches(5.9), Inches(8.6), Inches(0.4))
        foot.text_frame.text = "Pegasus QA Agents Lab · Media Supply Chain · wbdstreaming.atlassian.net"
        foot.text_frame.paragraphs[0].font.size = Pt(11)
        foot.text_frame.paragraphs[0].font.color.rgb = RGBColor(0x93, 0xC5, 0xFD)

    def bar_slide(title, accent, num, subtitle, bullets):
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        bar = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(1.05))
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent
        bar.line.fill.background()
        if num:
            c = s.shapes.add_shape(9, Inches(0.35), Inches(0.22), Inches(0.55), Inches(0.55))
            c.fill.solid()
            c.fill.fore_color.rgb = WHITE
            c.fill.transparency = 0.15
            c.line.fill.background()
            c.text_frame.text = num
            c.text_frame.paragraphs[0].font.size = Pt(14)
            c.text_frame.paragraphs[0].font.bold = True
            c.text_frame.paragraphs[0].font.color.rgb = WHITE
            c.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            c.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
            left = Inches(1.05)
        else:
            left = Inches(0.45)
        tb = s.shapes.add_textbox(left, Inches(0.18), Inches(8.5), Inches(0.7))
        tb.text_frame.text = title
        tb.text_frame.paragraphs[0].font.size = Pt(26)
        tb.text_frame.paragraphs[0].font.bold = True
        tb.text_frame.paragraphs[0].font.color.rgb = WHITE
        top = 1.35
        if subtitle:
            st = s.shapes.add_textbox(Inches(0.55), Inches(1.15), Inches(8.8), Inches(0.4))
            st.text_frame.text = subtitle
            st.text_frame.paragraphs[0].font.size = Pt(13)
            st.text_frame.paragraphs[0].font.italic = True
            st.text_frame.paragraphs[0].font.color.rgb = MUTED
            top = 1.55
        box = s.shapes.add_textbox(Inches(0.55), Inches(top), Inches(8.8), Inches(5.6))
        tf = box.text_frame
        tf.word_wrap = True
        for i, item in enumerate(bullets):
            text, size = item if isinstance(item, tuple) else (item, 17)
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = text
            p.font.size = Pt(size)
            p.font.color.rgb = DARK if not text.startswith("  ") else SLATE
            p.space_after = Pt(8)
            if text.startswith("  "):
                p.level = 1
                p.font.size = Pt(max(size - 2, 13))

    title_slide()

    bar_slide("What does this agent do?", NAVY, None, None, [
        "Validates MSC Jira user stories against linked GitHub PR(s) or branch code",
        "Reads acceptance criteria (AC) from Jira and maps each to production code and tests",
        "Separates what Development proves (unit/integration tests) from what QA must still verify",
        "Produces a timestamped HTML report for engineering and QA leadership",
        "Run in Cursor:  /msc-code-coverage-validator MSC-204417",
    ])

    bar_slide("Why leadership cares", BLUE, None, "Release confidence in one view", [
        "Traceability — every AC tied to code evidence before sign-off",
        "Clear dev vs QA ownership — avoids duplicate testing or missed handoffs",
        "Quantified metrics — dev code %, dev test %, QA scope, CI coverage, open gaps",
        "Actionable output — gaps, assumptions, and recommended next steps",
        "Audit-friendly — downloadable HTML with requirement-level evidence",
    ])

    bar_slide("How it works", SLATE, None, "8-step automated workflow", [
        "1. Fetch Jira story + remote PR links (Atlassian MCP)",
        "2. Resolve GitHub PR or branch compare (gh CLI / cache)",
        "3. Extract requirements R1, R2, … from acceptance criteria",
        "4. Map each requirement → code status, dev tests, QA scope",
        "5. Compute coverage percentages and overall verdict",
        "6. Write HTML report (laptop local timezone filename)",
    ])

    bar_slide("Report structure", NAVY, None, "Header + 7 numbered sections", [
        "Header — Story title, Jira link, status, verdict (Pass / Pass with gaps / Fail)",
        "§1 Coverage summary — 7 metric cards in 3 logical groups",
        "§2 Linked PR(s) — Where code lives; CI status",
        "§3 Dev vs QA test ownership — Who tests what",
        "§4 Requirements traceability — AC-by-AC audit table",
        "§5 Implementation review — Strengths and gaps",
        "§6 Assumptions · §7 Recommended actions",
    ])

    bar_slide("§1 Coverage summary", BLUE, "1", "7 cards · 3 groups · restrained color coding", [
        "Implementation & tests",
        "  • Dev code coverage — % of Jira AC with matching production code (green ≥85%)",
        "  • Dev unit / integration test coverage — dev-owned AC covered by PR tests",
        "  • Requirements mapped — e.g. 3/3 AC (R1–R3) extracted from Jira",
        "QA & release risk",
        "  • QA scope remaining — items needing E2E, manual, or regression",
        "  • Open gaps — High / Medium counts from implementation review",
        "CI pipeline coverage",
        "  • CI line coverage · CI branch coverage (NA when no PR)",
    ])

    bar_slide("§2 Linked PR(s)", RGBColor(0x37, 0x30, 0xA3), "2", "Source code traceability", [
        "Lists PR(s) linked to the Jira story (remote links, description, or search)",
        "Shows author, state (open/merged), and CI outcome per PR",
        "If no PR: notes branch compare (e.g. develop vs main) and key commits",
        "Answers: “Where is this story implemented and is it reviewable in GitHub?”",
    ])

    bar_slide("§3 Dev vs QA ownership", RGBColor(0x0E, 0x74, 0x90), "3", "Two-column handoff view", [
        "Covered by dev tests — Requirements proven by unit/integration tests in the PR",
        "  • Lists requirement ID + test file / test name evidence",
        "QA handoff — What automated tests do NOT fully cover",
        "  • E2E — end-to-end flows (Monitor, staging, UI)",
        "  • Manual / Spot-check — exploratory or payload verification",
        "  • Regression — confirm related fixes in QA build",
    ])

    bar_slide("§4 Requirements traceability", RGBColor(0x5B, 0x21, 0xB6), "4", "Core audit matrix", [
        "One row per acceptance criterion (R1, R2, …)",
        "Code — Implemented · Partial · Missing",
        "Dev tests — Covered · Partial · Missing + Unit/Integration tier",
        "Owner — Dev · Shared · QA",
        "QA scope — None · E2E · Manual · Spot-check · Regression",
        "Evidence — File paths, functions, and test names from the PR diff",
    ])

    bar_slide("§5–§7 Review & actions", GREEN, "5–7", "Findings and next steps", [
        "§5 Implementation review",
        "  • Correctly implemented — strengths backed by code evidence",
        "  • Gaps and concerns — severity: High · Medium · Critical",
        "§6 Assumptions and open questions — Inferred context needing confirmation",
        "§7 Recommended actions — Numbered dev and QA to-do list before release",
    ])

    bar_slide("Verdicts & metric colors", NAVY, None, None, [
        "Pass — Strong dev code and tests; minimal QA gaps",
        "Pass with gaps — Code largely complete; QA handoff or dev test gaps remain",
        "Fail — Significant missing implementation, tests, or AC contradictions",
        "",
        "Metric colors:  Green ≥85%  ·  Amber 70–84.9%  ·  Red <70%  ·  Gray NA",
        "Report file:  reports/MSC-204417-05-26-2026-22-47-51-IST.html",
    ])

    bar_slide("Getting started", BLUE, None, "Pegasus QA Agents Lab", [
        "git clone https://github.com/mgunjal11/pegasus-qa-agents-lab",
        "Enable Atlassian MCP + gh CLI; pip install -r requirements.txt",
        "python scripts/install_coverage_validator_permissions.py",
        "In Cursor:  /msc-code-coverage-validator MSC-204417",
        "",
        "Sample: MSC-204417 — 100% dev code · 83% dev tests · 2 QA items · Pass with gaps",
    ])

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    print(out.resolve())


if __name__ == "__main__":
    import sys

    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "reports" / "MSC-Code-Coverage-Validator-Guide.pptx"
    build(dest)
