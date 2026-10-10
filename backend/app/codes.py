"""Plain-English explanations of billing codes.

Gemini writes them (POST /api/explain-codes). A small built-in set, written in our own words,
is used when Gemini isn't configured or is unavailable, so common codes always get an answer.
"""
from __future__ import annotations

import json
import re
import threading

from pydantic import BaseModel

from .gemini_client import _generate, _model, describe_error, gemini_enabled, log

BUILTIN: dict[str, str] = {
    "99202": "A short visit with a doctor you haven't seen before (or not in 3+ years) for a simple problem.",
    "99203": "A visit with a new doctor for a fairly simple problem that needs some evaluation.",
    "99204": "A longer visit with a new doctor for a problem that takes more evaluation, like several symptoms or tests to review.",
    "99205": "A long, in-depth visit with a new doctor for a complex problem.",
    "99211": "A brief visit, often with a nurse, such as a blood pressure check.",
    "99212": "A short visit with your regular doctor for a simple issue.",
    "99213": "A standard visit with your regular doctor for a common problem, like a follow-up or a minor illness.",
    "99214": "A longer visit with your regular doctor for a more involved problem, such as managing an ongoing condition or new symptoms.",
    "99215": "An extended visit with your regular doctor for a complex or serious problem.",
    "99283": "An emergency room visit for a problem of moderate urgency.",
    "99284": "An emergency room visit for a serious problem that needs prompt evaluation.",
    "99285": "An emergency room visit for a severe or potentially life-threatening problem.",
    "36415": "The fee for drawing your blood with a needle so it can be sent for lab tests.",
    "85025": "A complete blood count (CBC): checks your red cells, white cells and platelets, often to look for infection or anemia.",
    "80053": "A comprehensive metabolic panel: one blood test that checks kidney and liver function, blood sugar and electrolytes.",
    "80048": "A basic metabolic panel: a blood test for kidney function, blood sugar and electrolytes.",
    "80061": "A lipid panel: a blood test that measures cholesterol and triglycerides.",
    "83036": "A hemoglobin A1c test: shows your average blood sugar over the past 2-3 months, used to check for or manage diabetes.",
    "84443": "A TSH test: a blood test that checks how well your thyroid is working.",
    "81002": "A basic urine test done in the office.",
    "81003": "A urine test run on an automated machine to check for things like infection or blood sugar.",
    "71045": "A chest X-ray with one picture.",
    "71046": "A chest X-ray with two pictures (front and side), often used to look at the lungs and heart.",
    "93000": "An electrocardiogram (ECG/EKG): records your heart's electrical activity, including the doctor's reading of it.",
    "90471": "The fee for giving you a vaccine shot (the vaccine itself is billed separately).",
    "87880": "A rapid strep test using a throat swab.",
}

_cache: dict[str, str] = {}
_lock = threading.Lock()


class _Expl(BaseModel):
    code: str
    explanation: str


class _ExplList(BaseModel):
    items: list[_Expl]


PROMPT = """Explain each US medical billing code below to a patient in plain English.
For each, write ONE sentence of at most 30 words: what the service is and, if helpful, why it's commonly done.
No jargon, no diagnosis, no prices, don't mention insurance coverage. If you are not sure what a code means,
use the description provided on the bill. Return JSON: {"items": [{"code": "...", "explanation": "..."}]}.

Codes (with the description printed on the bill):
"""


def explain_codes(items: list[tuple[str, str]]) -> dict[str, dict[str, str]]:
    """items: (code, description on the bill). Returns {code: {"text": ..., "source": "gemini" | "builtin"}}."""
    codes = {c.split("-")[0].upper(): d for c, d in items if c}
    result: dict[str, dict[str, str]] = {}
    with _lock:
        for c in codes:
            if c in _cache:
                result[c] = {"text": _cache[c], "source": "gemini"}
    todo = {c: d for c, d in codes.items() if c not in result}

    if todo and gemini_enabled():
        listing = "\n".join(f"- {c}: {d}" for c, d in todo.items())
        try:
            resp = _generate(PROMPT + listing, models=[_model()], attempts=2, budget_s=20,
                             response_mime_type="application/json", temperature=0.2)
            raw = re.sub(r"^```(?:json)?|```$", "", (resp.text or "").strip(), flags=re.M).strip()
            parsed = _ExplList.model_validate(json.loads(raw))
            with _lock:
                for it in parsed.items:
                    code = it.code.split("-")[0].upper()
                    if code in todo and it.explanation.strip():
                        _cache[code] = it.explanation.strip()
                        result[code] = {"text": _cache[code], "source": "gemini"}
        except Exception as exc:  # noqa: BLE001 - fall back to built-in text
            log.warning("Gemini code explanations failed: %s", describe_error(exc))

    for c in todo:
        if c not in result and c in BUILTIN:
            result[c] = {"text": BUILTIN[c], "source": "builtin"}
    return result
