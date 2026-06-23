"""
EXPOSED — PDF Report Generator
Generates a dossier-style PDF from profiles.json using reportlab.
Output: exposed_report.pdf
"""

import json
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── color palette ─────────────────────────────────────────────────────────────
BG          = colors.HexColor("#07070f")
SURFACE     = colors.HexColor("#0f0f1a")
BORDER      = colors.HexColor("#1a1a2e")
TEXT        = colors.HexColor("#e8e6f0")
MUTED       = colors.HexColor("#555577")
CY          = colors.HexColor("#00e5ff")
PU          = colors.HexColor("#9b5cff")
RD          = colors.HexColor("#ff2d6d")
WHITE       = colors.HexColor("#ffffff")

W, H = A4
MARGIN = 18 * mm


# ── styles ────────────────────────────────────────────────────────────────────
def make_styles():
    return {
        "stamp": ParagraphStyle("stamp",
            fontName="Courier", fontSize=7, textColor=MUTED,
            letterSpacing=3, spaceAfter=2),

        "subject_id": ParagraphStyle("subject_id",
            fontName="Courier-Bold", fontSize=18, textColor=TEXT,
            letterSpacing=1, spaceAfter=8),

        "meta": ParagraphStyle("meta",
            fontName="Courier", fontSize=7, textColor=MUTED,
            letterSpacing=2, spaceBefore=2, spaceAfter=16),

        "sec_tag_cy": ParagraphStyle("sec_tag_cy",
            fontName="Courier-Bold", fontSize=8, textColor=CY,
            letterSpacing=3, spaceAfter=6),

        "sec_tag_pu": ParagraphStyle("sec_tag_pu",
            fontName="Courier-Bold", fontSize=8, textColor=PU,
            letterSpacing=3, spaceAfter=6),

        "sec_tag_rd": ParagraphStyle("sec_tag_rd",
            fontName="Courier-Bold", fontSize=8, textColor=RD,
            letterSpacing=3, spaceAfter=6),

        "sec_tag_muted": ParagraphStyle("sec_tag_muted",
            fontName="Courier-Bold", fontSize=8, textColor=MUTED,
            letterSpacing=3, spaceAfter=6),

        "headline": ParagraphStyle("headline",
            fontName="Helvetica-Bold", fontSize=14, textColor=TEXT,
            leading=20, spaceAfter=10),

        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#aaaacc"),
            leading=16, spaceAfter=6),

        "bullet": ParagraphStyle("bullet",
            fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#aaaacc"),
            leading=16, spaceAfter=5, leftIndent=14, firstLineIndent=-14),

        "bullet_bold": ParagraphStyle("bullet_bold",
            fontName="Helvetica-Bold", fontSize=10, textColor=TEXT,
            leading=16, spaceAfter=5, leftIndent=14, firstLineIndent=-14),

        "missed": ParagraphStyle("missed",
            fontName="Helvetica", fontSize=9, textColor=MUTED,
            leading=15, spaceAfter=4, leftIndent=10),

        "ev_score": ParagraphStyle("ev_score",
            fontName="Courier-Bold", fontSize=20, textColor=CY,
            spaceAfter=2),

        "ev_label": ParagraphStyle("ev_label",
            fontName="Helvetica", fontSize=9, textColor=MUTED,
            spaceAfter=4),

        "ev_point": ParagraphStyle("ev_point",
            fontName="Courier", fontSize=8, textColor=MUTED,
            leading=13, spaceAfter=2, leftIndent=10),

        "verdict": ParagraphStyle("verdict",
            fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#aaaacc"),
            leading=17, spaceAfter=6, leftIndent=12, borderPad=0),

        "final": ParagraphStyle("final",
            fontName="Helvetica-BoldOblique", fontSize=13, textColor=TEXT,
            leading=20, alignment=TA_CENTER, spaceAfter=0, spaceBefore=16),

        "footer": ParagraphStyle("footer",
            fontName="Courier", fontSize=7, textColor=MUTED,
            letterSpacing=1, alignment=TA_CENTER),
    }


# ── background canvas ─────────────────────────────────────────────────────────
def dark_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # subtle top accent line
    canvas.setFillColor(CY)
    canvas.rect(MARGIN, H - 8*mm, W - 2*MARGIN, 1, fill=1, stroke=0)
    # page number
    canvas.setFont("Courier", 7)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(W/2, 8*mm, f"EXPOSED · INTELLIGENCE REPORT · PAGE {doc.page}")
    canvas.restoreState()


# ── section divider ───────────────────────────────────────────────────────────
def divider(color=BORDER):
    return HRFlowable(width="100%", thickness=0.5, color=color, spaceAfter=10, spaceBefore=10)


# ── stat table ────────────────────────────────────────────────────────────────
def stat_table(data: list, styles_map: dict) -> Table:
    """data = [(value, label, color), ...]"""
    header_row = [Paragraph(str(v), ParagraphStyle("sv",
        fontName="Courier-Bold", fontSize=20, textColor=c, leading=24))
        for v, _, c in data]
    label_row  = [Paragraph(l, ParagraphStyle("sl",
        fontName="Courier", fontSize=7, textColor=MUTED, letterSpacing=2))
        for _, l, _ in data]

    t = Table([header_row, label_row], colWidths=[(W - 2*MARGIN) / len(data)] * len(data))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SURFACE),
        ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID",  (0,0), (-1,-1), 0.5, BORDER),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),
    ]))
    return t


# ── bar visual (text-based) ───────────────────────────────────────────────────
def bar_paragraph(label: str, pct: float, color: colors.Color) -> Table:
    BAR_W = W - 2*MARGIN - 30*mm
    filled = int(pct / 100 * 40)
    empty  = 40 - filled
    bar    = "█" * filled + "░" * empty

    label_p = Paragraph(label, ParagraphStyle("bl",
        fontName="Helvetica", fontSize=9, textColor=MUTED))
    hexcolor = color.hexval()[2:]  # strip '0x' prefix
    bar_p   = Paragraph(f'<font color="#{hexcolor}">{bar}</font>  {pct}%',
        ParagraphStyle("bv", fontName="Courier", fontSize=7, textColor=MUTED))

    t = Table([[label_p, bar_p]], colWidths=[50*mm, W - 2*MARGIN - 50*mm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return t


# ── evidence box ──────────────────────────────────────────────────────────────
def evidence_box(score: str, label: str, points: list, score_color, s) -> Table:
    content = [
        Paragraph(score, ParagraphStyle("es", fontName="Courier-Bold", fontSize=18,
            textColor=score_color, leading=22)),
        Paragraph(label, ParagraphStyle("el", fontName="Helvetica", fontSize=8,
            textColor=MUTED, spaceAfter=6)),
    ] + [Paragraph(f"+ {p}", ParagraphStyle("ep", fontName="Courier", fontSize=8,
            textColor=MUTED, leading=13, leftIndent=8)) for p in points]

    t = Table([[content]], colWidths=[(W - 2*MARGIN - 8*mm) / 2])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), SURFACE),
        ("BOX",           (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return t


# ── main generator ────────────────────────────────────────────────────────────
def generate_pdf(profiles: dict, output_path: str = "exposed_report.pdf") -> str:
    s = make_styles()
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=14*mm, bottomMargin=16*mm,
    )

    sp_sig  = profiles.get("spotify", {}).get("signals", {})
    sp_prof = profiles.get("spotify", {}).get("profile", {})
    gp_sig  = profiles.get("chatgpt", {}).get("signals", {})
    gp_prof = profiles.get("chatgpt", {}).get("profile", {})
    contrast= profiles.get("contrast", {})
    sp_c    = sp_sig["constructs"]
    gp_c    = gp_sig["constructs"]

    has_spotify = bool(sp_sig)
    has_chatgpt = bool(gp_sig)
    platform_count = sum([has_spotify, has_chatgpt])
    findings_count = len(sp_prof.get("findings", [])) + len(gp_prof.get("findings", []))
    data_points = (sp_sig.get("summary", {}).get("total_plays", 0) +
                   gp_sig.get("summary", {}).get("total_conversations", 0))
    confidence_stat = f"{contrast.get('divergence_confidence', 73)}%" if platform_count == 2 else "—"

    story = []

    # ── PAGE 1: HEADER ────────────────────────────────────────────────────────
    story += [
        Paragraph("EXPOSED · INTELLIGENCE SYSTEM · CONFIDENTIAL", s["stamp"]),
        Spacer(1, 4),
        Paragraph(f"SUBJECT FILE — USER_{hash(profiles['generated_at']) % 9999:04d}", s["subject_id"]),
        Paragraph(
            f"GENERATED: {profiles['generated_at'][:10].upper()} · "
            f"PLATFORMS: {platform_count} · CLASSIFICATION: PERSONAL",
            s["meta"]),
        divider(CY),
        stat_table([
            (str(platform_count),  "PLATFORMS ANALYZED", CY),
            (str(findings_count),  "FINDINGS",           PU),
            (str(data_points), "DATA POINTS", RD),
            (confidence_stat, "CONFIDENCE", TEXT),
        ], s),
        Spacer(1, 10),
    ]

    # ── PAGE 2: SPOTIFY ───────────────────────────────────────────────────────
    story.append(PageBreak())
    story += [
        Paragraph("SPOTIFY · BEHAVIORAL PROFILE", s["sec_tag_cy"]),
        Paragraph(sp_prof.get("headline", ""), s["headline"]),
        divider(),
        Paragraph("BEHAVIORAL CONSTRUCTS", s["sec_tag_muted"]),
    ]

    story.append(stat_table([
        (f"{sp_c['late_night_frequency']['value']}%",   "LATE-NIGHT FREQUENCY",    CY),
        (f"{sp_c['solitary_listening_index']['value']}%","SOLITARY LISTENING INDEX", CY),
        (f"{sp_c['mood_dependency_rate']['value']}%",   "MOOD DEPENDENCY RATE",    RD),
        (str(sp_c['repeat_obsession_score']['value']),  "REPEAT OBSESSION SCORE",  PU),
    ], s))

    story += [Spacer(1, 10), Paragraph("FINDINGS", s["sec_tag_muted"])]
    for f in sp_prof.get("findings", []):
        story.append(Paragraph(f"— {f}", s["bullet"]))

    story += [Spacer(1, 8), Paragraph("TOP ARTISTS", s["sec_tag_muted"])]
    top_artists = sp_sig.get("distributions", {}).get("top_artists", [])[:5]
    artist_colors = [CY, PU, colors.HexColor("#00b3cc"), MUTED, BORDER]
    max_count = top_artists[0][1] if top_artists else 1
    for i, (artist, count) in enumerate(top_artists):
        pct = round(count / max_count * 100, 1)
        story.append(bar_paragraph(artist, pct, artist_colors[i % len(artist_colors)]))

    story += [Spacer(1, 8), Paragraph("WHAT SPOTIFY MISSED", s["sec_tag_muted"])]
    for m in sp_prof.get("what_spotify_missed", []):
        story.append(Paragraph(f"→  {m}", s["missed"]))

    # ── PAGE 3: CHATGPT ───────────────────────────────────────────────────────
    story.append(PageBreak())
    story += [
        Paragraph("CHATGPT · PSYCHOLOGICAL PROFILE", s["sec_tag_pu"]),
        Paragraph(gp_prof.get("headline", ""), s["headline"]),
        divider(),
        Paragraph("PSYCHOLOGICAL CONSTRUCTS", s["sec_tag_muted"]),
    ]

    story.append(stat_table([
        (str(gp_c['ai_reliance_score']['value']),             "AI RELIANCE SCORE",          PU),
        (str(gp_c['reassurance_seeking_pattern']['value']),   "REASSURANCE INSTANCES",      PU),
        (f"{gp_c['midnight_vulnerability_index']['value']}%", "MIDNIGHT VULNERABILITY",     RD),
        (str(gp_c['decision_paralysis_marker']['value']),     "DECISION PARALYSIS MARKER",  PU),
    ], s))

    story += [Spacer(1, 10), Paragraph("FINDINGS", s["sec_tag_muted"])]
    for f in gp_prof.get("findings", []):
        story.append(Paragraph(f"— {f}", s["bullet"]))

    story += [Spacer(1, 8), Paragraph("TOPIC DISTRIBUTION", s["sec_tag_muted"])]
    td = gp_sig["distributions"].get("topic_distribution", {})
    td_colors = {"career_uncertainty": RD, "relationship_anxiety": PU,
                 "self_assessment": colors.HexColor("#7744cc"),
                 "health_concerns": colors.HexColor("#cc3355"),
                 "validation_seeking": PU, "decision_paralysis": MUTED}
    for topic, pct in list(td.items())[:5]:
        label = topic.replace("_", " ").title()
        story.append(bar_paragraph(label, pct, td_colors.get(topic, MUTED)))

    story += [Spacer(1, 8), Paragraph("WHAT CHATGPT MISSED", s["sec_tag_muted"])]
    for m in gp_prof.get("what_chatgpt_missed", []):
        story.append(Paragraph(f"→  {m}", s["missed"]))

    # ── PAGE 4: EVIDENCE + GAP ────────────────────────────────────────────────
    story.append(PageBreak())
    story += [
        Paragraph("EVIDENCE EXPLORER · ALL CONSTRUCTS SOURCED", s["sec_tag_muted"]),
        divider(),
    ]

    ev_pairs = [
        (f"{sp_c['solitary_listening_index']['value']}%", "Solitary Listening Index",
         sp_c['solitary_listening_index']['evidence'], CY),
        (f"{sp_c['mood_dependency_rate']['value']}%",     "Mood Dependency Rate",
         sp_c['mood_dependency_rate']['evidence'],     CY),
        (f"{gp_c['ai_reliance_score']['value']}/100",     "AI Reliance Score",
         gp_c['ai_reliance_score']['evidence'],        PU),
        (str(gp_c['reassurance_seeking_pattern']['value']),"Reassurance Seeking Pattern",
         gp_c['reassurance_seeking_pattern']['evidence'], PU),
    ]
    for i in range(0, len(ev_pairs), 2):
        row = [evidence_box(*ev_pairs[i], s)]
        if i + 1 < len(ev_pairs):
            row.append(evidence_box(*ev_pairs[i+1], s))
        t = Table([row], colWidths=[(W-2*MARGIN-4*mm)/2]*2, hAlign="LEFT")
        t.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),
                                ("RIGHTPADDING",(0,0),(-1,-1),4),
                                ("TOPPADDING",(0,0),(-1,-1),0),
                                ("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        story.append(t)

    story += [
        Spacer(1, 14),
        divider(RD),
        Paragraph("THE GAP · CROSS-PLATFORM DIVERGENCE ANALYSIS", s["sec_tag_rd"]),
        Paragraph(contrast.get("headline", ""), s["headline"]),
        Spacer(1, 6),
    ]

    gap_table = Table([
        [Paragraph("WHAT SPOTIFY SEES", ParagraphStyle("gs",fontName="Courier-Bold",fontSize=8,textColor=CY,letterSpacing=2)),
         Paragraph("WHAT CHATGPT SEES", ParagraphStyle("gc",fontName="Courier-Bold",fontSize=8,textColor=PU,letterSpacing=2))],
        [Paragraph(contrast.get("spotify_sees",""), s["body"]),
         Paragraph(contrast.get("chatgpt_sees",""), s["body"])],
    ], colWidths=[(W-2*MARGIN-4*mm)/2]*2)
    gap_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), SURFACE),
        ("BOX",           (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID",     (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    story += [gap_table, Spacer(1, 10)]

    divergence_t = Table([[
        Paragraph(contrast.get("the_gap",""), s["body"])
    ]], colWidths=[W - 2*MARGIN])
    divergence_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#1a050d")),
        ("BOX",           (0,0), (-1,-1), 0.8, RD),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 14),
    ]))
    story += [divergence_t, Spacer(1, 12)]

    for line in contrast.get("verdict", "").split("\n"):
        if line.strip():
            story.append(Paragraph(line.strip(), s["verdict"]))

    story += [
        Spacer(1, 16),
        divider(MUTED),
        Paragraph(f'"{contrast.get("final_sentence","")}"', s["final"]),
        Spacer(1, 20),
        Paragraph(
            f"EXPOSED · INTELLIGENCE SYSTEM · GENERATED {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · CONFIDENTIAL",
            s["footer"]
        ),
    ]

    doc.build(story, onFirstPage=dark_background, onLaterPages=dark_background)
    pdf_bytes = buf.getvalue()

    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"✓ PDF report generated → {output_path}")
    return pdf_bytes


# ── streamlit integration helper ──────────────────────────────────────────────
def get_pdf_bytes(profiles: dict) -> bytes:
    """Call from dashboard.py — returns raw PDF bytes for st.download_button."""
    return generate_pdf(profiles)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "profiles.json"
    with open(path) as f:
        profiles = json.load(f)
    generate_pdf(profiles, "exposed_report.pdf")
