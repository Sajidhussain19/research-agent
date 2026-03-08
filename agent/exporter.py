# agent/exporter.py
# Generates .docx and .pptx files from research results

import io
import os
from datetime import datetime


# ── DOCX Export ───────────────────────────────────────────────────────────────

def generate_docx(query: str, facts: dict, report: str) -> bytes:
    """
    Generate a professional Word document from research results.
    Returns bytes that can be sent as a file download.
    """
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # ── Page margins ──
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1.2)
        section.right_margin  = Inches(1.2)

    # ── Title ──
    title = doc.add_heading(query.title(), level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.runs[0].font.color.rgb = RGBColor(0x00, 0x7A, 0xCC)

    # Date subtitle
    p = doc.add_paragraph()
    run = p.add_run(f"Generated: {datetime.now().strftime('%B %d, %Y')}  ·  AI Research Agent")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    doc.add_paragraph()

    # ── Key Companies ──
    companies = facts.get("companies", [])
    if companies:
        doc.add_heading("Key Companies", level=1)
        for c in companies:
            name = doc.add_paragraph()
            nr   = name.add_run(c.get("name", ""))
            nr.bold = True
            nr.font.size = Pt(12)
            nr.font.color.rgb = RGBColor(0x00, 0x7A, 0xCC)

            if c.get("focus"):
                fp = doc.add_paragraph(c["focus"])
                fp.runs[0].font.size = Pt(10)
                fp.runs[0].font.color.rgb = RGBColor(0x55, 0x55, 0x55)

            if c.get("key_fact"):
                kp = doc.add_paragraph()
                kr = kp.add_run(f"→ {c['key_fact']}")
                kr.font.size = Pt(10)
                kr.font.color.rgb = RGBColor(0x00, 0x88, 0x44)

            # Source
            ev = c.get("evidence", {})
            if ev.get("source_url"):
                sp = doc.add_paragraph()
                sr = sp.add_run(f"Source: {ev.get('source_title', ev['source_url'])}")
                sr.font.size = Pt(8)
                sr.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
                sr.italic = True

            doc.add_paragraph()

    # ── Market Facts ──
    market_facts = facts.get("market_facts", [])
    if market_facts:
        doc.add_heading("Market Overview", level=1)
        for f in market_facts:
            text = f.get("fact", f) if isinstance(f, dict) else f
            p    = doc.add_paragraph(style="List Bullet")
            p.add_run(text).font.size = Pt(11)

        doc.add_paragraph()

    # ── Challenges ──
    challenges = facts.get("challenges", [])
    if challenges:
        doc.add_heading("Challenges", level=1)
        for c in challenges:
            text = c.get("challenge", c) if isinstance(c, dict) else c
            p    = doc.add_paragraph(style="List Bullet")
            p.add_run(text).font.size = Pt(11)

        doc.add_paragraph()

    # ── Full Report ──
    if report:
        doc.add_heading("Full Research Report", level=1)
        for line in report.split("\n"):
            line = line.strip()
            if not line:
                doc.add_paragraph()
                continue
            if line.startswith("## "):
                doc.add_heading(line[3:], level=2)
            elif line.startswith("# "):
                doc.add_heading(line[2:], level=1)
            else:
                p = doc.add_paragraph(line)
                p.runs[0].font.size = Pt(11) if p.runs else None

    # ── Footer ──
    doc.add_paragraph()
    footer_p = doc.add_paragraph()
    footer_r = footer_p.add_run(f"AI Research Agent  ·  {datetime.now().strftime('%Y-%m-%d')}  ·  Powered by OpenAI + Tavily")
    footer_r.font.size  = Pt(8)
    footer_r.font.color.rgb = RGBColor(0xBB, 0xBB, 0xBB)
    footer_p.alignment  = WD_ALIGN_PARAGRAPH.CENTER

    # Save to bytes
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# ── PPTX Export ───────────────────────────────────────────────────────────────

def generate_pptx(query: str, facts: dict, report: str) -> bytes:
    """
    Generate a professional PowerPoint presentation from research results.
    Returns bytes that can be sent as a file download.

    Slide structure:
      1. Title slide
      2. Key Companies
      3. Market Overview
      4. Challenges
      5. Conclusion
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    # ── Colors ──
    C_BG      = RGBColor(0x08, 0x0B, 0x0F)   # dark background
    C_ACCENT  = RGBColor(0x00, 0xE5, 0xFF)   # cyan accent
    C_GREEN   = RGBColor(0x00, 0xFF, 0x88)   # green for facts
    C_TEXT    = RGBColor(0xDC, 0xE8, 0xF0)   # light text
    C_MUTED   = RGBColor(0x4A, 0x60, 0x70)   # muted text
    C_SURFACE = RGBColor(0x0E, 0x13, 0x18)   # card background
    C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)

    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]  # completely blank

    def add_bg(slide, color=C_BG):
        """Fill slide background."""
        bg    = slide.background
        fill  = bg.fill
        fill.solid()
        fill.fore_color.rgb = color

    def add_textbox(slide, text, x, y, w, h,
                    font_size=18, bold=False, color=C_TEXT,
                    align=PP_ALIGN.LEFT, italic=False):
        """Add a styled textbox to slide."""
        txBox = slide.shapes.add_textbox(
            Inches(x), Inches(y), Inches(w), Inches(h)
        )
        tf    = txBox.text_frame
        tf.word_wrap = True
        p     = tf.paragraphs[0]
        p.alignment = align
        run   = p.add_run()
        run.text = text
        run.font.size   = Pt(font_size)
        run.font.bold   = bold
        run.font.italic = italic
        run.font.color.rgb = color
        return txBox

    def add_rect(slide, x, y, w, h, color):
        """Add a filled rectangle."""
        from pptx.util import Inches
        shape = slide.shapes.add_shape(
            1,  # MSO_SHAPE_TYPE.RECTANGLE
            Inches(x), Inches(y), Inches(w), Inches(h)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.fill.background()
        return shape

    # ────────────────────────────────────────────────────────
    # SLIDE 1 — Title
    # ────────────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank_layout)
    add_bg(slide)

    # Accent bar top
    add_rect(slide, 0, 0, 13.33, 0.08, C_ACCENT)

    # Tag line
    add_textbox(slide, "AI RESEARCH AGENT",
                0.8, 1.8, 11, 0.4,
                font_size=11, color=C_ACCENT)

    # Title
    add_textbox(slide, query.title(),
                0.8, 2.3, 11, 2,
                font_size=40, bold=True, color=C_WHITE)

    # Date + source
    add_textbox(slide,
                f"Generated {datetime.now().strftime('%B %d, %Y')}  ·  Powered by OpenAI + Tavily",
                0.8, 4.6, 10, 0.4,
                font_size=12, color=C_MUTED)

    # Stats row
    companies  = facts.get("companies",    [])
    mfacts     = facts.get("market_facts", [])
    challenges = facts.get("challenges",   [])

    stats = [
        (str(len(companies)),  "Companies"),
        (str(len(mfacts)),     "Market Facts"),
        (str(len(challenges)), "Challenges"),
    ]
    for i, (num, label) in enumerate(stats):
        x = 0.8 + i * 2.8
        add_rect(slide, x, 5.3, 2.4, 1.2, C_SURFACE)
        add_textbox(slide, num,   x+0.1, 5.4, 2.2, 0.6,
                    font_size=32, bold=True, color=C_ACCENT, align=PP_ALIGN.CENTER)
        add_textbox(slide, label, x+0.1, 6.0, 2.2, 0.3,
                    font_size=11, color=C_MUTED, align=PP_ALIGN.CENTER)

    # Accent bar bottom
    add_rect(slide, 0, 7.42, 13.33, 0.08, C_ACCENT)

    # ────────────────────────────────────────────────────────
    # SLIDE 2 — Key Companies
    # ────────────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank_layout)
    add_bg(slide)
    add_rect(slide, 0, 0, 13.33, 0.08, C_ACCENT)

    add_textbox(slide, "KEY COMPANIES",
                0.5, 0.2, 12, 0.5,
                font_size=13, bold=True, color=C_ACCENT)

    # Company cards — up to 6, 3 per row
    for i, c in enumerate(companies[:6]):
        row = i // 3
        col = i %  3
        x   = 0.5 + col * 4.2
        y   = 0.9 + row * 3.1

        add_rect(slide, x, y, 3.9, 2.8, C_SURFACE)
        add_textbox(slide, c.get("name", ""),
                    x+0.15, y+0.1, 3.6, 0.45,
                    font_size=14, bold=True, color=C_WHITE)
        add_textbox(slide, c.get("focus", ""),
                    x+0.15, y+0.58, 3.6, 0.6,
                    font_size=10, color=C_MUTED)
        add_textbox(slide, c.get("key_fact", ""),
                    x+0.15, y+1.2, 3.6, 1.3,
                    font_size=10, color=C_GREEN)

    add_rect(slide, 0, 7.42, 13.33, 0.08, C_ACCENT)

    # ────────────────────────────────────────────────────────
    # SLIDE 3 — Market Overview
    # ────────────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank_layout)
    add_bg(slide)
    add_rect(slide, 0, 0, 13.33, 0.08, C_ACCENT)

    add_textbox(slide, "MARKET OVERVIEW",
                0.5, 0.2, 12, 0.5,
                font_size=13, bold=True, color=C_ACCENT)

    for i, f in enumerate(mfacts[:6]):
        text = f.get("fact", f) if isinstance(f, dict) else f
        y    = 0.9 + i * 1.0
        add_rect(slide, 0.5, y, 0.06, 0.5, C_ACCENT)
        add_textbox(slide, text,
                    0.8, y, 12, 0.8,
                    font_size=13, color=C_TEXT)

    add_rect(slide, 0, 7.42, 13.33, 0.08, C_ACCENT)

    # ────────────────────────────────────────────────────────
    # SLIDE 4 — Challenges
    # ────────────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank_layout)
    add_bg(slide)
    add_rect(slide, 0, 0, 13.33, 0.08, C_ACCENT)

    add_textbox(slide, "CHALLENGES",
                0.5, 0.2, 12, 0.5,
                font_size=13, bold=True, color=C_ACCENT)

    for i, c in enumerate(challenges[:5]):
        text = c.get("challenge", c) if isinstance(c, dict) else c
        y    = 0.9 + i * 1.1
        add_rect(slide, 0.5, y, 0.06, 0.6, RGBColor(0xFF, 0x4D, 0x6D))
        add_textbox(slide, text,
                    0.8, y, 12, 0.9,
                    font_size=13, color=C_TEXT)

    add_rect(slide, 0, 7.42, 13.33, 0.08, C_ACCENT)

    # ────────────────────────────────────────────────────────
    # SLIDE 5 — Conclusion
    # ────────────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank_layout)
    add_bg(slide)
    add_rect(slide, 0, 0, 13.33, 0.08, C_ACCENT)

    add_textbox(slide, "CONCLUSION",
                0.8, 1.5, 11, 0.5,
                font_size=13, bold=True, color=C_ACCENT)

    add_textbox(slide, query.title(),
                0.8, 2.1, 11, 1.2,
                font_size=32, bold=True, color=C_WHITE)

    # Summary bullets from report
    summary_lines = []
    if report:
        for line in report.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 30:
                summary_lines.append(line)
            if len(summary_lines) >= 3:
                break

    for i, line in enumerate(summary_lines):
        add_textbox(slide, f"→  {line}",
                    0.8, 3.5 + i * 0.8, 11.5, 0.6,
                    font_size=12, color=C_TEXT)

    add_textbox(slide,
                f"AI Research Agent  ·  {datetime.now().strftime('%Y-%m-%d')}",
                0.8, 6.8, 11, 0.4,
                font_size=10, color=C_MUTED, align=PP_ALIGN.CENTER)

    add_rect(slide, 0, 7.42, 13.33, 0.08, C_ACCENT)

    # Save to bytes
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()