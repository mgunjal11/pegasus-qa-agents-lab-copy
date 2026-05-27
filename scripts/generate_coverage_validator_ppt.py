#!/usr/bin/env python3
"""Generate management PPT for msc-code-coverage-validator (uses, report, config)."""

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
    PINK = RGBColor(0x9D, 0x17, 0x4D)
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
        t = s.shapes.add_textbox(Inches(0.7), Inches(1.8), Inches(8.6), Inches(1.2))
        t.text_frame.text = "MSC Code Coverage Validator"
        t.text_frame.paragraphs[0].font.size = Pt(36)
        t.text_frame.paragraphs[0].font.bold = True
        t.text_frame.paragraphs[0].font.color.rgb = WHITE
        sub = s.shapes.add_textbox(Inches(0.7), Inches(3.0), Inches(8.6), Inches(1.4))
        sub.text_frame.text = (
            "Management guide\n"
            "Business need · Uses · HTML report · Configuration"
        )
        sub.text_frame.paragraphs[0].font.size = Pt(20)
        sub.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xBF, 0xDB, 0xFE)
        foot = s.shapes.add_textbox(Inches(0.7), Inches(5.8), Inches(8.6), Inches(0.5))
        foot.text_frame.text = (
            "Pegasus QA Agents Lab · MSC · wbdstreaming.atlassian.net\n"
            "github.com/mgunjal11/pegasus-qa-agents-lab"
        )
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
        left = Inches(0.45)
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
        tb = s.shapes.add_textbox(left, Inches(0.18), Inches(8.5), Inches(0.7))
        tb.text_frame.text = title
        tb.text_frame.paragraphs[0].font.size = Pt(24)
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
            text, size = item if isinstance(item, tuple) else (item, 16)
            if not text:
                p = tf.add_paragraph() if i else tf.paragraphs[0]
                p.text = ""
                continue
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = text
            p.font.size = Pt(size)
            p.font.color.rgb = DARK if not text.startswith("  ") else SLATE
            p.space_after = Pt(6)
            if text.startswith("  "):
                p.level = 1
                p.font.size = Pt(max(size - 2, 12))

    title_slide()

    bar_slide("Why we need it", ORANGE, None, "The problem this solves", [
        "Stories ship with acceptance criteria in Jira, code in GitHub, and test plans in QMetry — no single view of readiness",
        "QA and dev often duplicate effort or miss handoffs (unit tests done, Monitor E2E never scheduled)",
        "Release reviews rely on tribal knowledge: “Is the PR linked?” “Does the test plan cover the bug?”",
        "Manual traceability across Jira + PR diff + Excel test plans is slow and inconsistent before sign-off",
        "Need: one automated, evidence-based report leadership can open in a browser before release",
    ])

    bar_slide("Primary uses", NAVY, None, "Who runs it and when", [
        "QA leads — pre-release readiness check on MSC stories (In QA / Ready for Release)",
        "Developers — confirm unit/integration tests cover dev-owned acceptance criteria before merge",
        "Release managers — snapshot of dev code %, dev test %, QA remaining, and open gaps",
        "Test designers — cross-check attached QMetry / Domino plan vs Jira acceptance criteria",
        "How to invoke in Cursor:",
        "  /msc-code-coverage-validator MSC-205625",
        "  Reuse cache:  /msc-code-coverage-validator MSC-205625 --from-cache --auto",
    ])

    bar_slide("What the agent delivers", BLUE, None, None, [
        "Reads Jira story, linked PR(s) or branch compare, and attached QMetry test plan",
        "Maps each acceptance criterion → production code, dev tests, test plan cases, QA scope",
        "Separates Development proof (unit/integration) from QA handoff (E2E, manual, regression)",
        "Outputs timestamped HTML:  reports/{KEY}-{date}-{time}-{TZ}.html",
        "Verdict: Pass · Pass with gaps · Fail — with numbered recommended actions",
    ])

    bar_slide("Why leadership cares", SLATE, None, "Release confidence in one view", [
        "Traceability — every acceptance criterion tied to code and test evidence",
        "Quantified metrics — 8 summary cards (dev, QA, test plan, CI)",
        "Clear ownership — no ambiguity on what QA must still run in SIT/UAT",
        "Test plan alignment — Domino / QMetry scenarios vs implementation (when attached)",
        "Audit-friendly — downloadable HTML; shareable with engineering and product",
    ])

    bar_slide("How it works", BLUE, None, "Automated workflow (≈2–5 min)", [
        "1. Fetch Jira issue + remote PR links (Atlassian MCP, one batch)",
        "2. Download/parse QMetry test plan from Jira attachment or local testplans/",
        "3. Prefetch GitHub PR diff, checks, CI coverage (single script; cached for reuse)",
        "4. Extract requirements R1, R2, … from acceptance criteria + LADR comments",
        "5. Score code, dev tests, test plan mapping, QA scope per requirement",
        "6. Write HTML report + save manifest under reports/.cache/",
    ])

    bar_slide("HTML report — overview", NAVY, None, "8 numbered sections + header", [
        "Header — Story title, Jira link, status, verdict, generation time (local TZ)",
        "§1 Coverage summary — 8 metric cards in 3 groups",
        "§2 Linked PR(s) — GitHub traceability and CI",
        "§3 Attached test plan validation — QMetry/Domino vs acceptance criteria",
        "§4 Dev vs QA test ownership — handoff lists",
        "§5 Requirements traceability — row-per-AC audit matrix",
        "§6 Implementation review · §7 Assumptions · §8 Recommended actions",
    ])

    bar_slide("§1 Coverage summary explained", BLUE, "1", "8 cards · 3 groups · color thresholds", [
        "Implementation & tests",
        "  • Dev code coverage — % of acceptance criteria with matching production code",
        "  • Dev unit/integration test coverage — dev-owned AC covered by PR tests",
        "  • Requirements mapped — e.g. 4/4 acceptance criteria (R1–R4)",
        "QA & release risk",
        "  • Test plan acceptance criteria coverage — % AC with ≥1 mapped test case",
        "  • QA scope remaining — E2E, manual, regression still required",
        "  • Open gaps — High / Medium from implementation review",
        "CI pipeline",
        "  • CI line coverage · CI branch coverage (NA if no PR / checks unavailable)",
        "Colors: Green ≥85% · Amber 70–84.9% · Red <70% · Gray NA",
    ])

    bar_slide("§2–§3 PR & test plan", RGBColor(0x37, 0x30, 0xA3), "2–3", None, [
        "§2 Linked PR(s)",
        "  • PR URL, author, merged/open, CI status",
        "  • If no PR: develop vs main compare + key commits (e.g. pegasus-ess)",
        "§3 Attached test plan validation",
        "  • Parses Jira attachment (Domino Test Plan.xlsx) or SharePoint reference",
        "  • Section · Summary scenarios, Given/When/Then, Mascot evidence links",
        "  • Maps test cases to R1…Rn; lists gaps (uncovered AC, weak Then steps)",
        "Example: MSC-205625 — 5 scenarios, 75% test plan AC coverage, R4 SIT gap",
    ])

    bar_slide("§4–§5 Ownership & traceability", RGBColor(0x5B, 0x21, 0xB6), "4–5", None, [
        "§4 Dev vs QA ownership",
        "  • Left: Covered by dev tests (file + test name evidence)",
        "  • Right: QA handoff (E2E Monitor, manual SIT, regression for related bugs)",
        "§5 Requirements traceability (core audit table)",
        "  • Per row: Code status · Dev test status · Owner · QA scope · Evidence paths",
        "  • Badges: Implemented/Covered/Partial/Missing, Dev/Shared/QA, Unit/Integration/E2E",
    ])

    bar_slide("§6–§8 Review & actions", GREEN, "6–8", None, [
        "§6 Implementation review — strengths and gaps (High / Medium severity)",
        "§7 Assumptions — inferred repo, branch, LADR scope needing confirmation",
        "§8 Recommended actions — numbered dev and QA to-dos before release",
        "Verdicts:",
        "  Pass — strong dev coverage, minimal QA gaps",
        "  Pass with gaps — code OK; QA handoff or test plan gaps remain",
        "  Fail — missing implementation, zero test plan coverage, or contradictions",
    ])

    bar_slide("Configuration required", ORANGE, None, "One-time per teammate (~10 min)", [
        "Required for all MSC agents:",
        "  • Cursor IDE with Agents · Clone pegasus-qa-agents-lab · Open as workspace",
        "  • Atlassian MCP authenticated for wbdstreaming.atlassian.net",
        "  • Python 3.10+ · pip install -r requirements.txt",
        "Additional for coverage validator:",
        "  • gh CLI authenticated (gh auth login)",
        "  • python scripts/install_coverage_validator_permissions.py",
        "  • Cursor Settings → Agents → Auto-Run → Allowlist",
        "Recommended when Jira has test plan attachments:",
        "  • .env with ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN (from .env.example)",
    ])

    bar_slide("Config: workspace defaults", SLATE, None, ".coverage-validator.defaults.json (gitignored)", [
        "Copy from .cursor/skills/msc-code-coverage-validator/validator.defaults.example.json",
        "Key fields:",
        "  repo — default GitHub org/repo (e.g. wbd-msc/pegasus-pick-genie)",
        "  timezone / timezoneLabel — report filename suffix (IST, EST)",
        "  testPlanPath / testPlanSheet — local Domino Excel when Jira references SharePoint",
        "  mode: auto · writeReport: true · useCache: true · cacheMaxAgeHours: 24",
        "Manifest reuse: reports/.cache/{KEY}-manifest.json stores last report path + PR URLs",
    ])

    bar_slide("Config: permissions & scripts", BLUE, None, "Avoid Allow/Run prompts every run", [
        "install_coverage_validator_permissions.py merges into ~/.cursor/permissions.json:",
        "  MCP: user-atlassian:getJiraIssue, getJiraIssueRemoteIssueLinks, …",
        "  Shell: gh, prefetch_coverage_inputs.py, fetch_jira_testplan.py, mkdir",
        "Supporting scripts (no manual gh per call):",
        "  fetch_jira_testplan.py — download QMetry attachment, parse scenarios",
        "  prefetch_coverage_inputs.py — batch PR view/diff/checks to cache",
        "  fetch_coverage_github.py — branch compare when no PR linked",
        "  verify_jira_credentials.py — test .env against an issue",
    ])

    bar_slide("Sample outcomes", GREEN, None, "Real MSC examples", [
        "MSC-205625 (Bug, Ready for Release)",
        "  • 100% dev code · 75% dev tests · 75% test plan AC · Pass with gaps",
        "  • PR #161 pick-genie passport fix; 5 Domino scenarios; R4 SIT evidence pending",
        "MSC-204417 (Story, In QA)",
        "  • 100% dev code · 83% dev tests · No test plan attachment (NA)",
        "  • develop branch only; Monitor E2E + STATUS_ERROR 9000 → QA handoff",
        "Report path example:",
        "  reports/MSC-205625-05-27-2026-14-56-29-IST.html",
    ])

    bar_slide("Getting started", NAVY, None, "Commands to run today", [
        "git clone https://github.com/mgunjal11/pegasus-qa-agents-lab",
        "cd pegasus-qa-agents-lab && cursor .",
        "pip install -r requirements.txt && pip install python-pptx",
        "python scripts/install_coverage_validator_permissions.py",
        "cp .env.example .env   # optional, for test plan download",
        "cp …/validator.defaults.example.json .coverage-validator.defaults.json",
        "In Cursor:  /msc-code-coverage-validator MSC-205625",
        "Generate this deck:  python scripts/generate_coverage_validator_ppt.py",
    ])

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    print(out.resolve())


if __name__ == "__main__":
    import sys

    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "MSC-Code-Coverage-Validator-Guide.pptx"
    build(dest)
    reports_copy = ROOT / "reports" / "MSC-Code-Coverage-Validator-Guide.pptx"
    if dest.resolve() != reports_copy.resolve():
        build(reports_copy)
