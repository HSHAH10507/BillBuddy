"""Step 2: turn raw document text into structured data.

Two extractors produce the same `ExtractedDocument`:

* `parse_with_rules` - deterministic regex/heuristic parser. Fast, offline, and works on
  typical statement layouts (rows that start with a date and end with dollar amounts).
* `parse_with_gemini` (in gemini_client.py) - used when the rules parser can't find line
  items, or when EXTRACTOR=gemini. Handles unusual layouts.
"""
from __future__ import annotations

import re
from datetime import datetime

from .models import DocType, ExtractedDocument, LineItem, SourceRef, Totals
from .text_extraction import TextResult

# ---------- small helpers ----------

AMOUNT_RE = re.compile(r"^\(?-?[\$S]?-?\(?[\d,]*\d\.\d{2}\)?$")
DATE_RE = r"\d{1,2}/\d{1,2}/\d{2,4}"
LINE_RE = re.compile(
    rf"^(?P<date>{DATE_RE})\s+(?:(?:-|to|thru)\s*{DATE_RE}\s+)?"
    r"(?:(?P<code>[A-Z]?\d{4,5}[A-Z]?)(?:-[A-Z0-9]{2})?\s+)?(?P<rest>.+)$"
)


def parse_amount(token: str) -> float | None:
    t = token.strip()
    negative = t.startswith("-") or t.startswith("(") or "-" in t[:3]
    digits = re.sub(r"[^\d.]", "", t)
    if not digits or digits.count(".") != 1:
        return None
    try:
        value = float(digits)
    except ValueError:
        return None
    return -value if negative else value


def parse_date(token: str) -> str | None:
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(token, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def split_trailing_amounts(rest: str) -> tuple[str, list[float]]:
    """'CBC with auto diff $145.00 $12.00' -> ('CBC with auto diff', [145.0, 12.0])."""
    tokens = rest.split()
    amounts: list[float] = []
    while tokens and AMOUNT_RE.match(tokens[-1]):
        value = parse_amount(tokens.pop())
        if value is None:
            break
        amounts.insert(0, value)
    return " ".join(tokens).strip(" .:-"), amounts


def detect_doc_type(text: str) -> DocType:
    t = text.lower()
    eob_hits = sum(k in t for k in ("explanation of benefits", "this is not a bill", "plan paid", "allowed amount"))
    bill_hits = sum(k in t for k in ("statement", "amount due", "balance due", "pay this amount", "please pay"))
    if eob_hits > bill_hits:
        return "eob"
    if bill_hits:
        return "bill"
    return "unknown"


# ---------- EOB column mapping ----------

# keyword -> LineItem field. Order of appearance in the header row decides the column order.
EOB_COLUMN_KEYWORDS: list[tuple[str, str]] = [
    (r"billed|amount charged|charges?", "billed"),
    (r"discount|not allowed|adjust\w*|network savings", "adjustment"),
    (r"allowed", "allowed"),
    (r"plan paid|paid by plan|plan payment|insurance paid", "plan_paid"),
    (r"deductible", "deductible"),
    (r"copay\w*", "copay"),
    (r"coins\w*\.?|coinsurance", "coinsurance"),
    (r"not covered", "not_covered"),
    (r"you (?:may )?owe|patient resp\w*|your share", "patient_responsibility"),
]
DEFAULT_EOB_COLUMNS = [
    "billed", "adjustment", "allowed", "plan_paid", "deductible", "copay", "coinsurance", "patient_responsibility",
]


def detect_eob_columns(lines: list[str]) -> list[str] | None:
    for line in lines:
        low = line.lower()
        if "billed" in low and "allowed" in low:
            found: list[tuple[int, str]] = []
            taken = low
            for pattern, fieldname in EOB_COLUMN_KEYWORDS:
                m = re.search(pattern, taken)
                if m:
                    found.append((m.start(), fieldname))
                    # blank out the match so "allowed" inside "not allowed" isn't reused
                    taken = taken[: m.start()] + " " * (m.end() - m.start()) + taken[m.end():]
            if len(found) >= 4:
                return [f for _, f in sorted(found)]
    return None


# ---------- header fields & totals ----------

FIELD_PATTERNS = {
    "patient": r"patient(?: name)?\s*:\s*(.+?)(?=\s+(?:account|member|dob|claim|id|group)\b|$)",
    "claim_id": r"claim\s*(?:#|no\.?|number|id)\s*:?\s*([A-Z0-9-]{4,})",
    "account_id": r"account\s*(?:#|no\.?|number)\s*:?\s*([A-Z0-9-]{4,})",
    "provider": r"(?:provider|rendering provider|billing provider|facility)\s*:\s*(.+?)(?=\s+(?:npi|claim|account)\b|$)",
    "insurer": r"(?:insurer|health plan|plan name|insurance)\s*:\s*(.+?)(?=\s+(?:member|group|id)\b|$)",
}

TOTAL_PATTERNS = [
    ("total_billed", r"total (?:charges|billed|amount billed)"),
    ("insurance_paid", r"insurance payments?|total (?:plan paid|paid by plan)|plan payments?|insurance paid"),
    ("adjustments", r"(?:insurance |contractual )?adjustments?|network discount|total discount"),
    ("patient_payments", r"patient payments?|payments received"),
    ("patient_responsibility", r"amount due|balance due|total you (?:may )?owe|total patient responsibility|pay this amount"),
]


def _find_field(lines: list[str], key: str) -> str | None:
    pattern = re.compile(FIELD_PATTERNS[key], re.IGNORECASE)
    for line in lines:
        m = pattern.search(line)
        if m:
            return m.group(1).strip(" .:")
    return None


def parse_with_rules(text_result: TextResult, filename: str) -> ExtractedDocument:
    full = text_result.full_text
    doc_type = detect_doc_type(full)
    doc = ExtractedDocument(
        doc_type=doc_type,
        filename=filename,
        raw_text=full,
        extraction_method=f"{text_result.method} + rules",
        warnings=list(text_result.warnings),
    )

    all_lines = [(p.page, ln.strip()) for p in text_result.pages for ln in p.text.splitlines() if ln.strip()]
    plain = [ln for _, ln in all_lines]

    for key in ("patient", "claim_id", "account_id", "provider", "insurer"):
        setattr(doc, key, _find_field(plain, key))
    # Statements usually print the facility name as the first line; EOBs print the insurer.
    if plain:
        if doc_type == "bill" and not doc.provider:
            doc.provider = plain[0]
        if doc_type == "eob" and not doc.insurer:
            doc.insurer = re.sub(r"(?i)\s*(explanation of benefits|eob|this is not a bill).*$", "", plain[0]).strip()

    eob_columns = detect_eob_columns(plain) if doc_type == "eob" else None
    if doc_type == "eob" and not eob_columns:
        eob_columns = DEFAULT_EOB_COLUMNS
        doc.warnings.append("EOB column header not found; assumed the standard column order.")

    totals = Totals()
    n = 0
    for page, line in all_lines:
        m = LINE_RE.match(line)
        if m:
            desc, amounts = split_trailing_amounts(m.group("rest"))
            date = parse_date(m.group("date"))
            is_ledger_row = bool(re.search(r"\b(payment|adjustment|write.?off|refund|transfer)\b", desc, re.I))
            if amounts and date and desc and not is_ledger_row:
                n += 1
                item = LineItem(
                    id=f"{doc_type[0]}{n}",
                    service_date=date,
                    code=m.group("code"),
                    description=desc,
                    source=SourceRef(page=page, text=line),
                )
                if doc_type == "eob" and eob_columns:
                    for fieldname, value in zip(eob_columns, amounts[-len(eob_columns):]):
                        setattr(item, fieldname, abs(value))
                else:
                    item.billed = amounts[-1]
                doc.line_items.append(item)
                continue

        # Totals rows
        low = line.lower()
        _, amounts = split_trailing_amounts(line)
        if not amounts:
            continue
        if doc_type == "eob" and eob_columns and low.startswith("total") and len(amounts) >= 4:
            mapping = dict(zip(eob_columns, amounts[-len(eob_columns):]))
            totals.total_billed = mapping.get("billed")
            totals.adjustments = mapping.get("adjustment")
            totals.insurance_paid = mapping.get("plan_paid")
            totals.patient_responsibility = mapping.get("patient_responsibility")
            for k in ("total_billed", "adjustments", "insurance_paid", "patient_responsibility"):
                totals.source[k] = SourceRef(page=page, text=line)
            continue
        for key, pattern in TOTAL_PATTERNS:
            if re.search(pattern, low) and getattr(totals, key) is None:
                setattr(totals, key, abs(amounts[-1]))
                totals.source[key] = SourceRef(page=page, text=line)
                break

    doc.totals = totals
    if not doc.line_items:
        doc.warnings.append("No line items recognised by the rules parser.")
    return doc


def rules_result_is_usable(doc: ExtractedDocument) -> bool:
    return bool(doc.line_items) and doc.totals.patient_responsibility is not None and doc.doc_type != "unknown"
