"""Fair-price check: compare each charge with what Medicare pays for the same service.

Medicare rates are a public, widely used reference point. They are not what a private plan has
to pay (private insurance usually pays more), so a high ratio is a reason to ask questions, not
proof that a charge is wrong.

Rates: 2026 Medicare Physician Fee Schedule, national amounts before geographic adjustment
(total RVU x the 2026 conversion factor of $33.4009), non-facility setting. Lab tests are paid
under a different schedule (the Clinical Laboratory Fee Schedule) and are not included yet.
"""
from __future__ import annotations

from .models import ExtractedDocument, MatchPair, PriceCheck

PRICING_SOURCE = ("2026 Medicare Physician Fee Schedule, national non-facility amounts before geographic "
                  "adjustment (CMS relative value file, via fastrvu.com)")

# code -> 2026 Medicare national payment (non-facility), USD
MEDICARE_2026: dict[str, float] = {
    "99203": 117.57,  # new patient office visit, low complexity
    "99204": 177.36,  # new patient office visit, moderate complexity
    "99212": 59.45,   # established patient office visit, straightforward
    "99213": 95.19,   # established patient office visit, low complexity
    "99214": 135.61,  # established patient office visit, moderate complexity
    "99215": 192.39,  # established patient office visit, high complexity
    "99284": 118.24,  # emergency department visit, moderate complexity (physician)
    "99285": 171.35,  # emergency department visit, high complexity (physician)
    "71046": 33.07,   # chest X-ray, 2 views
    "93000": 15.36,   # electrocardiogram (ECG), complete
}

HIGH_RATIO = 3.0


def build_price_checks(bill: ExtractedDocument, eob: ExtractedDocument, matches: list[MatchPair]) -> list[PriceCheck]:
    bills = {i.id: i for i in bill.line_items}
    eobs = {i.id: i for i in eob.line_items}
    out: list[PriceCheck] = []
    seen: set[tuple[str, float | None]] = set()
    for m in matches:
        b = bills.get(m.bill_item_id) if m.bill_item_id else None
        e = eobs.get(m.eob_item_id) if m.eob_item_id else None
        ref = b or e
        if not ref or not ref.code:
            continue
        code = ref.code.split("-")[0].upper()
        billed = b.billed if b and b.billed is not None else (e.billed if e else None)
        key = (code, billed)
        if key in seen:  # don't list exact duplicate lines twice
            continue
        seen.add(key)
        rate = MEDICARE_2026.get(code)
        allowed = e.allowed if e else None
        if rate and billed:
            ratio = round(billed / rate, 1)
            level = "high" if ratio >= HIGH_RATIO else "typical"
            note = (f"Billed at about {ratio}× what Medicare pays (${rate:,.2f}). "
                    + ("That's well above the Medicare rate, which can be worth asking about, especially if you're paying "
                       "out of pocket." if level == "high" else
                       "Private insurers commonly pay above Medicare rates, so this is within a common range."))
        else:
            ratio, level = None, "unavailable"
            note = ("No Medicare benchmark available for this code yet. Lab tests use a separate Medicare fee schedule."
                    if code.startswith("8") or code == "36415" else "No Medicare benchmark available for this code yet.")
        out.append(PriceCheck(code=code, description=ref.description, billed=billed, allowed=allowed,
                              medicare_rate=rate, ratio=ratio, level=level, note=note))
    return out
