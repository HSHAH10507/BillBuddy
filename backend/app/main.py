"""BillBuddy Health API.

Pipeline for POST /api/analyze:
  upload -> text (pdf text layer or OCR) -> structured data (rules, or Gemini fallback)
         -> match lines -> deterministic discrepancy rules -> explanations
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .explain import build_glossary, build_summary  # noqa: E402
from .gemini_client import gemini_enabled, parse_with_gemini  # noqa: E402
from .matching import match_documents  # noqa: E402
from .models import AnalysisResult, ExtractedDocument  # noqa: E402
from .parsing import parse_with_rules, rules_result_is_usable  # noqa: E402
from .rules import detect_discrepancies  # noqa: E402
from .text_extraction import extract_text  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024

app = FastAPI(title="BillBuddy Health API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_document(data: bytes, filename: str, content_type: str | None) -> ExtractedDocument:
    """Text -> structured data. EXTRACTOR=auto|rules|gemini (default auto)."""
    text = extract_text(data, filename, content_type)
    mode = os.getenv("EXTRACTOR", "auto").lower()
    rules_doc = parse_with_rules(text, filename)

    want_gemini = gemini_enabled() and (mode == "gemini" or (mode == "auto" and not rules_result_is_usable(rules_doc)))
    if want_gemini and text.full_text.strip():
        try:
            doc = parse_with_gemini([(p.page, p.text) for p in text.pages], filename, text.method)
            doc.warnings = text.warnings + doc.warnings
            if doc.doc_type == "unknown":
                doc.doc_type = rules_doc.doc_type
            return doc
        except Exception as exc:  # noqa: BLE001
            rules_doc.warnings.append(f"Gemini extraction failed, used rules parser instead ({type(exc).__name__}).")
    elif mode == "auto" and not rules_result_is_usable(rules_doc) and not gemini_enabled():
        rules_doc.warnings.append("Layout not fully recognised. Add a GEMINI_API_KEY to handle unusual layouts.")
    return rules_doc


async def _read(upload: UploadFile) -> bytes:
    data = await upload.read()
    if not data:
        raise HTTPException(400, f"{upload.filename} is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"{upload.filename} is larger than 15 MB.")
    return data


def analyze_documents(doc_a: ExtractedDocument, doc_b: ExtractedDocument) -> AnalysisResult:
    # Accept the two files in either order: figure out which is the bill and which is the EOB.
    bill, eob = doc_a, doc_b
    if doc_a.doc_type == "eob" and doc_b.doc_type != "eob":
        bill, eob = doc_b, doc_a
    bill.doc_type, eob.doc_type = "bill", "eob"

    matches = match_documents(bill, eob)
    findings = detect_discrepancies(bill, eob, matches)
    summary, source = build_summary(bill, eob, matches, findings)
    stats = {
        "matched": sum(m.status == "match" for m in matches),
        "mismatched": sum(m.status == "mismatch" for m in matches),
        "bill_only": sum(m.status == "bill_only" for m in matches),
        "eob_only": sum(m.status == "eob_only" for m in matches),
        "review_findings": sum(f.severity == "review" for f in findings),
        "amount_in_question": round(max((f.amount_at_stake or 0) for f in findings), 2) if findings else 0,
        "gemini_enabled": gemini_enabled(),
    }
    return AnalysisResult(
        bill=bill, eob=eob, matches=matches, findings=findings,
        glossary=build_glossary(bill, eob), summary=summary, summary_source=source, stats=stats,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "gemini_enabled": gemini_enabled(), "extractor": os.getenv("EXTRACTOR", "auto")}


@app.post("/api/extract", response_model=ExtractedDocument)
async def extract_one(file: UploadFile = File(...)):
    """Debug helper: see what BillBuddy extracts from a single document."""
    return extract_document(await _read(file), file.filename or "upload", file.content_type)


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze(bill: UploadFile = File(...), eob: UploadFile = File(...)):
    a = extract_document(await _read(bill), bill.filename or "bill", bill.content_type)
    b = extract_document(await _read(eob), eob.filename or "eob", eob.content_type)
    if not a.line_items and not b.line_items:
        raise HTTPException(422, "Couldn't find any charges in either document. Try a clearer PDF or image.")
    return analyze_documents(a, b)


@app.get("/api/samples")
def list_samples():
    return sorted(p.name for p in SAMPLES_DIR.glob("*") if p.suffix.lower() in {".pdf", ".png", ".jpg"})


@app.get("/api/samples/{name}")
def get_sample(name: str):
    path = (SAMPLES_DIR / name).resolve()
    if path.parent != SAMPLES_DIR.resolve() or not path.is_file():
        raise HTTPException(404, "Sample not found")
    return FileResponse(path)


@app.post("/api/analyze-samples", response_model=AnalysisResult)
def analyze_samples(bill: str = "sample_bill.pdf", eob: str = "sample_eob.pdf"):
    """One-click demo using the bundled fictional documents."""
    docs = []
    for name in (bill, eob):
        path = (SAMPLES_DIR / name).resolve()
        if path.parent != SAMPLES_DIR.resolve() or not path.is_file():
            raise HTTPException(404, f"Sample {name} not found")
        docs.append(extract_document(path.read_bytes(), name, None))
    return analyze_documents(*docs)


# ---------- Serve the built React app (production / Docker) ----------
# In development, Vite serves the frontend on :5173. In production the frontend is built
# into static files and FastAPI serves them, so the app and API share one URL.
from fastapi.staticfiles import StaticFiles  # noqa: E402

FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))

if FRONTEND_DIST.is_dir():
    if (FRONTEND_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def serve_frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        file = (FRONTEND_DIST / path).resolve()
        if path and file.is_file() and FRONTEND_DIST.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")
