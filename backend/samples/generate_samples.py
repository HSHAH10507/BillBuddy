"""Generate the fictional demo documents used by BillBuddy.

All names, numbers, and organisations are invented. Planted issues (for the demo):
  1. Venipuncture (36415) billed twice on the bill, once on the EOB      -> possible duplicate, $35
  2. Metabolic panel (80053) is $210 on the bill but $190 on the EOB     -> billed amount mismatch, $20
  3. Hemoglobin A1c dated 09/22 on the bill, 09/23 on the EOB            -> date mismatch
  4. Chest X-ray EOB line: "you owe" $94 but deductible + coinsurance=$84 -> EOB line doesn't add up, $10
  5. Bill amount due $299 vs EOB "you may owe" $254                      -> totals differ by $45 (= 1 + 2)
Everything else (office visit, CBC) matches, even though the descriptions are worded differently.

Run:  python samples/generate_samples.py
Creates: sample_bill.pdf, sample_eob.pdf, sample_bill_scanned.pdf (image-only, exercises OCR),
         sample_bill_photo.png
"""
from __future__ import annotations

import io
import random
from pathlib import Path

import pymupdf
from PIL import Image, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent
INK = colors.HexColor("#1f2a37")
MUTED = colors.HexColor("#6b7280")
ACCENT_BILL = colors.HexColor("#0f5f5c")
ACCENT_EOB = colors.HexColor("#3b3f9e")

BILL_LINES = [
    ("09/22/2026", "99214", "Office visit, est. patient, moderate", 285.00),
    ("09/22/2026", "85025", "CBC w/ auto diff", 145.00),
    ("09/22/2026", "80053", "Comprehensive metabolic panel", 210.00),
    ("09/22/2026", "36415", "Venipuncture, routine blood draw", 35.00),
    ("09/22/2026", "36415", "Venipuncture, routine blood draw", 35.00),
    ("09/22/2026", "83036", "Hemoglobin A1c", 95.00),
    ("09/22/2026", "71046", "XR chest 2 views", 320.00),
]

# date, code, description, billed, discount, allowed, plan paid, deductible, copay, coins, you owe
EOB_LINES = [
    ("09/22/2026", "99214", "Office/outpatient visit, established", 285.00, 120.00, 165.00, 135.00, 0.00, 30.00, 0.00, 30.00),
    ("09/22/2026", "85025", "Blood count; complete, automated", 145.00, 103.00, 42.00, 0.00, 42.00, 0.00, 0.00, 42.00),
    ("09/22/2026", "80053", "Metabolic panel, comprehensive", 190.00, 142.00, 48.00, 0.00, 48.00, 0.00, 0.00, 48.00),
    ("09/22/2026", "36415", "Collection of venous blood", 35.00, 25.00, 10.00, 0.00, 10.00, 0.00, 0.00, 10.00),
    ("09/23/2026", "83036", "Hemoglobin; glycosylated (A1C)", 95.00, 65.00, 30.00, 0.00, 30.00, 0.00, 0.00, 30.00),
    ("09/22/2026", "71046", "Radiologic exam, chest; 2 views", 320.00, 180.00, 140.00, 56.00, 70.00, 0.00, 14.00, 94.00),
]


def m(v: float) -> str:
    return f"${v:,.2f}"


def watermark(c: canvas.Canvas, w: float, h: float):
    c.saveState()
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#b45309"))
    c.drawCentredString(w / 2, 18, "FICTIONAL SAMPLE FOR BILLBUDDY HEALTH DEMO - NOT A REAL DOCUMENT")
    c.restoreState()


def make_bill(path: Path):
    w, h = letter
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setTitle("Riverbend Community Medical Center - Patient Statement (fictional)")

    c.setFillColor(ACCENT_BILL)
    c.rect(0, h - 8, w, 8, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(48, h - 52, "Riverbend Community Medical Center")
    c.setFont("Helvetica", 9.5)
    c.setFillColor(MUTED)
    c.drawString(48, h - 68, "410 Larkspur Avenue, Suite 200, Millbrook, NJ 08999")
    c.drawString(48, h - 81, "Billing questions: (555) 014-2290, Mon-Fri 8am-5pm")

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(w - 48, h - 52, "PATIENT STATEMENT")
    c.setFont("Helvetica", 9.5)
    c.drawRightString(w - 48, h - 68, "Statement Date: 10/06/2026")
    c.drawRightString(w - 48, h - 81, "Due by: 11/05/2026")

    y = h - 118
    c.setFont("Helvetica", 10)
    for line in ("Patient: Jordan Rivera", "Account #: RB-448213", "Insurance: Lanternfield Health Plan",
                 "Claim #: LHP-2026-0318842"):
        c.drawString(48, y, line)
        y -= 15

    # amount due box
    c.setStrokeColor(ACCENT_BILL)
    c.setLineWidth(1.2)
    c.roundRect(w - 220, h - 178, 172, 62, 6, stroke=1, fill=0)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(w - 208, h - 134, "PLEASE PAY")
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(w - 208, h - 162, m(299.00))

    y = h - 220
    c.setFillColor(colors.HexColor("#eef6f5"))
    c.rect(40, y - 6, w - 80, 20, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(48, y, "Date")
    c.drawString(120, y, "Code")
    c.drawString(170, y, "Description")
    c.drawRightString(w - 48, y, "Charges")
    y -= 24
    c.setFont("Helvetica", 10)
    for date, code, desc, amt in BILL_LINES:
        c.drawString(48, y, date)
        c.drawString(120, y, code)
        c.drawString(170, y, desc)
        c.drawRightString(w - 48, y, m(amt))
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.setLineWidth(0.5)
        c.line(40, y - 7, w - 40, y - 7)
        y -= 22

    total = sum(a for *_, a in BILL_LINES)
    y -= 14
    rows = [("Total Charges", total), ("Insurance Payments", -191.00), ("Insurance Adjustments", -635.00),
            ("Patient Payments", 0.00)]
    c.setFont("Helvetica", 10)
    for label, val in rows:
        c.drawString(w - 260, y, label)
        c.drawRightString(w - 48, y, ("-" if val < 0 else "") + m(abs(val)))
        y -= 17
    c.setStrokeColor(INK)
    c.line(w - 260, y + 9, w - 40, y + 9)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(w - 260, y - 6, "Amount Due")
    c.drawRightString(w - 48, y - 6, m(299.00))

    c.setFont("Helvetica", 8.5)
    c.setFillColor(MUTED)
    c.drawString(48, 70, "Your insurance has processed this claim. The balance shown is your responsibility.")
    c.drawString(48, 58, "Pay online at riverbend-example.test/pay or call the number above to set up a payment plan.")
    watermark(c, w, h)
    c.showPage()
    c.save()


def make_eob(path: Path):
    w, h = landscape(letter)
    c = canvas.Canvas(str(path), pagesize=(w, h))
    c.setTitle("Lanternfield Health Plan - Explanation of Benefits (fictional)")

    c.setFillColor(ACCENT_EOB)
    c.rect(0, h - 8, w, 8, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(40, h - 48, "Lanternfield Health Plan")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w - 40, h - 46, "EXPLANATION OF BENEFITS")
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(colors.HexColor("#b91c1c"))
    c.drawRightString(w - 40, h - 61, "THIS IS NOT A BILL")

    c.setFillColor(INK)
    c.setFont("Helvetica", 10)
    left = ["Patient: Jordan Rivera", "Member ID: LHP884120577", "Group: 70412"]
    right = ["Claim #: LHP-2026-0318842", "Provider: Riverbend Community Medical Center", "Processed: 09/30/2026"]
    y = h - 84
    for a, b in zip(left, right):
        c.drawString(40, y, a)
        c.drawString(330, y, b)
        y -= 15

    cols = [  # (label, x, right-aligned)
        ("Date", 40, False), ("Code", 104, False), ("Service", 148, False), ("Billed", 395, True),
        ("Discount", 448, True), ("Allowed", 501, True), ("Plan Paid", 556, True), ("Deductible", 615, True),
        ("Copay", 662, True), ("Coins.", 708, True), ("You Owe", 752, True),
    ]
    y = h - 150
    c.setFillColor(colors.HexColor("#eef0fb"))
    c.rect(32, y - 6, w - 64, 20, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 8.6)
    for label, x, right_al in cols:
        (c.drawRightString if right_al else c.drawString)(x, y, label)
    y -= 22
    c.setFont("Helvetica", 9)
    for row in EOB_LINES:
        date, code, desc, *amts = row
        c.drawString(40, y, date)
        c.drawString(104, y, code)
        c.drawString(148, y, desc)
        for (_, x, _), v in zip(cols[3:], amts):
            c.drawRightString(x, y, m(v))
        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.setLineWidth(0.5)
        c.line(32, y - 7, w - 32, y - 7)
        y -= 20

    totals = [round(sum(r[i] for r in EOB_LINES), 2) for i in range(3, 11)]
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y - 4, "Totals")
    for (_, x, _), v in zip(cols[3:], totals):
        c.drawRightString(x, y - 4, m(v))

    y -= 48
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(40, y, f"Total You May Owe Provider {m(totals[-1])}")
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(40, y - 18, "Plan year deductible: $1,500.00 individual; applied this claim shown above.")
    c.drawString(40, y - 31, "Remark DX17: Allowed amount reflects your plan's in-network contracted rate. "
                             "Provider may not bill you for the discount.")
    c.drawString(40, y - 44, "Questions? Call Member Services at (555) 013-7788. Appeal rights are described on our website.")
    watermark(c, w, h)
    c.showPage()
    c.save()


def make_scans(bill_pdf: Path):
    """Image-only versions of the bill to demo the OCR path."""
    doc = pymupdf.open(bill_pdf)
    pix = doc[0].get_pixmap(dpi=200)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    rnd = random.Random(7)
    img = img.rotate(0.5, expand=True, fillcolor=255).filter(ImageFilter.GaussianBlur(0.6))
    noise = Image.effect_noise(img.size, 18).convert("L")
    img = Image.blend(img, noise, 0.05 + rnd.random() * 0.01)
    img.save(OUT / "sample_bill_photo.png")
    img.convert("RGB").save(OUT / "sample_bill_scanned.pdf", resolution=200)


if __name__ == "__main__":
    make_bill(OUT / "sample_bill.pdf")
    make_eob(OUT / "sample_eob.pdf")
    make_scans(OUT / "sample_bill.pdf")
    print("Wrote sample_bill.pdf, sample_eob.pdf, sample_bill_scanned.pdf, sample_bill_photo.png")
