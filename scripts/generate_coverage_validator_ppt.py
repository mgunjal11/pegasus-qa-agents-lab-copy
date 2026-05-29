#!/usr/bin/env python3
"""Generate MSC Code Coverage Validator deck — WBD QBR brand + executive presentation visuals."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]

# Brand
CORAL = RGBColor(0xFF, 0x5E, 0x4F)
NAVY = RGBColor(0x04, 0x06, 0x6C)
NAVY_LIGHT = RGBColor(0x1E, 0x3A, 0x8A)
GOLD = RGBColor(0xFF, 0xC0, 0x00)
GOLD_DARK = RGBColor(0xD4, 0x9A, 0x00)
LIGHT_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
SOFT_BLUE = RGBColor(0xE8, 0xF0, 0xFE)
SOFT_GOLD = RGBColor(0xFF, 0xF8, 0xE1)
SOFT_CORAL = RGBColor(0xFF, 0xED, 0xEA)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
BODY = RGBColor(0x33, 0x41, 0x55)
MUTED = RGBColor(0x94, 0xA3, 0xB8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x16, 0xA3, 0x4A)
GREEN_BG = RGBColor(0xDC, 0xFC, 0xE7)
AMBER = RGBColor(0xD9, 0x77, 0x06)
AMBER_BG = RGBColor(0xFF, 0xED, 0xD5)
RED = RGBColor(0xDC, 0x26, 0x26)
RED_BG = RGBColor(0xFE, 0xE2, 0xE2)
TEAL = RGBColor(0x00, 0x96, 0x88)
PILOT_ORANGE = RGBColor(0xE8, 0x78, 0x08)
IMPL_GOLD = RGBColor(0xBC, 0xB8, 0x1E)
PILL_GRAY = RGBColor(0x74, 0x74, 0x74)

FONT = "Calibri"
W = Inches(13.333)
H = Inches(7.5)

# Latest validator example — sync with reports/MSC-205625-*-IST.html
REPORT_DEVELOPER = "Mayur Gunjal"
LATEST_EXAMPLE = {
    "key": "MSC-205625",
    "generated": "05-29-2026 12:43 IST",
    "verdict": "Pass with gaps",
    "summary_short": "PFT Clear passport dropped in incremental workflow (SIT)",
    "dev_code_pct": "100%",
    "dev_tests_pct": "75%",
    "testplan_ac_pct": "75%",
    "qa_remaining": "1 item",
    "open_gaps": "2 Med",
    "ci_line_pct": "95.3%",
    "ci_branch_pct": "94.5%",
    "pr_note": "PR #161 pick-genie · MERGED · CI Passed",
    "testplan_note": "Domino Test Plan.xlsx · Inc as Fulll · 5/5 Given/When/Then",
    "report_file": "MSC-205625-05-29-2026-12-43-49-IST.html",
}


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = W
        self.prs.slide_height = H
        self._n = 0

    def blank(self):
        return self.prs.slides.add_slide(self.prs.slide_layouts[6])

    def footer(self, slide):
        self._n += 1
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.92), W, Inches(0.02))
        line.fill.solid()
        line.fill.fore_color.rgb = LIGHT_GRAY
        line.line.fill.background()
        lb = slide.shapes.add_textbox(Inches(0.5), Inches(7.0), Inches(9), Inches(0.35))
        lb.text_frame.text = f"©LTM  |  Privileged and Confidential  |  MSC Code Coverage Validator  |  Developed by {REPORT_DEVELOPER}"
        p = lb.text_frame.paragraphs[0]
        p.font.size = Pt(8)
        p.font.name = FONT
        p.font.color.rgb = MUTED
        rb = slide.shapes.add_textbox(Inches(12.35), Inches(7.0), Inches(0.6), Inches(0.35))
        rb.text_frame.text = str(self._n)
        rb.text_frame.paragraphs[0].font.size = Pt(8)
        rb.text_frame.paragraphs[0].font.name = FONT
        rb.text_frame.paragraphs[0].font.color.rgb = MUTED
        rb.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

    def _accent_bar(self, slide, top=Inches(0)):
        b = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, top, Inches(0.12), H)
        b.fill.solid()
        b.fill.fore_color.rgb = CORAL
        b.line.fill.background()

    def _slide_title(self, slide, title: str, subtitle: str | None = None):
        self._accent_bar(slide)
        tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.32), Inches(12), Inches(0.65))
        tb.text_frame.text = title
        p = tb.text_frame.paragraphs[0]
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.name = FONT
        p.font.color.rgb = NAVY
        if subtitle:
            st = slide.shapes.add_textbox(Inches(0.55), Inches(0.88), Inches(12), Inches(0.38))
            st.text_frame.text = subtitle
            sp = st.text_frame.paragraphs[0]
            sp.font.size = Pt(13)
            sp.font.name = FONT
            sp.font.color.rgb = MUTED

    def _rect(self, slide, l, t, w, h, fill, text=None, font_pt=11, bold=False, color=WHITE, radius=None):
        kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        sh = slide.shapes.add_shape(kind, l, t, w, h)
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
        sh.line.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
        sh.line.width = Pt(0.5)
        if text is not None:
            sh.text_frame.text = text
            p = sh.text_frame.paragraphs[0]
            p.font.size = Pt(font_pt)
            p.font.bold = bold
            p.font.name = FONT
            p.font.color.rgb = color
            p.alignment = PP_ALIGN.CENTER
            sh.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
            sh.text_frame.word_wrap = True
        return sh

    def _icon_circle(self, slide, l, t, size, letter, fill=NAVY):
        o = slide.shapes.add_shape(MSO_SHAPE.OVAL, l, t, size, size)
        o.fill.solid()
        o.fill.fore_color.rgb = fill
        o.line.fill.background()
        o.text_frame.text = letter
        p = o.text_frame.paragraphs[0]
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.name = FONT
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER
        o.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        return o

    def _arrow(self, slide, x1, y1, x2, y2):
        c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
        c.line.color.rgb = GOLD
        c.line.width = Pt(2.5)
        return c

    def _kpi_card(self, slide, l, t, w, h, value, label, sub, fill, value_color=WHITE):
        self._rect(slide, l, t, w, h, fill, radius=True)
        v = slide.shapes.add_textbox(l + Inches(0.1), t + Inches(0.15), w - Inches(0.2), Inches(0.55))
        v.text_frame.text = value
        v.text_frame.paragraphs[0].font.size = Pt(28)
        v.text_frame.paragraphs[0].font.bold = True
        v.text_frame.paragraphs[0].font.name = FONT
        v.text_frame.paragraphs[0].font.color.rgb = value_color
        v.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        lb = slide.shapes.add_textbox(l + Inches(0.08), t + Inches(0.72), w - Inches(0.16), Inches(0.45))
        lb.text_frame.text = label
        lb.text_frame.paragraphs[0].font.size = Pt(11)
        lb.text_frame.paragraphs[0].font.bold = True
        lb.text_frame.paragraphs[0].font.name = FONT
        lb.text_frame.paragraphs[0].font.color.rgb = value_color
        lb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        if sub:
            sb = slide.shapes.add_textbox(l + Inches(0.08), t + h - Inches(0.42), w - Inches(0.16), Inches(0.35))
            sb.text_frame.text = sub
            sb.text_frame.paragraphs[0].font.size = Pt(9)
            sb.text_frame.paragraphs[0].font.name = FONT
            sb.text_frame.paragraphs[0].font.color.rgb = value_color
            sb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    def title_slide(self):
        s = self.blank()
        bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
        bg.fill.solid()
        bg.fill.fore_color.rgb = NAVY
        bg.line.fill.background()
        # decorative circles
        for cx, cy, r, alpha in [(Inches(10.5), Inches(-0.8), Inches(3.2), 0.85), (Inches(11.8), Inches(5.5), Inches(2.0), 0.9)]:
            c = s.shapes.add_shape(MSO_SHAPE.OVAL, cx, cy, r, r)
            c.fill.solid()
            c.fill.fore_color.rgb = NAVY_LIGHT
            c.fill.transparency = alpha
            c.line.fill.background()
        band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.55), W, Inches(0.95))
        band.fill.solid()
        band.fill.fore_color.rgb = GOLD
        band.line.fill.background()
        t1 = s.shapes.add_textbox(Inches(0.85), Inches(1.6), Inches(11), Inches(0.9))
        t1.text_frame.text = "Business Assurance"
        t1.text_frame.paragraphs[0].font.size = Pt(22)
        t1.text_frame.paragraphs[0].font.name = FONT
        t1.text_frame.paragraphs[0].font.color.rgb = GOLD
        t2 = s.shapes.add_textbox(Inches(0.85), Inches(2.35), Inches(11), Inches(1.4))
        t2.text_frame.text = "MSC Code Coverage Validator"
        t2.text_frame.paragraphs[0].font.size = Pt(40)
        t2.text_frame.paragraphs[0].font.bold = True
        t2.text_frame.paragraphs[0].font.name = FONT
        t2.text_frame.paragraphs[0].font.color.rgb = WHITE
        t3 = s.shapes.add_textbox(Inches(0.85), Inches(3.75), Inches(10), Inches(0.9))
        t3.text_frame.text = "AI-driven release readiness · Jira + GitHub + Excel test plan attachment in one evidence report"
        t3.text_frame.paragraphs[0].font.size = Pt(16)
        t3.text_frame.paragraphs[0].font.name = FONT
        t3.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xBF, 0xDB, 0xFE)
        # KPI strip on title
        metrics = [("3", "Systems unified"), ("8", "Coverage metrics"), ("2–5", "Minutes per run"), ("1", "HTML verdict")]
        cw = Inches(2.85)
        for i, (val, lbl) in enumerate(metrics):
            left = Inches(0.85) + cw * i + Inches(0.12) * i
            self._kpi_card(s, left, Inches(4.85), cw, Inches(1.15), val, lbl, None, NAVY_LIGHT)
        foot = s.shapes.add_textbox(Inches(0.85), Inches(6.72), Inches(11), Inches(0.4))
        foot.text_frame.text = (
            f"Pegasus QA Agents Lab · May 2026 · github.com/mgunjal11/pegasus-qa-agents-lab · "
            f"Developed by {REPORT_DEVELOPER}"
        )
        foot.text_frame.paragraphs[0].font.size = Pt(11)
        foot.text_frame.paragraphs[0].font.name = FONT
        foot.text_frame.paragraphs[0].font.color.rgb = DARK

    def agenda_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._accent_bar(s)
        tb = s.shapes.add_textbox(Inches(0.55), Inches(0.5), Inches(4), Inches(0.9))
        tb.text_frame.text = "Agenda"
        tb.text_frame.paragraphs[0].font.size = Pt(44)
        tb.text_frame.paragraphs[0].font.bold = True
        tb.text_frame.paragraphs[0].font.color.rgb = CORAL
        tb.text_frame.paragraphs[0].font.name = FONT
        items = [
            ("01", "Executive summary", "Value at a glance"),
            ("02", "The challenge", "Fragmented release signals"),
            ("03", "The solution", "Cursor subagent + workflow"),
            ("04", "HTML report deep-dive", "8 sections · info icons · traceability"),
            ("05", "Enablement", "Setup · scripts · permissions"),
            ("06", "Proven outcomes", "MSC case studies"),
        ]
        for i, (num, title, sub) in enumerate(items):
            top = Inches(1.35) + Inches(0.92) * i
            card = self._rect(s, Inches(0.55), top, Inches(6.2), Inches(0.78), LIGHT_GRAY if i % 2 else SOFT_BLUE, radius=True)
            card.line.fill.background()
            nb = s.shapes.add_textbox(Inches(0.7), top + Inches(0.12), Inches(0.55), Inches(0.5))
            nb.text_frame.text = num
            nb.text_frame.paragraphs[0].font.size = Pt(22)
            nb.text_frame.paragraphs[0].font.bold = True
            nb.text_frame.paragraphs[0].font.color.rgb = CORAL
            nb.text_frame.paragraphs[0].font.name = FONT
            tt = s.shapes.add_textbox(Inches(1.35), top + Inches(0.1), Inches(4.5), Inches(0.35))
            tt.text_frame.text = title
            tt.text_frame.paragraphs[0].font.size = Pt(16)
            tt.text_frame.paragraphs[0].font.bold = True
            tt.text_frame.paragraphs[0].font.color.rgb = NAVY
            tt.text_frame.paragraphs[0].font.name = FONT
            st = s.shapes.add_textbox(Inches(1.35), top + Inches(0.42), Inches(4.8), Inches(0.3))
            st.text_frame.text = sub
            st.text_frame.paragraphs[0].font.size = Pt(11)
            st.text_frame.paragraphs[0].font.color.rgb = MUTED
            st.text_frame.paragraphs[0].font.name = FONT
        # right visual — mini architecture
        panel = self._rect(s, Inches(7.1), Inches(1.2), Inches(5.7), Inches(5.5), NAVY, radius=True)
        panel.line.fill.background()
        cap = s.shapes.add_textbox(Inches(7.35), Inches(1.4), Inches(5.2), Inches(0.45))
        cap.text_frame.text = "What you get in one run"
        cap.text_frame.paragraphs[0].font.size = Pt(14)
        cap.text_frame.paragraphs[0].font.bold = True
        cap.text_frame.paragraphs[0].font.color.rgb = GOLD
        cap.text_frame.paragraphs[0].font.name = FONT
        stack = ["Jira story + AC", "Linked PR + CI", "Excel test plan (Jira attachment)", "HTML readiness report"]
        for j, lbl in enumerate(stack):
            y = Inches(2.0) + Inches(0.95) * j
            self._rect(s, Inches(7.5), y, Inches(4.9), Inches(0.7), NAVY_LIGHT, lbl, 12, True, WHITE, True)
            if j < 3:
                arr = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(9.6), y + Inches(0.72), Inches(0.35), Inches(0.22))
                arr.fill.solid()
                arr.fill.fore_color.rgb = GOLD
                arr.line.fill.background()

    def executive_summary(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "Executive summary", "One automated readiness view before every MSC release sign-off")
        cards = [
            ("Problem", "Jira, GitHub, and attached Excel test plans live in silos — release reviews lack a single evidence trail.", CORAL, WHITE),
            ("Solution", "Cursor subagent correlates AC → code → dev tests → QA plan → verdict in minutes.", NAVY, WHITE),
            ("Outcome", "Leadership opens a timestamped HTML report with 8 quantified metrics and clear QA handoff.", TEAL, WHITE),
        ]
        for i, (h, b, fill, tc) in enumerate(cards):
            left = Inches(0.55) + Inches(4.15) * i
            self._rect(s, left, Inches(1.35), Inches(3.95), Inches(0.5), fill, h, 14, True, tc, True)
            box = s.shapes.add_textbox(left + Inches(0.12), Inches(1.95), Inches(3.7), Inches(1.5))
            box.text_frame.text = b
            box.text_frame.paragraphs[0].font.size = Pt(12)
            box.text_frame.paragraphs[0].font.name = FONT
            box.text_frame.paragraphs[0].font.color.rgb = BODY
            box.text_frame.word_wrap = True
        # bottom impact row
        impacts = [
            ("~35–40%", "Faster triage vs manual traceability", SOFT_CORAL, CORAL),
            ("100%", "AC-to-evidence mapping per run", SOFT_BLUE, NAVY),
            ("Pass / Gaps / Fail", "Explicit release verdict", SOFT_GOLD, GOLD_DARK),
            ("Audit-ready", "Shareable HTML artifact", GREEN_BG, GREEN),
        ]
        for i, (val, lbl, bg, vc) in enumerate(impacts):
            left = Inches(0.55) + Inches(3.12) * i
            self._kpi_card(s, left, Inches(3.85), Inches(2.95), Inches(1.55), val, lbl, "Per validator run", bg, vc)
        quote = self._rect(s, Inches(0.55), Inches(5.65), Inches(12.2), Inches(0.85), LIGHT_GRAY, radius=True)
        quote.line.fill.background()
        qt = s.shapes.add_textbox(Inches(0.75), Inches(5.78), Inches(11.8), Inches(0.6))
        qt.text_frame.text = (
            '"We no longer ask five people whether the PR, unit tests, and Jira test plan align — '
            'the validator answers that in one report." — MSC QA lead workflow'
        )
        qt.text_frame.paragraphs[0].font.size = Pt(12)
        qt.text_frame.paragraphs[0].font.italic = True
        qt.text_frame.paragraphs[0].font.color.rgb = NAVY
        qt.text_frame.paragraphs[0].font.name = FONT

    def section_slide(self, num: str, title: str, tagline: str):
        s = self.blank()
        bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
        bg.fill.solid()
        bg.fill.fore_color.rgb = NAVY
        bg.line.fill.background()
        c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(9.5), Inches(1.2), Inches(4.5), Inches(4.5))
        c.fill.solid()
        c.fill.fore_color.rgb = NAVY_LIGHT
        c.fill.transparency = 0.25
        c.line.fill.background()
        num_b = s.shapes.add_textbox(Inches(0.85), Inches(2.0), Inches(2), Inches(1.2))
        num_b.text_frame.text = num
        num_b.text_frame.paragraphs[0].font.size = Pt(72)
        num_b.text_frame.paragraphs[0].font.bold = True
        num_b.text_frame.paragraphs[0].font.color.rgb = GOLD
        num_b.text_frame.paragraphs[0].font.name = FONT
        tit = s.shapes.add_textbox(Inches(0.85), Inches(3.2), Inches(10), Inches(1.2))
        tit.text_frame.text = title
        tit.text_frame.paragraphs[0].font.size = Pt(36)
        tit.text_frame.paragraphs[0].font.bold = True
        tit.text_frame.paragraphs[0].font.color.rgb = WHITE
        tit.text_frame.paragraphs[0].font.name = FONT
        tg = s.shapes.add_textbox(Inches(0.85), Inches(4.35), Inches(9), Inches(0.6))
        tg.text_frame.text = tagline
        tg.text_frame.paragraphs[0].font.size = Pt(16)
        tg.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xBF, 0xDB, 0xFE)
        tg.text_frame.paragraphs[0].font.name = FONT
        self.footer(s)

    def challenge_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "The challenge — three silos, zero single view", "Manual traceability before release is slow, inconsistent, and error-prone")
        silos = [
            ("J", "Jira", "Acceptance criteria,\nstory status, attachments", SOFT_BLUE, NAVY),
            ("GH", "GitHub", "PR diffs, checks,\nunit/integration tests", SOFT_GOLD, GOLD_DARK),
            ("XL", "Excel test plan", "Jira attachment ·\nGiven/When/Then · Mascot links", SOFT_CORAL, CORAL),
        ]
        for i, (icon, name, desc, bg, ic) in enumerate(silos):
            left = Inches(0.65) + Inches(4.15) * i
            self._rect(s, left, Inches(1.45), Inches(3.85), Inches(3.2), bg, radius=True)
            self._icon_circle(s, left + Inches(1.45), Inches(1.75), Inches(0.95), icon, ic)
            nm = s.shapes.add_textbox(left, Inches(2.85), Inches(3.85), Inches(0.4))
            nm.text_frame.text = name
            nm.text_frame.paragraphs[0].font.size = Pt(18)
            nm.text_frame.paragraphs[0].font.bold = True
            nm.text_frame.paragraphs[0].font.color.rgb = DARK
            nm.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            nm.text_frame.paragraphs[0].font.name = FONT
            ds = s.shapes.add_textbox(left + Inches(0.2), Inches(3.35), Inches(3.45), Inches(1.0))
            ds.text_frame.text = desc
            ds.text_frame.paragraphs[0].font.size = Pt(11)
            ds.text_frame.paragraphs[0].font.color.rgb = BODY
            ds.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            ds.text_frame.paragraphs[0].font.name = FONT
        # pain callouts
        pains = [
            "Duplicate QA/dev effort",
            "Missed E2E handoffs",
            "Tribal release knowledge",
            "Weak test-plan ↔ AC mapping",
        ]
        for i, p in enumerate(pains):
            left = Inches(0.65) + Inches(3.12) * i
            chip = self._rect(s, left, Inches(5.0), Inches(2.95), Inches(0.55), RED_BG, p, 10, True, RED, True)
            chip.line.color.rgb = RED
        self._rect(s, Inches(0.55), Inches(5.75), Inches(12.2), Inches(0.75), NAVY, radius=True).line.fill.background()
        sol = s.shapes.add_textbox(Inches(0.75), Inches(5.9), Inches(11.8), Inches(0.5))
        sol.text_frame.text = "→  MSC Code Coverage Validator unifies all three into one HTML readiness report with numbered recommended actions"
        sol.text_frame.paragraphs[0].font.size = Pt(13)
        sol.text_frame.paragraphs[0].font.bold = True
        sol.text_frame.paragraphs[0].font.color.rgb = WHITE
        sol.text_frame.paragraphs[0].font.name = FONT

    def idea_generation_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "Idea Generation — Cursor AI subagent", "Completed · Pegasus QA Agents Lab · Gen AI transformation journey")
        cols = [
            ("Fragmented readiness", NAVY, "Problem Statement", [
                "AC in Jira, code in GitHub, test plans in Jira Excel attachments — no single view",
                "Release reviews depend on tribal knowledge",
                "Manual traceability is slow before sign-off",
            ]),
            ("Unified validator", GOLD, "Solution", [
                "/msc-code-coverage-validator {KEY}",
                "One batch: Jira + PR(s) + Excel test plan attachment",
                "Maps AC → code → dev tests → QA scope",
                "HTML report + Pass / Pass with gaps / Fail",
            ]),
            ("Leadership evidence", NAVY, "Benefits", [
                "8 quantified metric cards",
                "Dev vs QA ownership made explicit",
                "Mascot + Given/When/Then test-plan validation",
                "Audit-friendly downloadable artifact",
                f"Developed by {REPORT_DEVELOPER}",
            ]),
        ]
        col_w = Inches(3.95)
        for i, (title, hf, sec, bullets) in enumerate(cols):
            left = Inches(0.55) + (col_w + Inches(0.22)) * i
            self._rect(s, left, Inches(1.35), col_w, Inches(0.48), hf, title, 13, True, WHITE, True)
            body = self._rect(s, left, Inches(1.83), col_w, Inches(4.35), LIGHT_GRAY, radius=True)
            body.line.fill.background()
            tb = s.shapes.add_textbox(left + Inches(0.12), Inches(1.95), col_w - Inches(0.24), Inches(4.0))
            tf = tb.text_frame
            tf.word_wrap = True
            p0 = tf.paragraphs[0]
            p0.text = f"{sec}:"
            p0.font.bold = True
            p0.font.size = Pt(11)
            p0.font.color.rgb = NAVY
            p0.font.name = FONT
            for b in bullets:
                para = tf.add_paragraph()
                para.text = f"• {b}"
                para.font.size = Pt(10)
                para.font.name = FONT
                para.font.color.rgb = BODY
                para.space_after = Pt(4)
            pills = ["Ideation", "Pilot", "Implementation", "Completed"]
            fills = [PILL_GRAY, PILOT_ORANGE, IMPL_GOLD, GREEN]
            pw = (col_w - Inches(0.1)) / 4
            for j, (lab, fill) in enumerate(zip(pills, fills)):
                sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left + Inches(0.05) + pw * j, Inches(5.95), pw - Inches(0.05), Inches(0.22))
                sh.fill.solid()
                sh.fill.fore_color.rgb = fill if lab == "Completed" else PILL_GRAY
                sh.line.fill.background()
                sh.text_frame.text = lab
                sh.text_frame.paragraphs[0].font.size = Pt(7)
                sh.text_frame.paragraphs[0].font.bold = True
                sh.text_frame.paragraphs[0].font.color.rgb = WHITE
                sh.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    def personas_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "Who uses it — four personas", "Same command, role-specific value from one HTML report")
        personas = [
            ("QA Lead", "Pre-release readiness", "In QA / Ready for Release stories", "QA scope %, test plan gaps", SOFT_BLUE, NAVY),
            ("Developer", "Merge confidence", "Dev-owned AC + unit tests", "Code %, dev test evidence", SOFT_GOLD, GOLD_DARK),
            ("Release Mgr", "Go/no-go snapshot", "Verdict + open gaps", "8 cards, recommended actions", SOFT_CORAL, CORAL),
            ("Test Designer", "Plan alignment", "Excel plan vs Jira AC", "Given/When/Then quality, Mascot links", GREEN_BG, GREEN),
        ]
        for i, (role, when, focus, metric, bg, accent) in enumerate(personas):
            left = Inches(0.55) + Inches(3.12) * i
            self._rect(s, left, Inches(1.4), Inches(2.95), Inches(4.8), bg, radius=True)
            self._icon_circle(s, left + Inches(1.0), Inches(1.65), Inches(0.95), role[0], accent)
            for yoff, txt, bold, sz in [(2.75, role, True, 14), (3.15, when, False, 11), (3.55, focus, False, 10), (4.2, metric, True, 10)]:
                bx = s.shapes.add_textbox(left + Inches(0.15), Inches(yoff), Inches(2.65), Inches(0.55))
                bx.text_frame.text = txt
                bx.text_frame.paragraphs[0].font.size = Pt(sz)
                bx.text_frame.paragraphs[0].font.bold = bold
                bx.text_frame.paragraphs[0].font.color.rgb = DARK if bold else BODY
                bx.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                bx.text_frame.paragraphs[0].font.name = FONT
        cmd = self._rect(s, Inches(2.5), Inches(6.35), Inches(8.3), Inches(0.5), DARK, radius=True)
        cmd.line.fill.background()
        ct = s.shapes.add_textbox(Inches(2.65), Inches(6.42), Inches(8), Inches(0.38))
        ct.text_frame.text = "/msc-code-coverage-validator MSC-205625   ·   --from-cache --auto"
        ct.text_frame.paragraphs[0].font.size = Pt(14)
        ct.text_frame.paragraphs[0].font.name = "Consolas"
        ct.text_frame.paragraphs[0].font.color.rgb = GOLD
        ct.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    def workflow_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "Automated workflow", "End-to-end in ~2–5 minutes · single MCP batch + cached GitHub prefetch")
        steps = [
            ("1", "Jira", "Story, AC,\nattachments"),
            ("2", "Test plan", "Excel xlsx (Jira),\nGiven/When/Then, Mascot"),
            ("3", "GitHub", "PR diff,\nchecks, CI"),
            ("4", "Map", "R1…Rn\nscoring"),
            ("5", "Report", "HTML + tooltips\n+ footer credit"),
        ]
        sw = Inches(2.15)
        for i, (num, title, sub) in enumerate(steps):
            left = Inches(0.45) + (sw + Inches(0.28)) * i
            self._rect(s, left, Inches(1.55), sw, Inches(2.35), NAVY if i % 2 == 0 else NAVY_LIGHT, radius=True)
            nb = s.shapes.add_textbox(left + Inches(0.15), Inches(1.7), Inches(0.5), Inches(0.45))
            nb.text_frame.text = num
            nb.text_frame.paragraphs[0].font.size = Pt(22)
            nb.text_frame.paragraphs[0].font.bold = True
            nb.text_frame.paragraphs[0].font.color.rgb = GOLD
            nb.text_frame.paragraphs[0].font.name = FONT
            tt = s.shapes.add_textbox(left, Inches(2.25), sw, Inches(0.4))
            tt.text_frame.text = title
            tt.text_frame.paragraphs[0].font.size = Pt(14)
            tt.text_frame.paragraphs[0].font.bold = True
            tt.text_frame.paragraphs[0].font.color.rgb = WHITE
            tt.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            tt.text_frame.paragraphs[0].font.name = FONT
            sb = s.shapes.add_textbox(left + Inches(0.1), Inches(2.75), sw - Inches(0.2), Inches(0.9))
            sb.text_frame.text = sub
            sb.text_frame.paragraphs[0].font.size = Pt(10)
            sb.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xBF, 0xDB, 0xFE)
            sb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            sb.text_frame.paragraphs[0].font.name = FONT
            if i < len(steps) - 1:
                ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, left + sw + Inches(0.04), Inches(2.45), Inches(0.22), Inches(0.35))
                ar.fill.solid()
                ar.fill.fore_color.rgb = GOLD
                ar.line.fill.background()
        # cache callout
        self._rect(s, Inches(0.55), Inches(4.25), Inches(12.2), Inches(1.15), SOFT_GOLD, radius=True)
        cb = s.shapes.add_textbox(Inches(0.75), Inches(4.4), Inches(11.8), Inches(0.9))
        cb.text_frame.text = (
            "Performance: reports/.cache/ stores Jira, test plan, and GitHub prefetch — "
            "reuse with --from-cache --auto. Final HTML pass runs apply_report_ui_enhancements(): "
            "info-icon tooltips on every section, tooltip layout v5 (Dev tests / CI status columns), "
            f"and footer credit (Developed by {REPORT_DEVELOPER})."
        )
        cb.text_frame.paragraphs[0].font.size = Pt(12)
        cb.text_frame.paragraphs[0].font.color.rgb = BODY
        cb.text_frame.paragraphs[0].font.name = FONT
        verdicts = [("Pass", GREEN_BG, GREEN), ("Pass with gaps", AMBER_BG, AMBER), ("Fail", RED_BG, RED)]
        for i, (v, bg, fc) in enumerate(verdicts):
            left = Inches(0.55) + Inches(4.15) * i
            self._rect(s, left, Inches(5.65), Inches(3.95), Inches(0.7), bg, v, 16, True, fc, True)

    def architecture_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "Solution architecture", "Cursor IDE · Atlassian MCP · GitHub CLI · Python scripts")
        # center hub
        hub = self._rect(s, Inches(5.0), Inches(2.85), Inches(3.3), Inches(1.5), CORAL, "Coverage\nValidator", 14, True, WHITE, True)
        hub.line.fill.background()
        nodes = [
            (Inches(0.7), Inches(2.5), "Jira MCP", "getJiraIssue\nremote links"),
            (Inches(10.2), Inches(2.5), "GitHub", "prefetch PR\nchecks · diff"),
            (Inches(0.7), Inches(5.0), "Test plan", "fetch_jira_\ntestplan.py"),
            (Inches(10.2), Inches(5.0), "HTML report", "reports/\n{KEY}-…-IST.html"),
        ]
        for l, t, title, sub in nodes:
            self._rect(s, l, t, Inches(2.5), Inches(1.35), LIGHT_GRAY, title, 12, True, NAVY, True)
            sb = s.shapes.add_textbox(l + Inches(0.1), t + Inches(0.55), Inches(2.3), Inches(0.7))
            sb.text_frame.text = sub
            sb.text_frame.paragraphs[0].font.size = Pt(9)
            sb.text_frame.paragraphs[0].font.color.rgb = BODY
            sb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            sb.text_frame.paragraphs[0].font.name = FONT
            # connector to hub center approx
            hx, hy = Inches(6.65), Inches(3.55)
            cx = l + Inches(1.25)
            cy = t + Inches(0.68)
            self._arrow(s, cx, cy, hx, hy)
        leg = s.shapes.add_textbox(Inches(0.55), Inches(6.45), Inches(12), Inches(0.45))
        leg.text_frame.text = (
            "Skill: .cursor/skills/msc-code-coverage-validator/  ·  Agent: msc-code-coverage-validator  ·  "
            f"Command: /msc-code-coverage-validator  ·  Developed by {REPORT_DEVELOPER}"
        )
        leg.text_frame.paragraphs[0].font.size = Pt(10)
        leg.text_frame.paragraphs[0].font.color.rgb = MUTED
        leg.text_frame.paragraphs[0].font.name = FONT

    def report_sections_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(
            s,
            "HTML report — 8 sections",
            "reports/{KEY}-{date}-{time}-{TZ}.html  ·  hover i icons for context  ·  browser-ready",
        )
        sections = [
            ("1", "Coverage summary", "8 metric cards + i tooltips"),
            ("2", "Linked PR(s)", "PR · Repo · State · Title · Dev tests · CI"),
            ("3", "Test plan", "Excel attachment · GWT · Mascot"),
            ("4", "Dev vs QA", "Ownership split"),
            ("5", "Traceability", "Row-per-AC matrix"),
            ("6", "Impl. review", "Gaps · strengths"),
            ("7", "Assumptions", "Scope notes"),
            ("8", "Actions", "Numbered to-dos"),
        ]
        for i, (num, title, sub) in enumerate(sections):
            row, col = i // 4, i % 4
            left = Inches(0.55) + Inches(3.12) * col
            top = Inches(1.4) + Inches(1.55) * row
            card = self._rect(s, left, top, Inches(2.95), Inches(1.35), SOFT_BLUE if row == 0 else SOFT_GOLD, radius=True)
            card.line.fill.background()
            n = s.shapes.add_textbox(left + Inches(0.12), top + Inches(0.1), Inches(0.45), Inches(0.4))
            n.text_frame.text = num
            n.text_frame.paragraphs[0].font.size = Pt(20)
            n.text_frame.paragraphs[0].font.bold = True
            n.text_frame.paragraphs[0].font.color.rgb = CORAL
            n.text_frame.paragraphs[0].font.name = FONT
            tt = s.shapes.add_textbox(left + Inches(0.55), top + Inches(0.12), Inches(2.2), Inches(0.4))
            tt.text_frame.text = title
            tt.text_frame.paragraphs[0].font.size = Pt(12)
            tt.text_frame.paragraphs[0].font.bold = True
            tt.text_frame.paragraphs[0].font.color.rgb = NAVY
            tt.text_frame.paragraphs[0].font.name = FONT
            st = s.shapes.add_textbox(left + Inches(0.12), top + Inches(0.75), Inches(2.7), Inches(0.45))
            st.text_frame.text = sub
            st.text_frame.paragraphs[0].font.size = Pt(10)
            st.text_frame.paragraphs[0].font.color.rgb = MUTED
            st.text_frame.paragraphs[0].font.name = FONT
        # mock header bar
        hdr = self._rect(s, Inches(0.55), Inches(4.55), Inches(12.2), Inches(0.55), NAVY, radius=True)
        hdr.line.fill.background()
        ht = s.shapes.add_textbox(Inches(0.75), Inches(4.65), Inches(11.5), Inches(0.38))
        ex = LATEST_EXAMPLE
        ht.text_frame.text = (
            f"{ex['key']}  ·  Verdict: {ex['verdict']}  ·  Generated {ex['generated']}"
        )
        ht.text_frame.paragraphs[0].font.size = Pt(12)
        ht.text_frame.paragraphs[0].font.bold = True
        ht.text_frame.paragraphs[0].font.color.rgb = WHITE
        ht.text_frame.paragraphs[0].font.name = FONT

    def report_ui_slide(self):
        """Report UX — info icons, tooltip layout v5, Linked PR columns, footer."""
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(
            s,
            "Report UX — info icons & tooltips",
            "apply_report_ui_enhancements() runs automatically before every HTML write",
        )
        # Left: where i icons appear
        self._rect(s, Inches(0.55), Inches(1.35), Inches(6.0), Inches(0.42), NAVY, "Where the i icon appears", 12, True, WHITE, True)
        ui_items = [
            "Header verdict (Pass / Pass with gaps / Fail)",
            "All 8 section titles + 3 summary group titles",
            "All 8 Coverage summary metric cards",
            "Linked PR(s) — 6 column headers (PR, Repo, State, Title, Dev tests, CI status)",
            "Test plan + traceability table headers",
            "Dev vs QA cards · Implementation review panels",
        ]
        for j, item in enumerate(ui_items):
            bx = s.shapes.add_textbox(Inches(0.75), Inches(1.9) + Inches(0.48) * j, Inches(5.6), Inches(0.42))
            bx.text_frame.text = f"i  {item}"
            bx.text_frame.paragraphs[0].font.size = Pt(11)
            bx.text_frame.paragraphs[0].font.color.rgb = BODY
            bx.text_frame.paragraphs[0].font.name = FONT
        # Right: tooltip v5 + footer
        self._rect(s, Inches(6.85), Inches(1.35), Inches(5.9), Inches(0.42), CORAL, "Tooltip layout v5", 12, True, WHITE, True)
        tips = [
            "overflow: visible on sections, tables, and headers — no clipped text",
            "Default columns: tooltip opens left from the icon",
            "Last two table columns (Dev tests, CI status): anchor to <th> right edge",
            "Section headings: tooltip aligns right of the icon",
            "Pointer cursor (not ? help cursor) on hover",
        ]
        for j, tip in enumerate(tips):
            bx = s.shapes.add_textbox(Inches(7.05), Inches(1.9) + Inches(0.48) * j, Inches(5.5), Inches(0.42))
            bx.text_frame.text = f"• {tip}"
            bx.text_frame.paragraphs[0].font.size = Pt(10)
            bx.text_frame.paragraphs[0].font.color.rgb = BODY
            bx.text_frame.paragraphs[0].font.name = FONT
        # Linked PR table mock
        self._rect(s, Inches(0.55), Inches(4.85), Inches(12.2), Inches(0.38), NAVY_LIGHT, "§2 Linked PR(s) — six columns", 11, True, WHITE)
        pr_cols = ["PR", "Repo", "State", "Title", "Dev tests", "CI status"]
        cw = Inches(12.2) / 6
        for ci, col in enumerate(pr_cols):
            left = Inches(0.55) + cw * ci
            accent = SOFT_GOLD if col in ("Dev tests", "CI status") else LIGHT_GRAY
            self._rect(s, left, Inches(5.23), cw - Inches(0.04), Inches(0.35), accent, f"{col} i", 9, True, NAVY)
        ex = LATEST_EXAMPLE
        row_txt = f"#161  ·  wbd-msc/pegasus-pick-genie  ·  MERGED  ·  passport fix  ·  TestDominoPassportRouting  ·  Passed"
        self._rect(s, Inches(0.55), Inches(5.58), Inches(12.2), Inches(0.35), WHITE, row_txt, 9, False, BODY)
        # Footer mock
        ft = self._rect(s, Inches(0.55), Inches(6.15), Inches(12.2), Inches(0.45), LIGHT_GRAY, radius=True)
        ft.line.fill.background()
        fb = s.shapes.add_textbox(Inches(0.75), Inches(6.22), Inches(11.8), Inches(0.35))
        fb.text_frame.text = (
            f"Generated by msc-code-coverage-validator · Developed by {REPORT_DEVELOPER}  "
            f"({ex['report_file']})"
        )
        fb.text_frame.paragraphs[0].font.size = Pt(10)
        fb.text_frame.paragraphs[0].font.color.rgb = MUTED
        fb.text_frame.paragraphs[0].font.name = FONT
        fb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    def metrics_dashboard_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "§1 Coverage summary — 8 metric cards", "Color thresholds: Green ≥85%  ·  Amber 70–84.9%  ·  Red <70%  ·  Gray NA")
        ex = LATEST_EXAMPLE
        groups = [
            ("Implementation & tests", [
                ("Dev code", ex["dev_code_pct"], GREEN_BG, GREEN),
                ("Dev tests", ex["dev_tests_pct"], AMBER_BG, AMBER),
                ("Req mapped", "4/4 AC", GREEN_BG, GREEN),
            ]),
            ("QA & release risk", [
                ("Test plan AC", ex["testplan_ac_pct"], AMBER_BG, AMBER),
                ("QA remaining", ex["qa_remaining"], LIGHT_GRAY, DARK),
                ("Open gaps", ex["open_gaps"], AMBER_BG, AMBER),
            ]),
            ("CI pipeline", [
                ("Line cov.", ex["ci_line_pct"], GREEN_BG, GREEN),
                ("Branch cov.", ex["ci_branch_pct"], GREEN_BG, GREEN),
            ]),
        ]
        top = Inches(1.35)
        for gi, (gname, cards) in enumerate(groups):
            left_base = Inches(0.55) + Inches(4.2) * gi
            gh = s.shapes.add_textbox(left_base, top, Inches(3.9), Inches(0.35))
            gh.text_frame.text = gname
            gh.text_frame.paragraphs[0].font.size = Pt(12)
            gh.text_frame.paragraphs[0].font.bold = True
            gh.text_frame.paragraphs[0].font.color.rgb = NAVY
            gh.text_frame.paragraphs[0].font.name = FONT
            for ci, (lbl, val, bg, vc) in enumerate(cards):
                cy = top + Inches(0.45) + Inches(1.05) * ci
                self._kpi_card(s, left_base, cy, Inches(3.75), Inches(0.95), val, lbl, None, bg, vc)
        # legend
        for i, (lbl, bg, fc) in enumerate([("≥85%", GREEN_BG, GREEN), ("70–84%", AMBER_BG, AMBER), ("<70%", RED_BG, RED), ("NA", LIGHT_GRAY, MUTED)]):
            left = Inches(0.55) + Inches(1.55) * i
            self._rect(s, left, Inches(5.85), Inches(1.35), Inches(0.4), bg, lbl, 10, True, fc, True)

    def testplan_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "§3 Test plan validation — Jira Excel attachment", "Parses Jira attachments · Section · Summary · Given/When/Then · Mascot evidence")
        feats = [
            ("Domino Excel test plan (Jira attachment)", "Jira attachment or local testplans/", "fetch_jira_testplan.py"),
            ("Given / When / Then", "Content-based Given/When/Then scoring (not column-name only)", "5/5 full Given/When/Then example"),
            ("Mascot hyperlinks", "Evidence column URLs rendered in report", "Monitor E2E traceability"),
            ("AC mapping", "Test cases → R1…Rn with gap list", "Uncovered AC highlighted"),
        ]
        for i, (title, desc, proof) in enumerate(feats):
            top = Inches(1.4) + Inches(1.15) * i
            self._rect(s, Inches(0.55), top, Inches(0.08), Inches(0.95), CORAL)
            tt = s.shapes.add_textbox(Inches(0.75), top, Inches(5.5), Inches(0.35))
            tt.text_frame.text = title
            tt.text_frame.paragraphs[0].font.size = Pt(14)
            tt.text_frame.paragraphs[0].font.bold = True
            tt.text_frame.paragraphs[0].font.color.rgb = NAVY
            tt.text_frame.paragraphs[0].font.name = FONT
            ds = s.shapes.add_textbox(Inches(0.75), top + Inches(0.38), Inches(5.8), Inches(0.5))
            ds.text_frame.text = desc
            ds.text_frame.paragraphs[0].font.size = Pt(11)
            ds.text_frame.paragraphs[0].font.color.rgb = BODY
            ds.text_frame.paragraphs[0].font.name = FONT
            pr = self._rect(s, Inches(6.8), top + Inches(0.15), Inches(5.95), Inches(0.75), SOFT_BLUE, proof, 11, True, NAVY, True)
            pr.line.fill.background()
        # sample table mock
        self._rect(s, Inches(6.8), Inches(5.0), Inches(5.95), Inches(0.4), NAVY, "Scenario", 10, True, WHITE)
        for j, row in enumerate(
            [
                "TC1–TC5 · Inc as Fulll · 5/5 Given/When/Then",
                "R4 · Edit ID SIT scenario · Gap",
            ]
        ):
            self._rect(s, Inches(6.8), Inches(5.4) + Inches(0.38) * j, Inches(5.95), Inches(0.35), LIGHT_GRAY if j == 0 else RED_BG, row, 9, False, BODY)

    def dev_qa_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "§4–§5 Dev vs QA ownership & traceability", "No ambiguity on what QA must still run in SIT/UAT")
        self._rect(s, Inches(0.55), Inches(1.4), Inches(5.9), Inches(4.9), SOFT_BLUE, radius=True)
        dh = s.shapes.add_textbox(Inches(0.75), Inches(1.55), Inches(5.5), Inches(0.4))
        dh.text_frame.text = "Development proof"
        dh.text_frame.paragraphs[0].font.size = Pt(16)
        dh.text_frame.paragraphs[0].font.bold = True
        dh.text_frame.paragraphs[0].font.color.rgb = NAVY
        dh.text_frame.paragraphs[0].font.name = FONT
        dev_items = [
            "Unit / integration tests in PR",
            "File + test name evidence",
            "Dev-owned AC marked Covered",
            f"SonarQube CI — {LATEST_EXAMPLE['ci_line_pct']} line (PR #161)",
        ]
        for j, it in enumerate(dev_items):
            bx = s.shapes.add_textbox(Inches(0.85), Inches(2.1) + Inches(0.55) * j, Inches(5.3), Inches(0.45))
            bx.text_frame.text = f"✓  {it}"
            bx.text_frame.paragraphs[0].font.size = Pt(12)
            bx.text_frame.paragraphs[0].font.color.rgb = GREEN
            bx.text_frame.paragraphs[0].font.name = FONT
        self._rect(s, Inches(6.85), Inches(1.4), Inches(5.9), Inches(4.9), SOFT_CORAL, radius=True)
        qh = s.shapes.add_textbox(Inches(7.05), Inches(1.55), Inches(5.5), Inches(0.4))
        qh.text_frame.text = "QA handoff"
        qh.text_frame.paragraphs[0].font.size = Pt(16)
        qh.text_frame.paragraphs[0].font.bold = True
        qh.text_frame.paragraphs[0].font.color.rgb = CORAL
        qh.text_frame.paragraphs[0].font.name = FONT
        qa_items = ["Monitor E2E scenarios", "Manual SIT / UAT evidence", "Regression for related bugs", "Mascot-linked validation runs"]
        for j, it in enumerate(qa_items):
            bx = s.shapes.add_textbox(Inches(7.15), Inches(2.1) + Inches(0.55) * j, Inches(5.3), Inches(0.45))
            bx.text_frame.text = f"→  {it}"
            bx.text_frame.paragraphs[0].font.size = Pt(12)
            bx.text_frame.paragraphs[0].font.color.rgb = CORAL
            bx.text_frame.paragraphs[0].font.name = FONT
        mid = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(6.15), Inches(3.5), Inches(1.0), Inches(1.0))
        mid.fill.solid()
        mid.fill.fore_color.rgb = GOLD
        mid.line.fill.background()
        mid.text_frame.text = "AC"
        mid.text_frame.paragraphs[0].font.size = Pt(14)
        mid.text_frame.paragraphs[0].font.bold = True
        mid.text_frame.paragraphs[0].font.color.rgb = NAVY
        mid.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        mid.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

    def _matrix_header(self, slide, left, top, width, text, fill=NAVY):
        self._rect(slide, left, top, width, Inches(0.42), fill, text, 10, True, WHITE)

    def _matrix_cell(
        self,
        slide,
        left,
        top,
        width,
        height,
        lines: list[str],
        fill=WHITE,
        title: str | None = None,
        title_color=NAVY,
        line_colors: list[RGBColor] | None = None,
    ):
        self._rect(slide, left, top, width, height, fill, radius=False)
        box = slide.shapes.add_textbox(left + Inches(0.08), top + Inches(0.06), width - Inches(0.16), height - Inches(0.1))
        tf = box.text_frame
        tf.word_wrap = True
        if title:
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = title_color
            p.font.name = FONT
        for i, line in enumerate(lines):
            para = tf.add_paragraph() if title or i > 0 else tf.paragraphs[0]
            para.text = line
            para.font.size = Pt(9)
            para.font.name = FONT
            para.font.color.rgb = (line_colors[i] if line_colors and i < len(line_colors) else BODY)
            para.space_after = Pt(2)

    def requirement_traceability_slide(self):
        """MSC-205625 example — Jira requirements vs PR code coverage vs Jira-attached Excel test plan."""
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(
            s,
            "Requirement traceability chart — Jira · Code · Test plan",
            f"{LATEST_EXAMPLE['key']} · {LATEST_EXAMPLE['testplan_note']} · {LATEST_EXAMPLE['pr_note']}",
        )
        left = Inches(0.55)
        col_req = Inches(4.35)
        col_code = Inches(4.05)
        col_plan = Inches(3.95)
        top = Inches(1.35)
        self._matrix_header(s, left, top, col_req, "Requirement (Jira story)")
        self._matrix_header(s, left + col_req + Inches(0.08), top, col_code, "Code coverage (linked PR)")
        self._matrix_header(s, left + col_req + col_code + Inches(0.16), top, col_plan, "Test plan (Jira Excel attachment)")
        rows = [
            (
                "R1",
                "Content passport retained in cumulative output manifestation for PFT Clear incremental-as-full",
                ["Implemented", "Dev tests: Covered", "PR #161 · passport_manager.py"],
                [GREEN, GREEN, BODY],
                GREEN_BG,
                ["TC1–TC5 mapped", "Given/When/Then: full", "Mascot evidence linked"],
                [GREEN, GREEN, GREEN],
                GREEN_BG,
            ),
            (
                "R2",
                "When metadata-update becomes full fulfillment, pack passport must be delivered for incremental-as-full",
                ["Implemented", "Dev tests: Partial", "PriorFulfilledManifestRecord model"],
                [GREEN, AMBER, BODY],
                AMBER_BG,
                ["TC1, TC4 mapped", "Given/When/Then: full", "Aligns with PR behavior"],
                [GREEN, GREEN, GREEN],
                SOFT_BLUE,
            ),
            (
                "R3",
                "Pick-genie must not drop passport re-fetch when workflow resolves fulfillmentType full (PFT Clear)",
                ["Implemented", "Dev tests: Covered", "TestDominoPassportRouting"],
                [GREEN, GREEN, BODY],
                GREEN_BG,
                ["TC1–TC5 mapped", "Given/When/Then: full", "Incremental-as-full scenarios"],
                [GREEN, GREEN, GREEN],
                GREEN_BG,
            ),
            (
                "R4",
                "Fix validated in SIT with Edit ID 37ea180e-77cc-413f-95cf-9dfcebf08cd2 and provided Mascot evidence",
                ["Partial", "Dev tests: Missing", "QA Manual — SIT validation"],
                [AMBER, RED, BODY],
                AMBER_BG,
                ["No mapped test case", "Gap: missing Edit ID scenario", "Then steps lack passport assertion"],
                [RED, RED, AMBER],
                RED_BG,
            ),
        ]
        row_h = Inches(1.05)
        for ri, (rid, req_text, code_lines, code_colors, code_bg, plan_lines, plan_colors, plan_bg) in enumerate(rows):
            y = top + Inches(0.48) + row_h * ri
            req_title = f"{rid}"
            req_body = req_text if len(req_text) <= 95 else req_text[:92] + "…"
            self._matrix_cell(s, left, y, col_req, row_h, [req_body], fill=LIGHT_GRAY if ri % 2 else WHITE, title=req_title)
            self._matrix_cell(
                s,
                left + col_req + Inches(0.08),
                y,
                col_code,
                row_h,
                code_lines,
                fill=code_bg,
                line_colors=code_colors,
            )
            self._matrix_cell(
                s,
                left + col_req + col_code + Inches(0.16),
                y,
                col_plan,
                row_h,
                plan_lines,
                fill=plan_bg,
                line_colors=plan_colors,
            )
        note = s.shapes.add_textbox(Inches(0.55), Inches(6.15), Inches(12.2), Inches(0.55))
        note.text_frame.word_wrap = True
        note.text_frame.text = (
            "Left: acceptance criteria extracted from Jira description · Middle: production code + dev unit/integration tests from PR diff · "
            "Right: scenarios parsed from the Excel test plan file attached to the Jira ticket (not a separate tool — the workbook in Jira attachments)."
        )
        note.text_frame.paragraphs[0].font.size = Pt(10)
        note.text_frame.paragraphs[0].font.color.rgb = MUTED
        note.text_frame.paragraphs[0].font.name = FONT

    def setup_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "Enablement — one-time setup (~10 min)", "Clone lab → MCP → gh → permissions → optional .env")
        steps = [
            ("Clone pegasus-qa-agents-lab", "cursor ."),
            ("pip install -r requirements.txt", "Python 3.10+"),
            ("Atlassian MCP auth", "wbdstreaming.atlassian.net"),
            ("gh auth login", "GitHub PR access"),
            ("install_coverage_validator_permissions.py", "Auto-run allowlist"),
            (".env + validator.defaults.json", "Test plan download + repo defaults"),
        ]
        for i, (title, sub) in enumerate(steps):
            row = i // 2
            col = i % 2
            left = Inches(0.55) + Inches(6.2) * col
            top = Inches(1.35) + Inches(1.05) * row
            self._rect(s, left, top, Inches(5.95), Inches(0.88), LIGHT_GRAY if i % 2 else SOFT_GOLD, radius=True)
            check = s.shapes.add_shape(MSO_SHAPE.OVAL, left + Inches(0.15), top + Inches(0.22), Inches(0.45), Inches(0.45))
            check.fill.solid()
            check.fill.fore_color.rgb = GREEN
            check.line.fill.background()
            check.text_frame.text = "✓"
            check.text_frame.paragraphs[0].font.size = Pt(14)
            check.text_frame.paragraphs[0].font.bold = True
            check.text_frame.paragraphs[0].font.color.rgb = WHITE
            check.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            check.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
            tt = s.shapes.add_textbox(left + Inches(0.75), top + Inches(0.12), Inches(5.0), Inches(0.35))
            tt.text_frame.text = title
            tt.text_frame.paragraphs[0].font.size = Pt(12)
            tt.text_frame.paragraphs[0].font.bold = True
            tt.text_frame.paragraphs[0].font.color.rgb = NAVY
            tt.text_frame.paragraphs[0].font.name = FONT
            st = s.shapes.add_textbox(left + Inches(0.75), top + Inches(0.48), Inches(5.0), Inches(0.3))
            st.text_frame.text = sub
            st.text_frame.paragraphs[0].font.size = Pt(10)
            st.text_frame.paragraphs[0].font.color.rgb = MUTED
            st.text_frame.paragraphs[0].font.name = FONT
        scripts = s.shapes.add_textbox(Inches(0.55), Inches(4.55), Inches(12.2), Inches(1.8))
        scripts.text_frame.word_wrap = True
        lines = [
            "Scripts (batched — no manual gh per run):",
            "fetch_jira_testplan.py  ·  prefetch_coverage_inputs.py  ·  generate_coverage_validator_ppt.py",
            "apply_report_ui_enhancements()  ·  Cache: reports/.cache/{KEY}-*.json",
            f"sync_pegasus_qa_agents_lab.py → push to github.com/mgunjal11/pegasus-qa-agents-lab",
        ]
        for j, line in enumerate(lines):
            para = scripts.text_frame.paragraphs[0] if j == 0 else scripts.text_frame.add_paragraph()
            para.text = line
            para.font.size = Pt(11 if j else 12)
            para.font.bold = j == 0
            para.font.color.rgb = NAVY if j == 0 else BODY
            para.font.name = FONT

    def case_studies_slide(self):
        s = self.blank()
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = WHITE
        self.footer(s)
        self._slide_title(s, "Proven MSC outcomes", "Real validator runs — Pegasus MSC project")
        cases = [
            (
                "MSC-205625",
                "Bug · Ready for Release",
                "100%",
                "75%",
                "75%",
                "Pass with gaps",
                "PR #161 · CI Passed · 5/5 GWT · R4 gap",
            ),
            ("MSC-204417", "Story · In QA", "100%", "83%", "12/12 Given/When/Then", "Pass with gaps", "Caption Monitoring · develop"),
            ("MSC-195138", "Story · FF Race", "—", "—", "66.7%", "Pass with gaps", "PRs #22 + #75 · 11/11 Given/When/Then"),
        ]
        headers = ["Ticket", "Type", "Code", "Dev tests", "Plan AC", "Verdict", "Notes"]
        # header row
        for ci, h in enumerate(headers):
            left = Inches(0.55) + Inches(1.75) * ci
            self._rect(s, left, Inches(1.35), Inches(1.65), Inches(0.42), NAVY, h, 9, True, WHITE)
        def _cell_color(ci: int, cell: str):
            if ci <= 1:
                return DARK
            if ci == 5:
                return AMBER
            if cell.endswith("%"):
                return GREEN if cell.startswith("100") else AMBER
            if "Given/When/Then" in cell or "GWT" in cell:
                return GREEN
            return BODY

        for ri, row in enumerate(cases):
            top = Inches(1.85) + Inches(0.52) * ri
            bg = LIGHT_GRAY if ri % 2 else WHITE
            for ci, cell in enumerate(row):
                left = Inches(0.55) + Inches(1.75) * ci
                self._rect(s, left, top, Inches(1.65), Inches(0.48), bg, cell, 8, ci == 0, _cell_color(ci, cell))

    def closing_slide(self):
        s = self.blank()
        bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
        bg.fill.solid()
        bg.fill.fore_color.rgb = NAVY
        bg.line.fill.background()
        c1 = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(-1), Inches(4.5), Inches(4), Inches(4))
        c1.fill.solid()
        c1.fill.fore_color.rgb = NAVY_LIGHT
        c1.fill.transparency = 0.3
        c1.line.fill.background()
        t1 = s.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.3), Inches(0.8))
        t1.text_frame.text = "It's time to"
        t1.text_frame.paragraphs[0].font.size = Pt(36)
        t1.text_frame.paragraphs[0].font.color.rgb = WHITE
        t1.text_frame.paragraphs[0].font.name = FONT
        t1.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        t2 = s.shapes.add_textbox(Inches(1.5), Inches(2.95), Inches(10.3), Inches(1.0))
        t2.text_frame.text = "Outcreate"
        t2.text_frame.paragraphs[0].font.size = Pt(52)
        t2.text_frame.paragraphs[0].font.bold = True
        t2.text_frame.paragraphs[0].font.color.rgb = GOLD
        t2.text_frame.paragraphs[0].font.name = FONT
        t2.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        t3 = s.shapes.add_textbox(Inches(2), Inches(4.2), Inches(9.3), Inches(0.5))
        t3.text_frame.text = f"/msc-code-coverage-validator {{YOUR-MSC-KEY}}  ·  Developed by {REPORT_DEVELOPER}"
        t3.text_frame.paragraphs[0].font.size = Pt(14)
        t3.text_frame.paragraphs[0].font.name = "Consolas"
        t3.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xBF, 0xDB, 0xFE)
        t3.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.55), W, Inches(0.95))
        band.fill.solid()
        band.fill.fore_color.rgb = GOLD
        band.line.fill.background()

    def build_all(self):
        self.title_slide()
        self.agenda_slide()
        self.executive_summary()
        self.section_slide("01", "The challenge", "Why fragmented Jira · GitHub · Excel test plans blocks confident releases")
        self.challenge_slide()
        self.idea_generation_slide()
        self.section_slide("02", "The solution", "Cursor subagent · automated workflow · solution architecture")
        self.personas_slide()
        self.workflow_slide()
        self.architecture_slide()
        self.section_slide("03", "HTML report", "Eight sections · info icons · metrics · traceability")
        self.report_sections_slide()
        self.report_ui_slide()
        self.metrics_dashboard_slide()
        self.requirement_traceability_slide()
        self.testplan_slide()
        self.dev_qa_slide()
        self.section_slide("04", "Enablement", "One-time setup · scripts · cache · permissions")
        self.setup_slide()
        self.section_slide("05", "Outcomes", "MSC case studies with real coverage metrics")
        self.case_studies_slide()
        self.closing_slide()


def build(out: Path) -> None:
    d = Deck()
    d.build_all()
    out.parent.mkdir(parents=True, exist_ok=True)
    d.prs.save(str(out))
    print(out.resolve())


if __name__ == "__main__":
    import sys

    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "MSC-Code-Coverage-Validator-Guide.pptx"
    build(dest)
    reports_copy = ROOT / "reports" / "MSC-Code-Coverage-Validator-Guide.pptx"
    if dest.resolve() != reports_copy.resolve():
        build(reports_copy)
