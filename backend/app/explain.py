"""Step 5: plain-English explanations.

The glossary and the "in your documents" sentences are templates filled with the extracted
numbers, so they are always grounded. Gemini (optional) only writes the short overall summary.
"""
from __future__ import annotations

from .gemini_client import gemini_enabled, summarize_with_gemini
from .models import ExtractedDocument, Finding, GlossaryTerm, MatchPair
from .rules import _sum, money

GLOSSARY = {
    "Billed amount": "The provider's full list price for a service, before any insurance discounts. "
                     "Insured patients rarely pay this full amount.",
    "Allowed amount": "The maximum your insurer has agreed to pay for a covered service with an in-network "
                      "provider. Your share is calculated from this number, not from the billed amount.",
    "Adjustment": "The difference between the billed amount and the allowed amount. In-network providers have "
                  "generally agreed to write this off, so it typically shouldn't be billed to you.",
    "Deductible": "The amount you pay for covered care each plan year before your insurance starts sharing costs.",
    "Copay": "A fixed dollar amount you pay for a type of service, such as $30 for an office visit.",
    "Coinsurance": "Your percentage share of the allowed amount after your deductible is met, such as 20%.",
    "Plan paid": "What your insurance company actually paid the provider for the service.",
    "Patient responsibility": "What the insurer says you owe the provider: usually deductible + copay + "
                              "coinsurance + anything not covered.",
    "EOB": "Explanation of Benefits: a statement from your insurer showing how a claim was processed. "
           "It is not a bill.",
    "CPT code": "A five-digit code that identifies a medical service. The same code on two documents usually "
                "means the same service.",
}


def build_glossary(bill: ExtractedDocument, eob: ExtractedDocument) -> list[GlossaryTerm]:
    items = eob.line_items
    ded = _sum(i.deductible for i in items)
    coins = _sum(i.coinsurance for i in items)
    copay = _sum(i.copay for i in items)
    adj = _sum(i.adjustment for i in items)
    allowed = _sum(i.allowed for i in items)
    billed = _sum(i.billed for i in items)
    paid = eob.totals.insurance_paid if eob.totals.insurance_paid is not None else _sum(i.plan_paid for i in items)
    owe = eob.totals.patient_responsibility

    context = {
        "Billed amount": f"Your EOB shows {money(billed)} billed across {len(items)} service(s)." if billed else None,
        "Allowed amount": f"Your insurer allowed {money(allowed)} in total for these services." if allowed else None,
        "Adjustment": f"Your EOB lists {money(adj)} in discounts/adjustments. This generally means the provider agreed "
                      "not to charge that portion; check that it isn't included in your bill's amount due." if adj else None,
        "Deductible": f"Your insurer lists {money(ded)} as your deductible responsibility. This generally means that this "
                      "portion of the covered cost is assigned to your deductible under your plan. Check your plan "
                      "details to confirm how it applies." if ded else None,
        "Copay": f"Your EOB assigns {money(copay)} in copays." if copay else None,
        "Coinsurance": f"Your EOB lists {money(coins)} as coinsurance — your percentage share after the deductible." if coins else None,
        "Plan paid": f"Your plan paid {money(paid)} toward this claim." if paid else None,
        "Patient responsibility": f"Your EOB says you may owe {money(owe)}; your bill asks for "
                                  f"{money(bill.totals.patient_responsibility)}." if owe is not None else None,
        "EOB": "Your second document is the EOB; the first is the provider's bill." if eob.doc_type == "eob" else None,
        "CPT code": "BillBuddy matched lines across documents using these codes where printed."
                    if any(i.code for i in bill.line_items + items) else None,
    }
    return [GlossaryTerm(term=t, definition=d, in_your_documents=context.get(t)) for t, d in GLOSSARY.items()]


def template_summary(matches: list[MatchPair], findings: list[Finding]) -> str:
    clean = sum(m.status == "match" for m in matches)
    review = [f for f in findings if f.severity == "review"]
    total = len(matches)
    if not findings:
        return (f"All {clean} charges on your bill line up with your EOB, and the totals agree. "
                "Nothing stood out for review, but it's still worth keeping both documents together.")
    top = findings[0]
    stake = f" ({money(top.amount_at_stake)})" if top.amount_at_stake else ""
    return (
        f"{clean} of {total} line items matched cleanly between your bill and your EOB. "
        f"{len(review)} item(s) may need a human to review. The most important: \u201c{top.title}\u201d{stake}. "
        "None of these are confirmed errors — each has a suggested question below. "
        "It's a good idea to ask about them before paying."
    )


def build_summary(bill, eob, matches, findings) -> tuple[str, str]:
    fallback = template_summary(matches, findings)
    if not gemini_enabled():
        return fallback, "template"
    payload = {
        "matched_cleanly": sum(m.status == "match" for m in matches),
        "total_line_pairs": len(matches),
        "bill_amount_due": bill.totals.patient_responsibility,
        "eob_patient_responsibility": eob.totals.patient_responsibility,
        "findings": [
            {"title": f.title, "detected": f.detected, "severity": f.severity, "amount_at_stake": f.amount_at_stake}
            for f in findings
        ],
    }
    try:
        text = summarize_with_gemini(payload)
        return (text, "gemini") if text else (fallback, "template")
    except Exception:  # noqa: BLE001 - never let the summary break the analysis
        return fallback, "template"
