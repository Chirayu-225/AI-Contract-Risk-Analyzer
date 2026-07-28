"""
LexAI PDF Report Generator
Generates a downloadable structured risk report using reportlab.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)

from services.aggregator_service import AggregationResult

# ── Colour palette ────────────────────────────────────────────────────────────
C_DARK   = colors.HexColor("#1e293b")
C_ACCENT = colors.HexColor("#3b82f6")
C_RED    = colors.HexColor("#ef4444")
C_ORANGE = colors.HexColor("#f97316")
C_GREEN  = colors.HexColor("#22c55e")
C_LIGHT  = colors.HexColor("#f1f5f9")
C_BORDER = colors.HexColor("#e2e8f0")
C_WHITE  = colors.white

RISK_COLOURS = {"high": C_RED, "medium": C_ORANGE, "low": C_GREEN,
                "critical": C_RED}


def generate_report(
    result: AggregationResult,
    contract_filename: str,
    found_clauses: list[dict],
    missing_clauses: list[dict],
    contract_type: str,
) -> bytes:
    """Generate PDF report and return as bytes for download."""
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    story  = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "LexAI — Contract Risk Intelligence Report",
        ParagraphStyle("h1", fontSize=20, textColor=C_DARK,
                       fontName="Helvetica-Bold", spaceAfter=4)
    ))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}  |  "
        f"Contract: {contract_filename}  |  Type: {contract_type}",
        ParagraphStyle("meta", fontSize=8, textColor=colors.grey)
    ))
    story.append(HRFlowable(width="100%", thickness=1,
                            color=C_ACCENT, spaceAfter=12))

    # ── Overall risk score ────────────────────────────────────────────────────
    score  = result.overall_score
    s_col  = C_RED if score >= 70 else (C_ORANGE if score >= 40 else C_GREEN)
    s_label = "HIGH RISK" if score >= 70 else ("MEDIUM RISK" if score >= 40 else "LOW RISK")

    score_data = [[
        Paragraph("Overall Risk Score", ParagraphStyle(
            "sl", fontSize=10, textColor=colors.grey)),
        Paragraph(f"{score}/100", ParagraphStyle(
            "sv", fontSize=28, fontName="Helvetica-Bold", textColor=s_col)),
        Paragraph(s_label, ParagraphStyle(
            "sk", fontSize=12, fontName="Helvetica-Bold", textColor=s_col)),
    ]]
    score_table = Table(score_data, colWidths=[5*cm, 4*cm, 8*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT),
        ("ROUNDEDCORNERS", [6]),
        ("LEFTPADDING",  (0, 0), (-1, -1), 14),
        ("TOPPADDING",   (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 12),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        result.risk_summary,
        ParagraphStyle("summary", fontSize=9, textColor=C_DARK,
                       leading=14, spaceAfter=12)
    ))

    # ── Red flags ─────────────────────────────────────────────────────────────
    if result.red_flags:
        story.append(_section_header("🚩 Red Flags"))
        for flag in result.red_flags:
            story.append(Paragraph(
                flag,
                ParagraphStyle("flag", fontSize=9, textColor=C_DARK,
                               leading=14, leftIndent=10, spaceAfter=4)
            ))
        story.append(Spacer(1, 8))

    # ── Per-party dashboard ───────────────────────────────────────────────────
    story.append(_section_header("⚖ Per-Party Risk Dashboard"))
    party_data = [
        ["", result.party_a.name, result.party_b.name],
        ["Risk Score",
         _score_cell(result.party_a.risk_score),
         _score_cell(result.party_b.risk_score)],
        ["High-Risk Clauses",
         str(result.party_a.high_risk_count),
         str(result.party_b.high_risk_count)],
        ["Medium-Risk Clauses",
         str(result.party_a.med_risk_count),
         str(result.party_b.med_risk_count)],
        ["Favorable Clauses",
         str(len(result.party_a.favorable)),
         str(len(result.party_b.favorable))],
    ]
    party_table = Table(party_data, colWidths=[5*cm, 6.5*cm, 6.5*cm])
    party_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), C_DARK),
        ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.4, C_BORDER),
        ("ALIGN",        (1, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(party_table)
    story.append(Spacer(1, 12))

    # ── Found clauses ─────────────────────────────────────────────────────────
    story.append(_section_header("📋 Identified Risk Clauses"))
    if found_clauses:
        for clause in sorted(found_clauses,
                             key=lambda c: {"high": 0, "medium": 1, "low": 2}
                             .get(c.get("risk_level", "low"), 2)):
            story.append(_clause_block(clause, styles))
    else:
        story.append(Paragraph("No risk clauses identified.",
                               styles["Normal"]))
    story.append(Spacer(1, 8))

    # ── Missing clauses ───────────────────────────────────────────────────────
    story.append(_section_header("🚫 Missing Standard Protections"))
    if missing_clauses:
        miss_data = [["Clause", "Severity", "Why It Matters"]]
        for m in missing_clauses:
            sev   = m.get("severity", "medium")
            s_col2 = RISK_COLOURS.get(sev, C_ORANGE)
            miss_data.append([
                m.get("clause", ""),
                Paragraph(sev.upper(),
                          ParagraphStyle("ms", fontSize=8,
                                         textColor=s_col2,
                                         fontName="Helvetica-Bold")),
                Paragraph(m.get("reason", ""),
                          ParagraphStyle("mr", fontSize=8, leading=11)),
            ])
        miss_table = Table(miss_data, colWidths=[4.5*cm, 2.5*cm, 11*cm])
        miss_table.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
            ("GRID",         (0, 0), (-1, -1), 0.4, C_BORDER),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(miss_table)
    else:
        story.append(Paragraph(
            "All standard protective clauses are present.",
            styles["Normal"]
        ))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Paragraph(
        "⚠ This report is generated by LexAI for informational purposes only and does not "
        "constitute legal advice. Consult a qualified lawyer before signing any contract. "
        "Risk classification is grounded in the CUAD legal taxonomy (NeurIPS 2021) and "
        "Indian commercial law context.",
        ParagraphStyle("disc", fontSize=7, textColor=colors.grey,
                       leading=10, spaceAfter=0)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section_header(title: str) -> Paragraph:
    return Paragraph(
        title,
        ParagraphStyle("sec", fontSize=12, fontName="Helvetica-Bold",
                       textColor=C_DARK, spaceBefore=12, spaceAfter=6)
    )


def _score_cell(score: int) -> str:
    label = "HIGH" if score >= 70 else ("MED" if score >= 40 else "LOW")
    return f"{score}/100 ({label})"


def _clause_block(clause: dict, styles) -> KeepTogether:
    risk   = clause.get("risk_level", "medium")
    r_col  = RISK_COLOURS.get(risk, C_ORANGE)
    cat    = clause.get("category", "Unknown")
    plain  = clause.get("plain_language", "")
    rec    = clause.get("recommendation", "")
    excerpt = clause.get("excerpt", "")
    burdened = clause.get("party_burdened", "Unclear")

    items = []
    items.append(Paragraph(
        f'<font color="#{r_col.hexval()[2:]}">[{risk.upper()}]</font>  '
        f'<b>{cat}</b>  —  Burden: {burdened}',
        ParagraphStyle("ch", fontSize=9, fontName="Helvetica-Bold",
                       textColor=C_DARK, spaceBefore=6, spaceAfter=2)
    ))
    if plain:
        items.append(Paragraph(
            f"Plain language: {plain}",
            ParagraphStyle("cp", fontSize=8, textColor=C_DARK,
                           leftIndent=10, spaceAfter=2)
        ))
    if excerpt:
        items.append(Paragraph(
            f'<i>"{excerpt[:180]}..."</i>',
            ParagraphStyle("ce", fontSize=8, textColor=colors.grey,
                           leftIndent=10, spaceAfter=2)
        ))
    if rec:
        items.append(Paragraph(
            f"Recommendation: {rec}",
            ParagraphStyle("cr", fontSize=8, textColor=C_ACCENT,
                           leftIndent=10, spaceAfter=4)
        ))
    return KeepTogether(items)
