"""Optional Gemini integration.

Gemini is used for two things, and the app works without it:
1. Structured extraction for layouts the rules parser can't read.
2. A short plain-English summary of the findings the rules engine already produced.

Gemini never decides whether something is a discrepancy - that is done in rules.py.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from pydantic import BaseModel

from .models import ExtractedDocument, LineItem, SourceRef, Totals

_client = None


def gemini_enabled() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        from google import genai  # imported lazily so the app runs without the key

        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    return _client


def _model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-flash-latest")


# ---------- 1. structured extraction ----------


class _GLine(BaseModel):
    service_date: Optional[str] = None
    code: Optional[str] = None
    description: str
    billed: Optional[float] = None
    allowed: Optional[float] = None
    adjustment: Optional[float] = None
    plan_paid: Optional[float] = None
    deductible: Optional[float] = None
    copay: Optional[float] = None
    coinsurance: Optional[float] = None
    not_covered: Optional[float] = None
    patient_responsibility: Optional[float] = None
    page: Optional[int] = None
    source_text: Optional[str] = None


class _GDoc(BaseModel):
    doc_type: str
    provider: Optional[str] = None
    insurer: Optional[str] = None
    patient: Optional[str] = None
    claim_id: Optional[str] = None
    account_id: Optional[str] = None
    line_items: list[_GLine]
    total_billed: Optional[float] = None
    insurance_paid: Optional[float] = None
    adjustments: Optional[float] = None
    patient_payments: Optional[float] = None
    patient_responsibility: Optional[float] = None


EXTRACTION_PROMPT = """You are extracting data from a US medical document. It is either a provider's
medical bill/statement ("bill") or an insurer's Explanation of Benefits ("eob").

Return JSON only. Rules:
- doc_type: "bill" or "eob".
- One line_items entry per service line. Do NOT include payment or adjustment ledger rows on bills.
- service_date as YYYY-MM-DD. code is the CPT/HCPCS code if printed, else null.
- All money as positive numbers without $ or commas. Use null when a value is not printed.
  Never compute or guess a missing value.
- On bills, the line charge goes in `billed`.
- patient_responsibility at document level: bill "amount due/balance due" or EOB "total you may owe".
- source_text: copy the row text exactly as printed. page: 1-based page number.

Document text (pages separated by ===== PAGE n =====):
"""


def parse_with_gemini(page_texts: list[tuple[int, str]], filename: str, method: str) -> ExtractedDocument:
    from google.genai import types

    text = "\n".join(f"===== PAGE {p} =====\n{t}" for p, t in page_texts)
    response = _get_client().models.generate_content(
        model=_model(),
        contents=EXTRACTION_PROMPT + text,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_GDoc,
            temperature=0,
        ),
    )
    g = response.parsed if isinstance(response.parsed, _GDoc) else _GDoc.model_validate(json.loads(response.text))
    doc_type = g.doc_type if g.doc_type in ("bill", "eob") else "unknown"
    items = []
    for i, ln in enumerate(g.line_items, start=1):
        data = ln.model_dump(exclude={"page", "source_text"})
        items.append(
            LineItem(id=f"{doc_type[0]}{i}", **data, source=SourceRef(page=ln.page or 1, text=ln.source_text or ""))
        )
    return ExtractedDocument(
        doc_type=doc_type,
        filename=filename,
        provider=g.provider,
        insurer=g.insurer,
        patient=g.patient,
        claim_id=g.claim_id,
        account_id=g.account_id,
        line_items=items,
        totals=Totals(
            total_billed=g.total_billed,
            insurance_paid=g.insurance_paid,
            adjustments=g.adjustments,
            patient_payments=g.patient_payments,
            patient_responsibility=g.patient_responsibility,
        ),
        extraction_method=f"{method} + gemini",
        raw_text=text,
    )


# ---------- 2. plain-English summary ----------

SUMMARY_PROMPT = """You help patients understand a medical bill compared with their insurer's
Explanation of Benefits. Below are findings produced by a deterministic rules engine, with evidence.

Write a calm, plain-English summary for the patient in 3-5 sentences (under 110 words):
- Say how many charges matched cleanly and how many items need a human to review.
- Mention the most important item first, with its dollar amounts.
- Do not claim anything is an error or fraud; say it "may need review" and why.
- Do not invent facts, amounts, or plan rules that are not in the data.
- End by suggesting they compare with their insurer before paying.

Data:
"""


def summarize_with_gemini(payload: dict) -> str:
    from google.genai import types

    response = _get_client().models.generate_content(
        model=_model(),
        contents=SUMMARY_PROMPT + json.dumps(payload, indent=1),
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=400),
    )
    return (response.text or "").strip()
