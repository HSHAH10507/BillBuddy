"""Run with:  pytest -q   (from the backend folder)"""
from fastapi.testclient import TestClient

from app.main import app
from app.matching import normalize_description

client = TestClient(app)


def _rules(result):
    return {f["rule"] for f in result["findings"]}


def test_sample_pdfs_find_all_planted_issues():
    r = client.post("/api/analyze-samples").json()
    assert r["bill"]["totals"]["patient_responsibility"] == 299.0
    assert r["eob"]["totals"]["patient_responsibility"] == 254.0
    assert _rules(r) == {
        "patient_total_mismatch", "possible_duplicate", "billed_amount_mismatch",
        "eob_line_not_reconciling", "date_mismatch",
    }
    assert r["stats"]["matched"] == 4
    gap = next(f for f in r["findings"] if f["rule"] == "patient_total_mismatch")
    assert "account for the whole gap" in gap["detected"]


def test_files_can_be_uploaded_in_either_order():
    files = {
        "bill": ("eob.pdf", open("samples/sample_eob.pdf", "rb"), "application/pdf"),
        "eob": ("bill.pdf", open("samples/sample_bill.pdf", "rb"), "application/pdf"),
    }
    r = client.post("/api/analyze", files=files).json()
    assert r["bill"]["filename"] == "bill.pdf"
    assert len(r["findings"]) == 5


def test_scanned_bill_goes_through_ocr():
    r = client.post("/api/analyze-samples", params={"bill": "sample_bill_scanned.pdf"}).json()
    assert r["bill"]["extraction_method"].startswith("ocr")
    assert len(r["bill"]["line_items"]) == 7
    assert "possible_duplicate" in _rules(r)


def test_abbreviations_are_normalised():
    assert "complete blood count" in normalize_description("CBC w/ auto diff")


def test_description_first_layout_without_gemini():
    """Team's own sample layout: code inside the description, EOB rows without dates,
    a combined 'Copay / coins.' column, and summary labels above their amounts."""
    files = {
        "bill": ("bill.pdf", open("tests/fixtures/BillBuddy_Sample_Medical_Bill.pdf", "rb"), "application/pdf"),
        "eob": ("eob.pdf", open("tests/fixtures/BillBuddy_Sample_EOB.pdf", "rb"), "application/pdf"),
    }
    r = client.post("/api/analyze", files=files).json()
    assert [i["code"] for i in r["bill"]["line_items"]] == ["99213", "85025", "80053"]
    assert r["eob"]["line_items"][1]["service_date"] == "2026-09-14"
    assert r["bill"]["totals"]["patient_responsibility"] == 125.8
    assert r["eob"]["totals"]["patient_responsibility"] == 110.8
    assert r["stats"]["matched"] == 3
    assert "patient_total_mismatch" in _rules(r)


def test_pdf_report_download():
    analysis = client.post("/api/analyze-samples").json()
    r = client.post("/api/report", json=analysis)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert "attachment" in r.headers["content-disposition"]
