"""Pydantic data models shared across the BillBuddy pipeline."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

DocType = Literal["bill", "eob", "unknown"]


class SourceRef(BaseModel):
    """Where a value came from, so every finding can point back to evidence."""

    page: int = 1
    text: str = ""


class LineItem(BaseModel):
    id: str
    service_date: Optional[str] = None  # ISO yyyy-mm-dd
    code: Optional[str] = None  # CPT / HCPCS, e.g. 85025
    description: str = ""
    billed: Optional[float] = None  # charge as billed by provider
    allowed: Optional[float] = None  # EOB only
    adjustment: Optional[float] = None  # EOB: discount / not allowed
    plan_paid: Optional[float] = None  # EOB only
    deductible: Optional[float] = None
    copay: Optional[float] = None
    coinsurance: Optional[float] = None
    not_covered: Optional[float] = None
    patient_responsibility: Optional[float] = None
    source: SourceRef = Field(default_factory=SourceRef)


class Totals(BaseModel):
    total_billed: Optional[float] = None
    insurance_paid: Optional[float] = None
    adjustments: Optional[float] = None
    patient_payments: Optional[float] = None
    patient_responsibility: Optional[float] = None  # bill "balance due" / EOB "you may owe"
    source: dict[str, SourceRef] = Field(default_factory=dict)


class ExtractedDocument(BaseModel):
    doc_type: DocType = "unknown"
    filename: str = ""
    provider: Optional[str] = None
    insurer: Optional[str] = None
    patient: Optional[str] = None
    claim_id: Optional[str] = None
    account_id: Optional[str] = None
    statement_date: Optional[str] = None  # ISO; bill
    due_date: Optional[str] = None  # ISO; bill payment due date
    processed_date: Optional[str] = None  # ISO; EOB claim processed date
    line_items: list[LineItem] = Field(default_factory=list)
    totals: Totals = Field(default_factory=Totals)
    extraction_method: str = ""  # e.g. "pdf-text + rules", "ocr + gemini"
    raw_text: str = ""
    warnings: list[str] = Field(default_factory=list)


class MatchPair(BaseModel):
    bill_item_id: Optional[str] = None
    eob_item_id: Optional[str] = None
    score: float = 0
    status: Literal["match", "mismatch", "bill_only", "eob_only"]
    reasons: list[str] = Field(default_factory=list)  # why they were paired
    differences: list[str] = Field(default_factory=list)  # fields that differ


class Evidence(BaseModel):
    document: Literal["bill", "eob", "computed"]
    field: str
    value: Optional[str] = None
    location: Optional[str] = None  # e.g. "page 1: '03/14/2026 85025 CBC ...'"


class Finding(BaseModel):
    id: str
    rule: str
    severity: Literal["review", "notice"]
    title: str
    detected: str
    evidence: list[Evidence]
    why_flagged: str
    cannot_determine: str
    suggested_question: str
    ask: Literal["provider", "insurer", "either"] = "either"
    amount_at_stake: Optional[float] = None
    related_items: list[str] = Field(default_factory=list)


class GlossaryTerm(BaseModel):
    term: str
    definition: str
    in_your_documents: Optional[str] = None


class Deadline(BaseModel):
    id: str
    kind: Literal["payment", "followup", "appeal"]
    title: str
    date: str  # ISO yyyy-mm-dd
    description: str
    estimated: bool = False
    source: Optional[str] = None  # link explaining the rule


class PriceCheck(BaseModel):
    code: str
    description: str
    billed: Optional[float] = None  # what the provider charged
    allowed: Optional[float] = None  # what the insurer allowed (EOB)
    medicare_rate: Optional[float] = None  # benchmark, None when not available
    ratio: Optional[float] = None  # billed / medicare_rate
    level: Literal["high", "typical", "unavailable"]
    note: str


class AnalysisResult(BaseModel):
    bill: ExtractedDocument
    eob: ExtractedDocument
    matches: list[MatchPair]
    findings: list[Finding]
    glossary: list[GlossaryTerm]
    summary: str
    summary_source: Literal["gemini", "template"]
    stats: dict
    deadlines: list[Deadline] = Field(default_factory=list)
    pricing: list[PriceCheck] = Field(default_factory=list)
    pricing_source: Optional[str] = None
    # Filled in by the browser after it asks /api/explain-codes; used when building the PDF report.
    code_explanations: dict[str, str] = Field(default_factory=dict)
