"""
pdf_generator.py – PDF Report Generator for ScholarMind
Uses reportlab.platypus to produce a professionally formatted,
academic-style PDF research report with full Unicode support
for Hindi, Marathi, Sanskrit, Tamil, Telugu, and other Indic scripts.
"""

import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── Output directory ────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Color palette ───────────────────────────────────────────────────
PRIMARY = HexColor("#1a1a2e")
ACCENT = HexColor("#6c63ff")
TEXT_COLOR = HexColor("#222222")
HEADING_COLOR = HexColor("#1a1a2e")
SUBHEADING_COLOR = HexColor("#333366")


# ── Font Registration ──────────────────────────────────────────────
FONT_FAMILY = "Helvetica"
FONT_FAMILY_BOLD = "Helvetica-Bold"

def _register_unicode_fonts():
    """
    Register Unicode fonts that support Hindi, Marathi, Sanskrit,
    Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Punjabi, Urdu.

    Windows 10/11 ships with Nirmala.ttc (TrueType Collection) which
    covers ALL Indic scripts. We load it with subfontIndex=0 (Regular)
    and subfontIndex=1 (Bold).
    """
    global FONT_FAMILY, FONT_FAMILY_BOLD

    fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

    # ── Strategy 1: Nirmala.ttc (TrueType Collection) ──
    ttc_path = os.path.join(fonts_dir, "Nirmala.ttc")
    if os.path.exists(ttc_path):
        try:
            pdfmetrics.registerFont(TTFont("NirmalaUI", ttc_path, subfontIndex=0))
            pdfmetrics.registerFont(TTFont("NirmalaUI-Bold", ttc_path, subfontIndex=1))
            FONT_FAMILY = "NirmalaUI"
            FONT_FAMILY_BOLD = "NirmalaUI-Bold"
            print(f"[PDF] Registered Unicode font: Nirmala.ttc (Regular + Bold)")
            return True
        except Exception as e:
            # subfontIndex=1 might not exist, use 0 for both
            try:
                pdfmetrics.registerFont(TTFont("NirmalaUI", ttc_path, subfontIndex=0))
                pdfmetrics.registerFont(TTFont("NirmalaUI-Bold", ttc_path, subfontIndex=0))
                FONT_FAMILY = "NirmalaUI"
                FONT_FAMILY_BOLD = "NirmalaUI-Bold"
                print(f"[PDF] Registered Unicode font: Nirmala.ttc (Regular only)")
                return True
            except Exception as e2:
                print(f"[PDF] Failed to register Nirmala.ttc: {e2}")

    # ── Strategy 2: NirmalaUI.ttf (flat TrueType) ──
    ttf_paths = [
        ("NirmalaUI.ttf", "NirmalaUIB.ttf"),
        ("Nirmala.ttf", "NirmalaB.ttf"),
    ]
    for reg, bold in ttf_paths:
        reg_path = os.path.join(fonts_dir, reg)
        bold_path = os.path.join(fonts_dir, bold)
        if os.path.exists(reg_path):
            try:
                pdfmetrics.registerFont(TTFont("NirmalaUI", reg_path))
                bp = bold_path if os.path.exists(bold_path) else reg_path
                pdfmetrics.registerFont(TTFont("NirmalaUI-Bold", bp))
                FONT_FAMILY = "NirmalaUI"
                FONT_FAMILY_BOLD = "NirmalaUI-Bold"
                print(f"[PDF] Registered Unicode font: {reg}")
                return True
            except Exception as e:
                print(f"[PDF] Failed to register {reg}: {e}")

    # ── Strategy 3: Arial Unicode MS ──
    arial_path = os.path.join(fonts_dir, "ARIALUNI.TTF")
    if os.path.exists(arial_path):
        try:
            pdfmetrics.registerFont(TTFont("ArialUnicode", arial_path))
            pdfmetrics.registerFont(TTFont("ArialUnicode-Bold", arial_path))
            FONT_FAMILY = "ArialUnicode"
            FONT_FAMILY_BOLD = "ArialUnicode-Bold"
            print(f"[PDF] Registered Unicode font: ARIALUNI.TTF")
            return True
        except Exception as e:
            print(f"[PDF] Failed to register ARIALUNI.TTF: {e}")

    # ── Strategy 4: Download Noto Sans Devanagari ──
    local_font = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NotoSansDevanagari-Regular.ttf")
    if os.path.exists(local_font):
        try:
            pdfmetrics.registerFont(TTFont("NotoDevanagari", local_font))
            pdfmetrics.registerFont(TTFont("NotoDevanagari-Bold", local_font))
            FONT_FAMILY = "NotoDevanagari"
            FONT_FAMILY_BOLD = "NotoDevanagari-Bold"
            print(f"[PDF] Registered Unicode font: NotoSansDevanagari (local)")
            return True
        except Exception as e:
            print(f"[PDF] Failed to register local Noto font: {e}")

    print("[PDF] WARNING: No Unicode font found. Non-Latin scripts will NOT render.")
    print("[PDF] Please ensure Nirmala.ttc exists in C:\\Windows\\Fonts\\")
    return False


# Register fonts at module load time
_register_unicode_fonts()


def _build_styles():
    """Create custom paragraph styles for the PDF with Unicode font."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontSize=26,
        leading=34,
        textColor=HEADING_COLOR,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName=FONT_FAMILY_BOLD,
    ))

    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=HexColor("#666666"),
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName=FONT_FAMILY,
    ))

    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading1"],
        fontSize=16,
        leading=22,
        textColor=HEADING_COLOR,
        spaceBefore=20,
        spaceAfter=10,
        fontName=FONT_FAMILY_BOLD,
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        name="SubHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=18,
        textColor=SUBHEADING_COLOR,
        spaceBefore=14,
        spaceAfter=6,
        fontName=FONT_FAMILY_BOLD,
    ))

    styles.add(ParagraphStyle(
        name="BodyText2",
        parent=styles["Normal"],
        fontSize=11,
        leading=18,
        textColor=TEXT_COLOR,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
        fontName=FONT_FAMILY,
    ))

    styles.add(ParagraphStyle(
        name="BulletText",
        parent=styles["Normal"],
        fontSize=11,
        leading=18,
        textColor=TEXT_COLOR,
        leftIndent=24,
        spaceAfter=4,
        fontName=FONT_FAMILY,
        bulletIndent=12,
        bulletFontName=FONT_FAMILY,
        bulletFontSize=11,
    ))

    styles.add(ParagraphStyle(
        name="FooterStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=HexColor("#999999"),
        alignment=TA_CENTER,
        fontName=FONT_FAMILY,
    ))

    return styles


def _safe_xml_text(text: str) -> str:
    """Escape text for safe use in reportlab XML paragraphs."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text


def _process_markdown_bold(text: str) -> str:
    """Convert **bold** markdown to <b> tags."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text


def _parse_report_to_flowables(report_text: str, styles) -> list:
    """
    Parse the report text and convert it into reportlab flowables.
    Recognizes headings, bullet points, and body text.
    """
    flowables = []
    lines = report_text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flowables.append(Spacer(1, 6))
            continue

        # ── Main section heading: ## N. Title  or  N. Title
        heading_match = re.match(r"^#{1,2}\s*(\d+[\.\\)]\s*.+)", stripped)
        if heading_match:
            text = heading_match.group(1).strip()
            text = _safe_xml_text(text)
            text = _process_markdown_bold(text)
            flowables.append(Spacer(1, 10))
            flowables.append(HRFlowable(
                width="100%", thickness=1,
                color=HexColor("#e0e0e0"),
                spaceBefore=4, spaceAfter=8,
            ))
            try:
                flowables.append(Paragraph(text, styles["SectionHeading"]))
            except Exception:
                flowables.append(Paragraph(_safe_xml_text(stripped), styles["SectionHeading"]))
            continue

        # ── Sub-heading: ### Title
        sub_match = re.match(r"^#{3,}\s*(.+)", stripped)
        if sub_match:
            text = sub_match.group(1).strip()
            text = _safe_xml_text(text)
            text = _process_markdown_bold(text)
            try:
                flowables.append(Paragraph(text, styles["SubHeading"]))
            except Exception:
                flowables.append(Paragraph(_safe_xml_text(stripped), styles["SubHeading"]))
            continue

        # ── Standalone bold heading (like **1. Executive Summary**)
        bold_heading = re.match(r"^\*\*(\d+[\.\\)]\s*.+?)\*\*\s*$", stripped)
        if bold_heading:
            text = bold_heading.group(1).strip()
            text = _safe_xml_text(text)
            flowables.append(Spacer(1, 10))
            flowables.append(HRFlowable(
                width="100%", thickness=1,
                color=HexColor("#e0e0e0"),
                spaceBefore=4, spaceAfter=8,
            ))
            try:
                flowables.append(Paragraph(text, styles["SectionHeading"]))
            except Exception:
                flowables.append(Paragraph(_safe_xml_text(stripped), styles["SectionHeading"]))
            continue

        # ── Bullet point: - text  or  * text
        bullet_match = re.match(r"^[\-\*]\s+(.+)", stripped)
        if bullet_match:
            text = bullet_match.group(1).strip()
            text = _safe_xml_text(text)
            text = _process_markdown_bold(text)
            try:
                flowables.append(Paragraph(f"&#8226;  {text}", styles["BulletText"]))
            except Exception:
                flowables.append(Paragraph(f"- {_safe_xml_text(stripped)}", styles["BulletText"]))
            continue

        # ── Numbered list item: 1. text, 2. text, etc.
        numbered_match = re.match(r"^(\d+[\.\\)])\s+(.+)", stripped)
        if numbered_match and not re.match(r"^\d+[\.\\)]\s+[A-Z][\w\s]+$", stripped):
            num = numbered_match.group(1)
            text = numbered_match.group(2).strip()
            text = _safe_xml_text(text)
            text = _process_markdown_bold(text)
            try:
                flowables.append(Paragraph(f"{num} {text}", styles["BulletText"]))
            except Exception:
                flowables.append(Paragraph(_safe_xml_text(stripped), styles["BulletText"]))
            continue

        # ── Regular body text
        text = stripped
        text = _safe_xml_text(text)
        text = _process_markdown_bold(text)

        if text.startswith("#"):
            text = text.lstrip("#").strip()
            try:
                flowables.append(Paragraph(text, styles["SectionHeading"]))
            except Exception:
                flowables.append(Paragraph(_safe_xml_text(stripped), styles["SectionHeading"]))
        else:
            try:
                flowables.append(Paragraph(text, styles["BodyText2"]))
            except Exception:
                flowables.append(Paragraph(_safe_xml_text(stripped), styles["BodyText2"]))

    return flowables


def generate_pdf(topic: str, report_text: str) -> str:
    """
    Generate a professional PDF research report with Unicode support.

    Args:
        topic: The research topic (used as the title).
        report_text: The full research report text.

    Returns:
        The file path to the generated PDF.
    """
    filepath = os.path.join(OUTPUT_DIR, "report.pdf")
    styles = _build_styles()

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=30 * mm,
        bottomMargin=25 * mm,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        title=f"Research Report: {topic}",
        author="ScholarMind",
    )

    flowables = []

    # ── Title page ──────────────────────────────────────────────────
    flowables.append(Spacer(1, 60))

    safe_topic = _safe_xml_text(topic)
    try:
        flowables.append(Paragraph(safe_topic, styles["ReportTitle"]))
    except Exception:
        flowables.append(Paragraph("Research Report", styles["ReportTitle"]))

    flowables.append(Paragraph(
        "Comprehensive Research Report",
        styles["ReportSubtitle"],
    ))
    flowables.append(Paragraph(
        "Generated by ScholarMind",
        styles["ReportSubtitle"],
    ))
    flowables.append(Spacer(1, 20))
    flowables.append(HRFlowable(
        width="60%", thickness=2,
        color=ACCENT,
        spaceBefore=10, spaceAfter=30,
    ))
    flowables.append(PageBreak())

    # ── Report content ──────────────────────────────────────────────
    content_flowables = _parse_report_to_flowables(report_text, styles)
    flowables.extend(content_flowables)

    # ── Footer ──────────────────────────────────────────────────────
    flowables.append(Spacer(1, 30))
    flowables.append(HRFlowable(
        width="40%", thickness=1,
        color=HexColor("#cccccc"),
        spaceBefore=10, spaceAfter=10,
    ))
    flowables.append(Paragraph(
        "Generated by ScholarMind - AI-Powered Research Intelligence",
        styles["FooterStyle"],
    ))

    # ── Build PDF ───────────────────────────────────────────────────
    doc.build(flowables)
    print(f"[PDF] Generated: {filepath} (font: {FONT_FAMILY})")
    return filepath


if __name__ == "__main__":
    # Test with Hindi text to verify Unicode rendering
    sample = """## 1. कार्यकारी सारांश
यह एक परीक्षण रिपोर्ट है जो एक आकर्षक विषय के बारे में है।

## 2. परिचय
- परिचय के बारे में पहला बिंदु
- परिचय के बारे में दूसरा बिंदु

**मुख्य अंतर्दृष्टि**: यह PDF स्वरूपण को प्रदर्शित करता है।
"""
    path = generate_pdf("एज एआई शोध", sample)
    print(f"PDF saved to: {path}")
