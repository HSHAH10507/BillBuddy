"""Step 4: the discrepancy detection engine.

Every check here is plain Python arithmetic or comparison - no AI. Each finding carries the
exact values and source rows that triggered it, what the app *can't* know, and a question
the patient can ask. Findings are "may need review", never "this is an error".
"""
from __future__ import annotations

from typing import Optional

from .models import Evidence, ExtractedDocument, Finding, LineItem, MatchPair, SourceRef

TOL = 0.01
MINUS = "\u2212"


def money(v: Optional[float]) -> str:
    return "not shown" if v is None else f"${v:,.2f}"


def fdate(iso: Optional[str]) -> str:
    if not iso:
        return "an unknown date"
    from datetime import date
    d = date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}, {d.year}"  # e.g. "Mar 14, 2026" (portable; %-d fails on Windows)


def loc(src: Optional[SourceRef]) -> Optional[str]:
    if not src or not src.text:
        return None
    return f"page {src.page}: “{src.text}”"


def _label(item: LineItem) -> str:
    code = f" ({item.code})" if item.code else ""
    return f"{item.description}{code}"


def _neq(a: Optional[float], b: Optional[float]) -> bool:
    return a is not None and b is not None and abs(a - b) > TOL


def _sum(values) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return round(sum(vals), 2) if vals else None


class _Builder:
    def __init__(self):
        self.findings: list[Finding] = []

    def add(self, **kw):
        kw.setdefault("id", f"F{len(self.findings) + 1}")
        self.findings.append(Finding(**kw))


def detect_discrepancies(bill: ExtractedDocument, eob: ExtractedDocument, matches: list[MatchPair]) -> list[Finding]:
    out = _Builder()
    bmap = {i.id: i for i in bill.line_items}
    emap = {i.id: i for i in eob.line_items}
    bt, et = bill.totals, eob.totals

    # --- 1. What you're asked to pay vs what the insurer says you owe -----------------
    if _neq(bt.patient_responsibility, et.patient_responsibility):
        diff = round(bt.patient_responsibility - et.patient_responsibility, 2)
        more_less = "more" if diff > 0 else "less"
        out.add(
            rule="patient_total_mismatch", severity="review", ask="provider",
            title="Amount due on the bill differs from what your EOB says you owe",
            detected=f"The bill asks for {money(bt.patient_responsibility)}, but the EOB lists your responsibility "
                     f"as {money(et.patient_responsibility)} — {money(abs(diff))} {more_less}.",
            evidence=[
                Evidence(document="bill", field="Amount due", value=money(bt.patient_responsibility),
                         location=loc(bt.source.get("patient_responsibility"))),
                Evidence(document="eob", field="Total you may owe", value=money(et.patient_responsibility),
                         location=loc(et.source.get("patient_responsibility"))),
                Evidence(document="computed", field="Difference", value=money(abs(diff))),
            ],
            why_flagged="For the same claim, the provider's balance normally equals the patient responsibility "
                        "on the EOB once the claim is processed. A gap usually traces back to a line item below.",
            cannot_determine="Whether the bill includes a prior balance, services from another claim, or a claim the "
                             "insurer has since reprocessed.",
            suggested_question=f"My EOB for this claim shows I owe {money(et.patient_responsibility)}, but my statement "
                               f"says {money(bt.patient_responsibility)}. Can you explain the {money(abs(diff))} "
                               "difference or send an itemized bill?",
            amount_at_stake=abs(diff),
        )

    # --- 2. Line-level cross checks ---------------------------------------------------
    for m in matches:
        b = bmap.get(m.bill_item_id) if m.bill_item_id else None
        e = emap.get(m.eob_item_id) if m.eob_item_id else None

        if m.status == "bill_only" and b:
            twin = next(
                (o for o in bill.line_items
                 if o.id != b.id and o.code and o.code == b.code and o.service_date == b.service_date),
                None,
            )
            if twin:
                out.add(
                    rule="possible_duplicate", severity="review", ask="provider",
                    title=f"Possible duplicate charge: {b.description}",
                    detected=f"{_label(b)} appears twice on the bill for {fdate(b.service_date)}, "
                             "but the EOB shows it only once.",
                    evidence=[
                        Evidence(document="bill", field="Line item", value=money(twin.billed), location=loc(twin.source)),
                        Evidence(document="bill", field="Repeated line item", value=money(b.billed), location=loc(b.source)),
                        Evidence(document="eob", field="Matching EOB lines", value="1"),
                    ],
                    why_flagged="Same billing code on the same date, listed twice on the bill, with only one "
                                "corresponding line processed by the insurer.",
                    cannot_determine="Whether the service was genuinely performed twice (some services can be) and "
                                     "submitted on a separate claim.",
                    suggested_question=f"I see {b.code} billed twice on {fdate(b.service_date)}. Was this service performed "
                                       "twice? My EOB shows it once. If it's a duplicate, can it be removed?",
                    amount_at_stake=b.billed, related_items=[twin.id, b.id],
                )
            else:
                out.add(
                    rule="bill_only_item", severity="review", ask="provider",
                    title=f"Charge on the bill not found on the EOB: {b.description}",
                    detected=f"{_label(b)} for {money(b.billed)} on {fdate(b.service_date)} has no matching line on the EOB.",
                    evidence=[Evidence(document="bill", field="Line item", value=money(b.billed), location=loc(b.source))],
                    why_flagged="No EOB line had a similar code, date, and description.",
                    cannot_determine="Whether it was billed to insurance on a different claim, is still processing, or "
                                     "was never submitted.",
                    suggested_question=f"Was the {b.description} charge on {fdate(b.service_date)} submitted to my insurance? "
                                       "I don't see it on my EOB.",
                    amount_at_stake=b.billed, related_items=[b.id],
                )

        if m.status == "eob_only" and e:
            out.add(
                rule="eob_only_item", severity="notice", ask="provider",
                title=f"Service on the EOB not listed on the bill: {e.description}",
                detected=f"The EOB lists {_label(e)} on {fdate(e.service_date)}, but the bill has no matching line.",
                evidence=[Evidence(document="eob", field="Line item", value=money(e.billed), location=loc(e.source))],
                why_flagged="No bill line had a similar code, date, and description.",
                cannot_determine="Whether the bill groups this service under another line or omits it.",
                suggested_question=f"My EOB shows {e.description} on {fdate(e.service_date)}. Is it included on my statement?",
                amount_at_stake=e.patient_responsibility, related_items=[e.id],
            )

        if b and e and "billed" in m.differences:
            diff = round(b.billed - e.billed, 2)
            out.add(
                rule="billed_amount_mismatch", severity="review", ask="provider",
                title=f"Different charge for the same service: {b.description}",
                detected=f"The bill charges {money(b.billed)} for {_label(b)}, but the EOB shows the provider "
                         f"billed {money(e.billed)} — a {money(abs(diff))} difference.",
                evidence=[
                    Evidence(document="bill", field="Charge", value=money(b.billed), location=loc(b.source)),
                    Evidence(document="eob", field="Amount billed", value=money(e.billed), location=loc(e.source)),
                ],
                why_flagged=f"These lines were paired because of {', '.join(m.reasons) or 'their similarity'}, "
                            "yet the charge differs. The insurer's numbers are based on what it received.",
                cannot_determine="Whether the bill was updated after the claim was sent, or the EOB reflects a corrected claim.",
                suggested_question=f"My statement shows {money(b.billed)} for {b.code or b.description}, but my insurer "
                                   f"received a claim for {money(e.billed)}. Which is correct?",
                amount_at_stake=abs(diff), related_items=[b.id, e.id],
            )

        if b and e and "service_date" in m.differences:
            out.add(
                rule="date_mismatch", severity="review", ask="either",
                title=f"Service date differs: {b.description}",
                detected=f"The bill dates {_label(b)} {fdate(b.service_date)}; the EOB dates it {fdate(e.service_date)}.",
                evidence=[
                    Evidence(document="bill", field="Service date", value=fdate(b.service_date), location=loc(b.source)),
                    Evidence(document="eob", field="Service date", value=fdate(e.service_date), location=loc(e.source)),
                ],
                why_flagged="Matched on code and description, but dates disagree. Wrong dates can affect which "
                            "deductible period or plan year a charge falls in.",
                cannot_determine="Which date is correct (e.g. a lab drawn one day and processed the next).",
                suggested_question=f"What date was {b.description} performed? My bill says {fdate(b.service_date)} and my EOB "
                                   f"says {fdate(e.service_date)}.",
                related_items=[b.id, e.id],
            )

        if b and e and "code" in m.differences:
            out.add(
                rule="code_mismatch", severity="review", ask="provider",
                title=f"Billing code differs: {b.description}",
                detected=f"The bill uses code {b.code}; the matching EOB line uses {e.code}.",
                evidence=[
                    Evidence(document="bill", field="Code", value=b.code, location=loc(b.source)),
                    Evidence(document="eob", field="Code", value=e.code, location=loc(e.source)),
                ],
                why_flagged="Different codes can mean a different level of service and a different price.",
                cannot_determine="Which code reflects the service actually provided.",
                suggested_question=f"Why does my bill show code {b.code} while my insurer processed {e.code}?",
                related_items=[b.id, e.id],
            )

    # --- 3. Does each EOB line add up? -------------------------------------------------
    for e in eob.line_items:
        share = _sum([e.deductible, e.copay, e.coinsurance, e.not_covered])
        problems: list[str] = []
        evidence: list[Evidence] = []
        if e.billed is not None and e.adjustment is not None and e.allowed is not None and \
                _neq(round(e.billed - e.adjustment, 2), e.allowed):
            problems.append(f"billed {money(e.billed)} − discount {money(e.adjustment)} = "
                            f"{money(e.billed - e.adjustment)}, but allowed is {money(e.allowed)}")
        if e.patient_responsibility is not None and share is not None and _neq(share, e.patient_responsibility):
            problems.append(f"deductible + copay + coinsurance = {money(share)}, but “you owe” is "
                            f"{money(e.patient_responsibility)}")
        if e.allowed is not None and e.plan_paid is not None and e.patient_responsibility is not None and \
                _neq(round(e.plan_paid + e.patient_responsibility, 2), e.allowed):
            problems.append(f"plan paid {money(e.plan_paid)} + you owe {money(e.patient_responsibility)} = "
                            f"{money(e.plan_paid + e.patient_responsibility)}, but allowed is {money(e.allowed)}")
        if problems:
            evidence.append(Evidence(document="eob", field="Line item", value=_label(e), location=loc(e.source)))
            for p in problems:
                evidence.append(Evidence(document="computed", field="Check", value=p))
            out.add(
                rule="eob_line_not_reconciling", severity="review", ask="insurer",
                title=f"EOB line doesn't add up: {e.description}",
                detected="The amounts on this EOB line don't reconcile: " + "; ".join(problems) + ".",
                evidence=evidence,
                why_flagged="On an EOB, allowed amount = what the plan paid + what you owe. When the parts don't "
                            "sum, one of the numbers may have been entered or processed incorrectly.",
                cannot_determine="Whether another column (like an amount not covered) explains the gap, or whether "
                                 "the text was misread from the document.",
                suggested_question=f"On my EOB for {fdate(e.service_date)}, the amounts for {e.code or e.description} don't add "
                                   "up. Can you explain how my share was calculated?",
                amount_at_stake=abs(round((share or 0) - (e.patient_responsibility or 0), 2)) or None,
                related_items=[e.id],
            )

    for b in bill.line_items:
        if None in (b.billed, b.adjustment, b.plan_paid, b.patient_responsibility):
            continue
        expected = round(b.billed - b.adjustment - b.plan_paid, 2)
        if _neq(expected, b.patient_responsibility):
            out.add(
                rule="bill_line_not_reconciling", severity="review", ask="provider",
                title=f"Bill line doesn't add up: {b.description}",
                detected=f"Charge {money(b.billed)} \u2212 adjustment {money(b.adjustment)} \u2212 insurance payment "
                         f"{money(b.plan_paid)} = {money(expected)}, but your portion is listed as {money(b.patient_responsibility)}.",
                evidence=[
                    Evidence(document="bill", field="Line item", value=_label(b), location=loc(b.source)),
                    Evidence(document="computed", field="Charge \u2212 adjustment \u2212 insurance", value=money(expected)),
                ],
                why_flagged="Your portion of a line normally equals the charge minus adjustments and insurance payments.",
                cannot_determine="Whether another credit or fee applies to this line.",
                suggested_question=f"How was my portion of {money(b.patient_responsibility)} for {b.description} calculated?",
                amount_at_stake=abs(round(expected - b.patient_responsibility, 2)), related_items=[b.id],
            )

    # --- 4. Document totals vs the sum of their lines ---------------------------------
    def total_check(doc: ExtractedDocument, field: str, label: str, line_attr: str):
        stated = getattr(doc.totals, field)
        summed = _sum(getattr(i, line_attr) for i in doc.line_items)
        if _neq(stated, summed):
            out.add(
                rule="total_vs_lines", severity="review", ask="provider" if doc.doc_type == "bill" else "insurer",
                title=f"{'Bill' if doc.doc_type == 'bill' else 'EOB'} total doesn't equal the sum of its lines",
                detected=f"The {label} printed on the {doc.doc_type.upper()} is {money(stated)}, "
                         f"but its line items add up to {money(summed)}.",
                evidence=[
                    Evidence(document=doc.doc_type, field=label, value=money(stated),
                             location=loc(doc.totals.source.get(field))),
                    Evidence(document="computed", field="Sum of line items", value=money(summed)),
                ],
                why_flagged="A printed total should equal the lines above it.",
                cannot_determine="Whether there are lines on another page that weren't read.",
                suggested_question=f"The {label.lower()} on my statement doesn't match the line items. "
                                   "Can you send a full itemized version?",
                amount_at_stake=abs(round(stated - summed, 2)),
            )

    total_check(bill, "total_billed", "Total charges", "billed")
    total_check(bill, "patient_responsibility", "Balance due", "patient_responsibility")
    total_check(eob, "total_billed", "Total billed", "billed")
    total_check(eob, "patient_responsibility", "Total you may owe", "patient_responsibility")
    total_check(eob, "insurance_paid", "Total plan paid", "plan_paid")

    # --- 5. Bill arithmetic: charges - payments - adjustments = balance ----------------
    if None not in (bt.total_billed, bt.insurance_paid, bt.adjustments, bt.patient_responsibility):
        expected = round(bt.total_billed - bt.insurance_paid - bt.adjustments - (bt.patient_payments or 0), 2)
        if _neq(expected, bt.patient_responsibility):
            out.add(
                rule="bill_balance_arithmetic", severity="review", ask="provider",
                title="Bill balance doesn't follow from its own numbers",
                detected=f"Charges {money(bt.total_billed)} − insurance {money(bt.insurance_paid)} − adjustments "
                         f"{money(bt.adjustments)} − your payments {money(bt.patient_payments or 0)} = {money(expected)}, "
                         f"but the amount due is {money(bt.patient_responsibility)}.",
                evidence=[
                    Evidence(document="bill", field="Total charges", value=money(bt.total_billed), location=loc(bt.source.get("total_billed"))),
                    Evidence(document="bill", field="Insurance payments", value=money(bt.insurance_paid), location=loc(bt.source.get("insurance_paid"))),
                    Evidence(document="bill", field="Adjustments", value=money(bt.adjustments), location=loc(bt.source.get("adjustments"))),
                    Evidence(document="bill", field="Amount due", value=money(bt.patient_responsibility), location=loc(bt.source.get("patient_responsibility"))),
                ],
                why_flagged="A statement's balance should equal charges minus payments and adjustments.",
                cannot_determine="Whether a prior balance or fee was added without its own line.",
                suggested_question="The amount due on my statement doesn't match charges minus payments. "
                                   "Could you walk me through the balance?",
                amount_at_stake=abs(round(expected - bt.patient_responsibility, 2)),
            )

    # --- 6. Insurance payment posted on the bill vs plan paid on the EOB -----------------
    if _neq(bt.insurance_paid, et.insurance_paid):
        out.add(
            rule="insurance_payment_mismatch", severity="review", ask="either",
            title="Insurance payment on the bill differs from the EOB",
            detected=f"The bill credits {money(bt.insurance_paid)} from insurance; the EOB says the plan paid "
                     f"{money(et.insurance_paid)}.",
            evidence=[
                Evidence(document="bill", field="Insurance payments", value=money(bt.insurance_paid), location=loc(bt.source.get("insurance_paid"))),
                Evidence(document="eob", field="Total plan paid", value=money(et.insurance_paid), location=loc(et.source.get("insurance_paid"))),
            ],
            why_flagged="If the provider posted less than the insurer paid, the remainder may have been shifted to you.",
            cannot_determine="Whether the payment is still in transit or was split across claims.",
            suggested_question=f"My EOB says my plan paid {money(et.insurance_paid)}, but my statement shows "
                               f"{money(bt.insurance_paid)}. Has the full payment been posted?",
            amount_at_stake=abs(round(bt.insurance_paid - et.insurance_paid, 2)),
        )

    # Connect the dots: do the bill-side line findings explain the total gap?
    gap = next((f for f in out.findings if f.rule == "patient_total_mismatch"), None)
    if gap and gap.amount_at_stake is not None and bt.patient_responsibility is not None:
        signed_gap = round(bt.patient_responsibility - et.patient_responsibility, 2)
        # (finding, signed effect on "bill minus EOB"): extra bill charges push it up; an EOB line
        # that overstates the patient's share pushes it down.
        parts: list[tuple[Finding, float, str]] = []
        for f in out.findings:
            if f.rule in ("possible_duplicate", "bill_only_item") and f.amount_at_stake:
                parts.append((f, f.amount_at_stake, "extra on the bill"))
            elif f.rule == "billed_amount_mismatch":
                b_it, e_it = bmap[f.related_items[0]], emap[f.related_items[1]]
                parts.append((f, round(b_it.billed - e_it.billed, 2), "price difference"))
            elif f.rule == "eob_line_not_reconciling":
                e_it = emap[f.related_items[0]]
                share = _sum([e_it.deductible, e_it.copay, e_it.coinsurance, e_it.not_covered])
                if share is not None and e_it.patient_responsibility is not None:
                    parts.append((f, -round(e_it.patient_responsibility - share, 2), "EOB overstates your share"))
        explained = round(sum(v for _, v, _ in parts), 2)
        if parts and abs(explained - signed_gap) <= TOL:
            listed = " ".join(
                f"{'+' if v >= 0 else MINUS} {money(abs(v))} ({why}: {f.title.split(': ', 1)[-1]})" for f, v, why in parts
            )
            gap.detected += f" The flagged line items below account for the whole gap: {listed.lstrip('+ ')} = {money(abs(explained))}."
            gap.evidence.append(Evidence(document="computed", field="Explained by flagged lines",
                                         value=f"{money(abs(explained))} of {money(abs(signed_gap))}"))
            gap.related_items = [i for f, _, _ in parts for i in f.related_items]

    order = {"review": 0, "notice": 1}
    out.findings.sort(key=lambda f: (order[f.severity], -(f.amount_at_stake or 0)))
    for i, f in enumerate(out.findings, start=1):
        f.id = f"F{i}"
    return out.findings
