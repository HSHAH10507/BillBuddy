"""Build a downloadable PDF version of an analysis (POST /api/report).

Uses ReportLab's layout engine (platypus), so the PDF contains real, selectable text.
"""
from __future__ import annotations

import io
from datetime import date
from typing import Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .models import AnalysisResult, Finding, LineItem

INK = colors.HexColor("#1c2430")
MUTED = colors.HexColor("#5f6b7a")
LINE = colors.HexColor("#e3ddd0")
PAPER = colors.HexColor("#f6f3ec")
MATCH = colors.HexColor("#0f6b66")
MATCH_SOFT = colors.HexColor("#e2f1ee")
REVIEW = colors.HexColor("#a85a06")
REVIEW_SOFT = colors.HexColor("#fbefdc")
MISSING = colors.HexColor("#b4364b")
EOB = colors.HexColor("#3b3f9e")
BILL = colors.HexColor("#0f5f5c")

STATUS_LABEL = {"match": ("Matched", MATCH), "mismatch": ("Differs", REVIEW),
                "bill_only": ("Bill only", MISSING), "eob_only": ("EOB only", EOB)}
ASK_LABEL = {"provider": "Ask your provider's billing office", "insurer": "Ask your insurer",
             "either": "Ask your provider or insurer"}


def _t(text: Optional[str]) -> str:
    """Escape for ReportLab's mini-markup and swap characters the built-in fonts can't draw."""
    s = (text or "").replace("−", "-").replace("→", "->").replace("…", "...")
    return escape(s)


def _money(v: Optional[float]) -> str:
    return "-" if v is None else f"${v:,.2f}"


def _date(iso: Optional[str]) -> str:
    if not iso:
        return "-"
    d = date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def _styles():
    base = getSampleStyleSheet()
    s = {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20,
                                leading=24, textColor=INK, alignment=0, spaceAfter=2),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9, leading=12, textColor=MUTED),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=INK,
                             spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=13.5, textColor=INK),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK),
        "muted": ParagraphStyle("muted", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=MUTED),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=MUTED),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.3, leading=10.5, textColor=INK),
        "cellr": ParagraphStyle("cellr", fontName="Helvetica", fontSize=8.3, leading=10.5, textColor=INK, alignment=TA_RIGHT),
        "big": ParagraphStyle("big", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=INK),
        "quote": ParagraphStyle("quote", fontName="Helvetica-Oblique", fontSize=9.5, leading=13, textColor=INK),
    }
    return s


def _summary_box(r: AnalysisResult, s) -> Table:
    bill_due = r.bill.totals.patient_responsibility
    eob_owe = r.eob.totals.patient_responsibility
    gap = (bill_due - eob_owe) if bill_due is not None and eob_owe is not None else None
    total = len(r.matches) or 1

    def tile(label, value, color):
        return [Paragraph(label.upper(), s["label"]), Paragraph(f'<font color="{color.hexval()}">{value}</font>', s["big"])]

    cells = [
        tile("Bill says", _money(bill_due), BILL),
        tile("EOB says you may owe", _money(eob_owe), EOB),
        tile("Gap", _money(abs(gap)) if gap is not None else "-", REVIEW if gap and abs(gap) > 0.005 else MATCH),
        tile("Matched cleanly", f"{r.stats.get('matched', 0)} of {total}", INK),
    ]
    t = Table([cells], colWidths=[1.85 * inch] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LINEAFTER", (0, 0), (-2, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _line_table(r: AnalysisResult, s) -> Table:
    bills = {i.id: i for i in r.bill.line_items}
    eobs = {i.id: i for i in r.eob.line_items}
    header = ["Service", "Date", "Code", "Bill charge", "EOB billed", "EOB: you owe", "Status"]
    rows = [[Paragraph(f"<b>{h}</b>", s["cellr"] if 3 <= i <= 5 else s["cell"]) for i, h in enumerate(header)]]
    styles = []
    for idx, m in enumerate(r.matches, start=1):
        b: Optional[LineItem] = bills.get(m.bill_item_id) if m.bill_item_id else None
        e: Optional[LineItem] = eobs.get(m.eob_item_id) if m.eob_item_id else None
        ref = b or e
        label, color = STATUS_LABEL[m.status]
        diffs = set(m.differences)
        date_txt = _date(b.service_date if b else None) if b else _date(e.service_date if e else None)
        if "service_date" in diffs and b and e:
            date_txt = f"{_date(b.service_date)} / {_date(e.service_date)}"
        rows.append([
            Paragraph(_t(ref.description if ref else ""), s["cell"]),
            Paragraph(date_txt, s["cell"]),
            Paragraph(_t(ref.code if ref and ref.code else "-"), s["cell"]),
            Paragraph(_money(b.billed) if b else "-", s["cellr"]),
            Paragraph(_money(e.billed) if e else "-", s["cellr"]),
            Paragraph(_money(e.patient_responsibility) if e else "-", s["cellr"]),
            Paragraph(f'<font color="{color.hexval()}"><b>{label}</b></font>', s["cell"]),
        ])
        if m.status != "match":
            styles.append(("BACKGROUND", (0, idx), (-1, idx), REVIEW_SOFT if m.status == "mismatch" else colors.HexColor("#f9e5e8")))
    t = Table(rows, colWidths=[2.2 * inch, 0.95 * inch, 0.6 * inch, 0.85 * inch, 0.85 * inch, 0.95 * inch, 0.7 * inch],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        *styles,
    ]))
    return t


def _finding_block(f: Finding, n: int, s) -> KeepTogether:
    sev_color = REVIEW if f.severity == "review" else EOB
    sev_label = "Needs review" if f.severity == "review" else "Worth noting"
    stake = f" &nbsp;&middot;&nbsp; {_money(f.amount_at_stake)} in question" if f.amount_at_stake else ""
    parts = [
        Paragraph(f'<font color="{sev_color.hexval()}"><b>{n}. {sev_label.upper()}</b></font>'
                  f'<font color="{MUTED.hexval()}">{stake}</font>', s["label"]),
        Spacer(1, 2),
        Paragraph(_t(f.title), s["h3"]),
        Spacer(1, 3),
        Paragraph(_t(f.detected), s["body"]),
        Spacer(1, 5),
    ]
    doc_label = {"bill": "BILL", "eob": "EOB", "computed": "CALC."}
    ev_rows = [[Paragraph(f"<b>{doc_label.get(ev.document, ev.document.upper())}</b>", s["cell"]), Paragraph(_t(ev.field), s["cell"]),
                Paragraph(_t(ev.value), s["cell"]), Paragraph(_t(ev.location), s["muted"])] for ev in f.evidence]
    if ev_rows:
        ev = Table(ev_rows, colWidths=[0.75 * inch, 1.5 * inch, 1.6 * inch, 3.25 * inch])
        ev.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PAPER), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        parts += [ev, Spacer(1, 5)]
    parts += [
        Paragraph(f"<b>Why it was flagged:</b> {_t(f.why_flagged)}", s["muted"]),
        Spacer(1, 2),
        Paragraph(f"<b>What BillBuddy can't determine:</b> {_t(f.cannot_determine)}", s["muted"]),
        Spacer(1, 5),
    ]
    q = Table([[Paragraph(f"<b>{ASK_LABEL[f.ask].upper()}</b>", s["label"])],
               [Paragraph(f"“{_t(f.suggested_question)}”", s["quote"])]], colWidths=[7.1 * inch])
    q.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), MATCH_SOFT), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    parts += [q, Spacer(1, 14)]
    return KeepTogether(parts)


def build_report_pdf(r: AnalysisResult) -> bytes:
    s = _styles()
    buf = io.BytesIO()
    generated = date.today()

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.7 * inch, 0.45 * inch,
                          "BillBuddy Health helps you prepare questions. It is not medical, legal or financial advice "
                          "and does not confirm billing errors.")
        canvas.drawRightString(letter[0] - 0.7 * inch, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.75 * inch,
                            title="BillBuddy Health report", author="BillBuddy Health")
    story = [
        Paragraph("BillBuddy Health report", s["title"]),
        Paragraph(f"Medical bill vs. Explanation of Benefits &nbsp;&middot;&nbsp; Generated {_date(generated.isoformat())}", s["sub"]),
        Spacer(1, 10),
    ]

    meta = [
        ("Provider", r.bill.provider or r.eob.provider), ("Insurer", r.eob.insurer or r.bill.insurer),
        ("Patient", r.bill.patient or r.eob.patient), ("Claim #", r.eob.claim_id or r.bill.claim_id),
        ("Bill file", r.bill.filename), ("EOB file", r.eob.filename),
    ]
    meta = [(k, v) for k, v in meta if v]
    if meta:
        rows = [[Paragraph(f"<b>{k}</b>", s["muted"]), Paragraph(_t(v), s["cell"])] for k, v in meta]
        half = (len(rows) + 1) // 2
        left, right = rows[:half], rows[half:] + [["", ""]] * (half - len(rows[half:]))
        mt = Table([l + rr for l, rr in zip(left, right)], colWidths=[0.8 * inch, 2.75 * inch, 0.8 * inch, 2.75 * inch])
        mt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        story += [mt, Spacer(1, 12)]

    story += [_summary_box(r, s), Spacer(1, 10), Paragraph(_t(r.summary), s["body"])]

    story += [Paragraph("Line-by-line comparison", s["h2"]), _line_table(r, s)]

    heading = Paragraph(f"What may need review ({len(r.findings)})", s["h2"])
    if r.findings:
        intro = Paragraph("Each item below was found with arithmetic and comparison rules and shows the values "
                          "that triggered it. None of these are confirmed errors.", s["muted"])
        blocks = [_finding_block(f, n, s) for n, f in enumerate(r.findings, start=1)]
        # keep the heading on the same page as the first finding
        story.append(KeepTogether([heading, intro, Spacer(1, 8), blocks[0]]))
        story.extend(blocks[1:])
    else:
        story += [heading, Paragraph("Every charge matched and all totals reconcile. Nothing stood out for review.", s["body"])]

    if r.findings:
        story.append(Paragraph("Questions to ask", s["h2"]))
        for who in ("provider", "insurer", "either"):
            qs = [f for f in r.findings if f.ask == who]
            if not qs:
                continue
            story.append(Paragraph(f"<b>{ASK_LABEL[who]}</b>", s["body"]))
            for f in qs:
                story.append(Paragraph(f"&bull;&nbsp; {_t(f.suggested_question)}", s["body"]))
            story.append(Spacer(1, 6))

    terms = [g for g in r.glossary if g.in_your_documents]
    if terms:
        story.append(Paragraph("Key terms", s["h2"]))
        for g in terms:
            story.append(Paragraph(f"<b>{_t(g.term)}</b>: {_t(g.definition)}", s["body"]))
            story.append(Paragraph(f"In your documents: {_t(g.in_your_documents)}", s["muted"]))
            story.append(Spacer(1, 5))

    story += [Spacer(1, 10), Paragraph(
        "Disclaimer: BillBuddy Health helps you prepare questions. It does not confirm billing errors and is not "
        "medical, legal or financial advice. Some differences have good explanations, such as a prior balance or a "
        "charge from a different visit. Always check with your provider and insurance company before paying or "
        "disputing a bill.", s["muted"])]

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
