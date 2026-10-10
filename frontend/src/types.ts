// Mirrors backend/app/models.py

export interface SourceRef { page: number; text: string }

export interface LineItem {
  id: string;
  service_date: string | null;
  code: string | null;
  description: string;
  billed: number | null;
  allowed: number | null;
  adjustment: number | null;
  plan_paid: number | null;
  deductible: number | null;
  copay: number | null;
  coinsurance: number | null;
  not_covered: number | null;
  patient_responsibility: number | null;
  source: SourceRef;
}

export interface Totals {
  total_billed: number | null;
  insurance_paid: number | null;
  adjustments: number | null;
  patient_payments: number | null;
  patient_responsibility: number | null;
}

export interface ExtractedDocument {
  doc_type: "bill" | "eob" | "unknown";
  filename: string;
  provider: string | null;
  insurer: string | null;
  patient: string | null;
  claim_id: string | null;
  account_id: string | null;
  line_items: LineItem[];
  totals: Totals;
  extraction_method: string;
  raw_text: string;
  warnings: string[];
}

export type MatchStatus = "match" | "mismatch" | "bill_only" | "eob_only";

export interface MatchPair {
  bill_item_id: string | null;
  eob_item_id: string | null;
  score: number;
  status: MatchStatus;
  reasons: string[];
  differences: string[];
}

export interface Evidence {
  document: "bill" | "eob" | "computed";
  field: string;
  value: string | null;
  location: string | null;
}

export interface Finding {
  id: string;
  rule: string;
  severity: "review" | "notice";
  title: string;
  detected: string;
  evidence: Evidence[];
  why_flagged: string;
  cannot_determine: string;
  suggested_question: string;
  ask: "provider" | "insurer" | "either";
  amount_at_stake: number | null;
  related_items: string[];
}

export interface GlossaryTerm { term: string; definition: string; in_your_documents: string | null }

export interface AnalysisResult {
  bill: ExtractedDocument;
  eob: ExtractedDocument;
  matches: MatchPair[];
  findings: Finding[];
  glossary: GlossaryTerm[];
  summary: string;
  summary_source: "gemini" | "template";
  stats: {
    matched: number;
    mismatched: number;
    bill_only: number;
    eob_only: number;
    review_findings: number;
    amount_in_question: number;
    gemini_enabled: boolean;
  };
}
