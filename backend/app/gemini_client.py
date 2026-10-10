"""Optional Gemini integration.

Gemini is used for two things, and the app works without it:
1. Structured extraction for layouts the rules parser can't read.
2. A short plain-English summary of the findings the rules engine already produced.

Gemini never decides whether something is a discrepancy - that is done in rules.py.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
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

        from google.genai import types

        _client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            http_options=types.HttpOptions(timeout=int(os.getenv("GEMINI_TIMEOUT_MS", "25000"))),
        )
    return _client


def _model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-flash-latest")


log = logging.getLogger("uvicorn.error")


def _models() -> list[str]:
    """Configured model first, then fallbacks in case it is overloaded or retired."""
    out = []
    for m in (_model(), os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-lite-latest"), "gemini-2.5-flash"):
        if m and m not in out:
            out.append(m)
    return out


def _generate(contents: str, models: list[str] | None = None, attempts: int = 3, budget_s: float = 30.0, **config):
    """Call Gemini with retries on temporary server errors (5xx / overloaded) and model fallbacks."""
    from google.genai import errors, types

    last: Exception | None = None
    deadline = time.monotonic() + budget_s  # never keep the user waiting longer than this
    for model in models or _models():
        for attempt in range(attempts):
            if time.monotonic() > deadline:
                raise last if last else TimeoutError("Gemini time budget exceeded")
            try:
                return _get_client().models.generate_content(
                    model=model, contents=contents, config=types.GenerateContentConfig(**config)
                )
            except errors.ServerError as exc:  # 500/503: overloaded or internal, worth retrying
                last = exc
                log.warning("Gemini %s server error (attempt %d): %s", model, attempt + 1, str(exc)[:200])
                time.sleep(1.0 * (attempt + 1))
            except errors.ClientError as exc:
                last = exc
                log.warning("Gemini %s client error: %s", model, str(exc)[:200])
                if getattr(exc, "code", None) in (404, 429):  # unknown model or rate limit: try next model
                    break
                raise
    raise last if last else RuntimeError("Gemini call failed")


def describe_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc)[:180]}"


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
    try:
        # Preferred: structured output constrained to the schema.
        response = _generate(EXTRACTION_PROMPT + text, models=[_model()], attempts=1, budget_s=20,
                             response_mime_type="application/json", response_schema=_GDoc, temperature=0)
        g = response.parsed if isinstance(response.parsed, _GDoc) else _GDoc.model_validate(json.loads(response.text))
    except Exception as exc:  # noqa: BLE001
        # Fallback: plain JSON mode with the schema described in the prompt (avoids schema-related API errors).
        log.warning("Structured Gemini extraction failed (%s); retrying in plain JSON mode", describe_error(exc))
        prompt = (EXTRACTION_PROMPT.replace("Document text", "JSON shape:\n" + json.dumps(_GDoc.model_json_schema())
                                            + "\n\nDocument text") + text)
        response = _generate(prompt, budget_s=25, response_mime_type="application/json", temperature=0)
        raw = re.sub(r"^```(?:json)?|```$", "", (response.text or "").strip(), flags=re.M).strip()
        g = _GDoc.model_validate(json.loads(raw))
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

    # The summary is optional (a template is used otherwise), so give it one quick try only.
    response = _generate(SUMMARY_PROMPT + json.dumps(payload, indent=1), models=[_model()], attempts=1,
                         budget_s=15, temperature=0.2, max_output_tokens=400)
    return (response.text or "").strip()
