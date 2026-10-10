"""Step 2: turn raw document text into structured data.

Two extractors produce the same `ExtractedDocument`:

* `parse_with_rules` - deterministic regex/heuristic parser. Fast and offline. It handles the
  common statement layouts:
    - rows that start with a date and code   ("03/14/2026 99214 Office visit ... $285.00")
    - rows that start with the description   ("Office visit — 99213 09/14/26 $180.00 $55.00 ...")
    - rows with no date (the document-level "Date(s) of service" is used instead)
    - money columns named in a header row, including combined ones like "Copay / coins."
    - totals printed as "Label $amount", as a "Totals" row, or as a label row followed by an amount row
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
DATE_SEARCH = re.compile(rf"(?<![\d/]){DATE_RE}(?![\d/])")
# CPT (5 digits, optionally a letter suffix) or HCPCS (letter + 4 digits), optional modifier.
CODE_SEARCH = re.compile(r"(?<![\w/$.,-])([A-Z]\d{4}|\d{4,5}[A-Z]?)(?:-[A-Z0-9]{2})?(?![\w/.,])")
LEDGER_WORDS = re.compile(r"\b(payment|write.?off|refund|transfer)\b", re.I)


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


def normalize_line(line: str) -> str:
    """Separate glued tokens like '85025$95.00' -> '85025 $95.00'."""
    return re.sub(r"(?<=[0-9A-Za-z.)])\$", " $", line).strip()


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
    eob_hits = sum(k in t for k in (
        "explanation of benefits", "this is not a bill", "it is not a bill", "plan paid", "allowed amount",
        "member owes",
    ))
    bill_hits = sum(k in t for k in ("statement", "amount due", "balance due", "pay this amount", "please pay"))
    if eob_hits > bill_hits:
        return "eob"
    if bill_hits:
        return "bill"
    return "unknown"


def _ordered_matches(text: str, patterns: list[tuple[str, str]]) -> list[tuple[int, str]]:
    """Find every pattern in `text`, blanking each match so later patterns can't reuse it.
    Returns (position, field) sorted by position, i.e. the left-to-right column order."""
    taken = text.lower()
    found: list[tuple[int, str]] = []
    for pattern, fieldname in patterns:
        for m in re.finditer(pattern, taken):
            found.append((m.start(), fieldname))
            taken = taken[: m.start()] + " " * (m.end() - m.start()) + taken[m.end():]
    return sorted(found)


# ---------- money columns in line-item tables ----------

# Order matters: more specific patterns first (each match is blanked out before the next pattern).
COLUMN_KEYWORDS: list[tuple[str, str]] = [
    (r"copay\s*/\s*coins\w*\.?", "coinsurance"),  # combined column
    (r"you (?:may )?owe|patient resp\w*|your share|patient portion|member owes|patient owes|amount you owe", "patient_responsibility"),
    (r"plan paid|paid by plan|plan payment|insurance pay\w*|insurance paid", "plan_paid"),
    (r"not covered", "not_covered"),
    (r"discount|not allowed|adjust\w*|network savings|write.?off", "adjustment"),
    (r"allowed", "allowed"),
    (r"billed|amount charged|charges?", "billed"),
    (r"deductible", "deductible"),
    (r"copay\w*", "copay"),
    (r"coinsurance|coins\.?", "coinsurance"),
]
DEFAULT_EOB_COLUMNS = [
    "billed", "adjustment", "allowed", "plan_paid", "deductible", "copay", "coinsurance", "patient_responsibility",
]


def header_columns(line: str) -> list[str] | None:
    cols = [f for _, f in _ordered_matches(line, COLUMN_KEYWORDS)]
    return cols if cols and ("billed" in cols or len(cols) >= 2) else None


# ---------- header fields & totals ----------

# Labels match in any case ((?i:...)); values must start with a capital letter or digit, so
# "Patient Statement" isn't mistaken for a patient name.
STOP = r"(?=\s+(?i:account|member|dob|claim|id|group|statement|date|due|npi|provider|processed)\b|\s*\||$)"
FIELD_PATTERNS = {
    "patient": rf"\b(?i:patient|member)(?i: name)?(?:\s*:\s*|\s+(?=[A-Z][a-z]+\s+[A-Z]))(.+?){STOP}",
    "claim_id": r"\b(?i:claim)\s*(?i:#|no\.?|number|id|reference|ref\.?)\s*:?\s*([A-Z0-9][A-Z0-9-]{3,})",
    "account_id": r"\b(?i:account)\s*(?i:#|no\.?|number)\s*:?\s*([A-Z0-9][A-Z0-9-]{3,})",
    "provider": rf"\b(?i:(?:rendering |billing )?(?:provider|facility))(?:\s*:\s*|\s+(?=[A-Z]))(.+?){STOP}",
    "insurer": rf"\b(?i:insurer|health plan|plan name|insurance(?: listed)?)(?:\s*:\s*|\s+(?=[A-Z]))(.+?){STOP}",
}
DOC_DATES = {
    "statement_date": re.compile(rf"statement\s+date\s*:?\s*({DATE_RE})", re.I),
    "due_date": re.compile(rf"(?:due\s+date|due\s+by|payment\s+due(?:\s+date)?|pay\s+by|please\s+pay\s+by)\s*:?\s*({DATE_RE})", re.I),
    "processed_date": re.compile(rf"(?:processed(?:\s+date|\s+on)?|date\s+processed|claim\s+processed)\s*:?\s*({DATE_RE})", re.I),
}
SERVICE_DATE = re.compile(rf"(?:date\(?s?\)?\s+of\s+service|service\s+date|dos)\s*:?\s*({DATE_RE})", re.I)

TOTAL_PATTERNS: list[tuple[str, str]] = [
    ("patient_responsibility", r"amount due|balance due|total you (?:may )?owe|(?:total )?patient responsibility|"
                               r"member owes|pay this amount|you may owe"),
    ("insurance_paid", r"insurance payments?|insurance paid|(?:total )?plan paid|paid by plan|plan payments?"),
    ("patient_payments", r"patient payments?|payments received|payments?\s*/\s*credits"),
    ("total_billed", r"total (?:charges|billed|amount billed)"),
    ("_ignore", r"total allowed|allowed"),
    ("adjustments", r"(?:insurance |contractual )?adjustments?|network discount|total discount|discounts?"),
]


def _find_field(lines: list[str], key: str) -> str | None:
    pattern = re.compile(FIELD_PATTERNS[key])
    for line in lines:
        m = pattern.search(line)
        if m and m.group(1).strip(" .:|"):
            return m.group(1).strip(" .:|")
    return None


def _total_label_columns(line: str) -> list[str]:
    return [f for _, f in _ordered_matches(line, [(p, k) for k, p in TOTAL_PATTERNS])]


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

    all_lines = [(p.page, normalize_line(ln)) for p in text_result.pages for ln in p.text.splitlines() if ln.strip()]
    plain = [ln for _, ln in all_lines]

    title_words = re.compile(r"(?i)\s*(?:patient statement|statement|explanation of benefits|\(?eob\)?|"
                             r"this is not a bill|medical bill)\b.*$")
    for key in ("patient", "claim_id", "account_id", "provider", "insurer"):
        value = _find_field(plain, key)
        if value and key in ("provider", "insurer"):
            value = title_words.sub("", value).strip(" |-") or None  # drop document titles on the same line
        setattr(doc, key, value)
    # Fallbacks: statements usually print the facility first; EOBs print the insurer near the top.
    if plain:
        if doc_type == "bill" and not doc.provider:
            doc.provider = title_words.sub("", plain[0].split("|")[0]).strip() or None
        if doc_type == "eob" and not doc.insurer:
            for cand in plain[:3]:
                name = re.sub(r"(?i)\s*(explanation of benefits|\(?eob\)?|this is not a bill).*$", "", cand.split("|")[0]).strip()
                if name:
                    doc.insurer = name
                    break

    for key, pattern in DOC_DATES.items():
        dm = pattern.search(full)
        if dm:
            setattr(doc, key, parse_date(dm.group(1)))

    m = SERVICE_DATE.search(full)
    default_date = parse_date(m.group(1)) if m else None

    columns: list[str] | None = None
    totals = Totals()
    pending_total_labels: tuple[list[str], int, str] | None = None
    n = 0

    def set_total(key: str, value: float, page: int, text: str):
        if key != "_ignore" and getattr(totals, key) is None:
            setattr(totals, key, abs(value))
            totals.source[key] = SourceRef(page=page, text=text)

    for page, line in all_lines:
        low = line.lower()
        desc_part, amounts = split_trailing_amounts(line)

        # A row of amounts right under a row of total labels ("Total charges  Balance due" / "$415.00  $125.80")
        if pending_total_labels and amounts and not desc_part:
            labels, lpage, ltext = pending_total_labels
            if len(labels) == len(amounts):
                for key, value in zip(labels, amounts):
                    set_total(key, value, page, f"{ltext} / {line}")
            pending_total_labels = None
            continue
        pending_total_labels = None

        if not amounts:
            total_labels = _total_label_columns(line)
            if len(total_labels) >= 2 and re.search(r"\btotal|balance due|amount due|summary", low):
                pending_total_labels = (total_labels, page, line)
            elif header_columns(line) and not re.search(r"\btotal", low):
                columns = header_columns(line)
            continue

        # Line item: has amounts, a description, and a date or billing code.
        date_m = DATE_SEARCH.search(desc_part)
        code_m = CODE_SEARCH.search(DATE_SEARCH.sub(" ", desc_part))
        if (date_m or code_m) and not low.startswith("total") and not LEDGER_WORDS.search(desc_part):
            desc = DATE_SEARCH.sub(" ", desc_part)
            if code_m:
                desc = desc.replace(code_m.group(0), " ", 1)
            desc = re.sub(r"\s+", " ", desc).strip(" -—–|:,")
            if desc:
                n += 1
                item = LineItem(
                    id=f"{doc_type[0]}{n}",
                    service_date=parse_date(date_m.group(0)) if date_m else default_date,
                    code=code_m.group(1) if code_m else None,
                    description=desc,
                    source=SourceRef(page=page, text=line),
                )
                cols = columns or (DEFAULT_EOB_COLUMNS if doc_type == "eob" else None)
                if cols:
                    use = cols[-len(amounts):] if len(amounts) <= len(cols) else cols
                    vals = amounts[-len(use):]
                    for fieldname, value in zip(use, vals):
                        setattr(item, fieldname, abs(value))
                else:
                    item.billed = abs(amounts[0])
                doc.line_items.append(item)
                continue

        # "Totals" row aligned with the item columns
        if low.startswith("total") and columns and len(amounts) >= 2:
            mapping = dict(zip(columns[-len(amounts):], amounts))
            for col, key in (("billed", "total_billed"), ("adjustment", "adjustments"),
                             ("plan_paid", "insurance_paid"), ("patient_responsibility", "patient_responsibility")):
                if col in mapping:
                    set_total(key, mapping[col], page, line)
            continue

        # "Label  $amount" totals
        for key, pattern in TOTAL_PATTERNS:
            if re.search(pattern, low):
                set_total(key, amounts[-1], page, line)
                break

    if doc_type == "eob" and not columns and doc.line_items:
        doc.warnings.append("EOB column header not found; assumed the standard column order.")
    doc.totals = totals
    if not doc.line_items:
        doc.warnings.append("No line items recognised by the rules parser.")
    return doc


def rules_result_is_usable(doc: ExtractedDocument) -> bool:
    return bool(doc.line_items) and doc.totals.patient_responsibility is not None and doc.doc_type != "unknown"
