"""Step 3: pair each bill line with the EOB line describing the same service.

Every candidate pair gets a score from four signals:
  billing code  (strongest - same code is very likely the same service)
  service date  (same day, or within a few days)
  description   (RapidFuzz similarity after normalising medical abbreviations)
  amount        (same billed amount)
Pairs are then assigned greedily from highest score down, so each line is used once.
"""
from __future__ import annotations

import re
from datetime import date

from rapidfuzz import fuzz

from .models import ExtractedDocument, LineItem, MatchPair

MATCH_THRESHOLD = 45.0
MONEY_TOLERANCE = 0.01

# Common abbreviations on bills and EOBs -> expanded words, so "CBC w/ auto diff"
# and "Complete blood count, automated" compare as similar.
ABBREVIATIONS = {
    "w/": "with ", "w/o": "without ", "cbc": "complete blood count", "cmp": "comprehensive metabolic panel",
    "bmp": "basic metabolic panel", "diff": "differential", "auto": "automated", "est": "established",
    "pt": "patient", "ov": "office visit", "e&m": "office visit", "eval": "evaluation", "mgmt": "management",
    "venipunct": "venipuncture", "draw": "venipuncture", "xr": "x-ray", "xray": "x-ray", "rad": "radiology",
    "inj": "injection", "admin": "administration", "vacc": "vaccine", "imm": "immunization", "tsh": "thyroid stimulating hormone",
    "a1c": "hemoglobin a1c", "aic": "hemoglobin a1c", "hgb": "hemoglobin", "ua": "urinalysis", "lab": "laboratory", "outpt": "outpatient",
    "mod": "moderate", "ecg": "electrocardiogram", "ekg": "electrocardiogram", "chg": "charge", "svc": "service",
}
STOPWORDS = {"the", "of", "and", "a", "an", "for", "with", "per", "each", "test", "panel", "service", "charge"}


def normalize_description(text: str) -> str:
    t = text.lower()
    t = t.replace("w/o", " without ").replace("w/", " with ")
    t = re.sub(r"[^a-z0-9&\- ]", " ", t)
    words = []
    for w in t.split():
        words.extend(ABBREVIATIONS.get(w, w).split())
    return " ".join(w for w in words if w not in STOPWORDS)


def _days_apart(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def _base_code(code: str | None) -> str | None:
    return code.split("-")[0].upper() if code else None


def score_pair(b: LineItem, e: LineItem) -> tuple[float, list[str], dict]:
    score = 0.0
    reasons: list[str] = []
    detail: dict = {}

    bc, ec = _base_code(b.code), _base_code(e.code)
    if bc and ec:
        detail["code_equal"] = bc == ec
        if bc == ec:
            score += 50
            reasons.append(f"same billing code {bc}")
        else:
            score -= 15

    days = _days_apart(b.service_date, e.service_date)
    detail["days_apart"] = days
    if days == 0:
        score += 20
        reasons.append("same service date")
    elif days is not None and days <= 3:
        score += 10
        reasons.append(f"service dates {days} day(s) apart")

    sim = fuzz.token_set_ratio(normalize_description(b.description), normalize_description(e.description))
    detail["description_similarity"] = round(sim)
    score += sim * 0.25
    if sim >= 70:
        reasons.append(f"similar descriptions ({round(sim)}% match)")

    if b.billed is not None and e.billed is not None:
        detail["amount_equal"] = abs(b.billed - e.billed) <= MONEY_TOLERANCE
        if detail["amount_equal"]:
            score += 10
            reasons.append("same billed amount")

    return round(score, 1), reasons, detail


def match_documents(bill: ExtractedDocument, eob: ExtractedDocument) -> list[MatchPair]:
    candidates = []
    for b in bill.line_items:
        for e in eob.line_items:
            s, reasons, detail = score_pair(b, e)
            candidates.append((s, b, e, reasons, detail))
    candidates.sort(key=lambda c: c[0], reverse=True)

    used_b: set[str] = set()
    used_e: set[str] = set()
    pairs: list[MatchPair] = []
    for s, b, e, reasons, detail in candidates:
        if s < MATCH_THRESHOLD or b.id in used_b or e.id in used_e:
            continue
        used_b.add(b.id)
        used_e.add(e.id)
        diffs = []
        if detail.get("code_equal") is False:
            diffs.append("code")
        if detail.get("days_apart"):
            diffs.append("service_date")
        if detail.get("amount_equal") is False:
            diffs.append("billed")
        pairs.append(
            MatchPair(
                bill_item_id=b.id, eob_item_id=e.id, score=s,
                status="mismatch" if diffs else "match", reasons=reasons, differences=diffs,
            )
        )

    for b in bill.line_items:
        if b.id not in used_b:
            pairs.append(MatchPair(bill_item_id=b.id, status="bill_only"))
    for e in eob.line_items:
        if e.id not in used_e:
            pairs.append(MatchPair(eob_item_id=e.id, status="eob_only"))

    order = {it.id: i for i, it in enumerate(bill.line_items)}
    eorder = {it.id: i for i, it in enumerate(eob.line_items)}
    pairs.sort(key=lambda p: (order.get(p.bill_item_id, 999), eorder.get(p.eob_item_id, 999)))
    return pairs
