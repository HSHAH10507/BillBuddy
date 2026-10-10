# BillBuddy Health

**Find out whether your medical bill and your insurance statement tell the same story, before you pay.**

About 4 in 10 insured adults under 65 have received a medical bill they didn't expect: one they thought insurance would cover, or one that was higher than they anticipated ([Peterson-KFF, 2020](https://www.healthsystemtracker.org/brief/an-examination-of-surprise-medical-bills-and-proposals-to-protect-consumers-from-them-3/)). After a doctor's visit you usually get two documents: a **bill** from the provider and an **Explanation of Benefits (EOB)** from your insurer. Comparing them line by line is the best way to catch a mistake, but they use different wording, different layouts and terms most people never learned.

BillBuddy Health does that comparison for you. Upload both documents and it:

- **lines up every charge** across the two documents, even when they describe the same service differently;
- **checks the math** and flags anything that doesn't add up: duplicate charges, price differences, totals that don't match, dates or codes that disagree;
- **explains each finding in plain English**, with the exact numbers behind it and a question to ask the provider or insurer;
- **explains every billing code** and compares each charge with what Medicare pays for the same service;
- **tracks your deadlines** (payment due date, when to call, the insurance appeal window) with one-click calendar reminders;
- **produces a PDF report** you can keep or bring to a billing call.

Built in 24 hours at **HackRU Fall 2026** (Social Good track).

> BillBuddy Health helps you prepare questions. It doesn't confirm billing errors and isn't medical, legal or financial advice.

---

## How it works: the chain of functionality

A comparison moves through six stages. Each stage hands structured data to the next, and every number shown to the user can be traced back to a line in one of the two documents.

```
 Upload (PDF or photo)
   │
   ▼
 1. READ ───────── text PDFs: PyMuPDF reads text in drawn pieces ("spans") and rebuilds rows
   │               scans and photos: rendered to an image → Tesseract OCR
   ▼
 2. UNDERSTAND ─── rules parser turns raw text into structured data
   │               (dates, codes, descriptions, money columns, totals, due dates)
   │               └─ unfamiliar layout? → Gemini extracts the same structure instead
   ▼
 3. MATCH ──────── every bill line is scored against every EOB line
   │               (billing code + service date + description similarity + amount)
   ▼
 4. CHECK ──────── deterministic Python rules compare and recompute the numbers
   │               → findings, each with evidence and a suggested question
   ▼
 5. EXPLAIN ────── plain-English summary, glossary filled with the user's own numbers,
   │               code explanations (Gemini), Medicare price comparison, deadlines
   ▼
 6. ACT ────────── results page, calendar reminders (.ics), downloadable PDF report
```

### 1. Reading the documents
Most bills downloaded from a patient portal are **text PDFs**. BillBuddy reads them with **PyMuPDF**, which reports each piece of text with its position on the page. Pieces at the same height are grouped into a row and sorted left to right, which keeps table columns separate even when a long description overlaps the next column. If a page has almost no text (a scanned document), it is rendered as a grayscale image and read with **Tesseract OCR**. Photos of bills go straight to OCR.

### 2. Turning text into data
A **rules parser** (regular expressions and layout heuristics) recognises the common shapes of bills and EOBs:
- rows that start with a date and a code, or that start with a description and end with the code;
- money columns named in a header row ("Billed / Allowed / Plan paid / Deductible / You owe"), including combined columns like "Copay / coins.";
- totals written as "Label $amount", as a "Totals" row, or as a row of labels with the amounts underneath;
- header details: provider, insurer, patient, claim and account numbers, statement date, due date, processed date.

The parser figures out which document is the bill and which is the EOB from its wording, so files can be uploaded in either order. If the parser can't find line items and a total, the document is sent to **Google Gemini**, which returns the same structure as validated JSON. Either way, the result is a typed **Pydantic** model.

### 3. Matching charges across documents
Bills and EOBs rarely describe a service identically ("CBC w/ auto diff" versus "Blood count; complete, automated"). Each candidate pair of lines gets a score:

| Signal | Points |
|---|---|
| Same billing code (CPT/HCPCS) | +50 (different code: −15) |
| Same service date / within 3 days | +20 / +10 |
| Description similarity, after expanding medical abbreviations (**RapidFuzz**) | up to +25 |
| Same billed amount | +10 |

Pairs are assigned greedily from the highest score down, so each line is used once, and anything scoring below 45 stays unmatched.

### 4. Checking the numbers
This is the core of the app, and it's **plain Python arithmetic, not AI**. Twelve rules look for:
- the bill's amount due differing from what the EOB says you owe, and whether the flagged lines **fully explain the gap**;
- possible duplicate charges, and charges that appear on only one document;
- different prices, dates or codes for the same service;
- EOB and bill lines whose parts don't add up (allowed = plan paid + your share);
- printed totals that don't equal the sum of their lines, and bill balances that don't follow from charges minus payments.

Each finding records **what was detected, the exact values and document rows compared, why it was flagged, what the app can't determine, and a question to ask**. Findings say "may need review", never "error".

### 5. Explaining it
- A **glossary** of insurance terms is filled in with the user's own numbers ("Your insurer lists $200.00 as your deductible responsibility…").
- **Gemini** writes a short summary of the rule-based findings and a one-sentence explanation of each billing code. Gemini never decides what counts as a discrepancy.
- A **fair-price check** compares each charge with the 2026 Medicare Physician Fee Schedule rate for the same code.
- **Deadlines** are computed from the documents: the payment due date, a suggested call-by date, and the 180-day window for an insurance appeal ([HealthCare.gov](https://www.healthcare.gov/appeal-insurance-company-decision/internal-appeals/)).

### 6. Acting on it
The results page shows the matched charges, charts, findings and dates. Users can add deadlines to their calendar (a standard `.ics` file with reminders) and download a full **PDF report** built with **ReportLab**.

---

## Design principles

- **Evidence over trust.** Every flag shows the numbers that triggered it.
- **AI assists; arithmetic decides.** Gemini reads unusual layouts and writes explanations; discrepancies are always computed in code.
- **Works without AI.** The rules parser, all checks and built-in code explanations run with no API key, so the app still works if Gemini is down.
- **Privacy by default.** Documents are analyzed in memory and never stored, and document text is never written to logs.

---

## What it relies on

| Layer | What it does | Built with |
|---|---|---|
| Frontend | Upload, results, charts, calendar export, routing between Home / About / Analyze | React, TypeScript, Vite, Tailwind CSS, Recharts, React Router |
| API | Receives uploads, runs the pipeline in a worker thread, serves the built site | FastAPI, Uvicorn |
| Reading | Text extraction from PDFs; OCR for scans and photos | PyMuPDF, pdfplumber (fallback), Tesseract + pytesseract, Pillow |
| Understanding | Rules parser; data validation | Python regular expressions, Pydantic |
| Matching | Fuzzy description comparison | RapidFuzz |
| AI (optional) | Extraction for unusual layouts, summaries, code explanations | Google Gemini (`google-genai`) |
| Reports | PDF generation | ReportLab |
| Hosting | Single container serving the site and the API | Docker, Render |

---

## Run it locally

**Prerequisites:** Python 3.10+, Node.js 18+, and Tesseract OCR (`brew install tesseract`, `sudo apt install tesseract-ocr`, or the [Windows installer](https://github.com/UB-Mannheim/tesseract/wiki)).

**Backend** (terminal 1):
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # optional: add GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

**Frontend** (terminal 2):
```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>, click **Check my bill**, then **Load sample documents → Compare documents**. The sample documents are fictional.

**Tests:** `cd backend && pytest -q`

### Optional: Gemini
Without a key, BillBuddy uses its rules parser and built-in explanations. To enable Gemini, add `GEMINI_API_KEY=...` (from [Google AI Studio](https://aistudio.google.com/apikey)) to `backend/.env`, or to the host's environment variables when deployed. `EXTRACTOR=auto|rules|gemini` controls when Gemini is used for extraction (default `auto`: only when the rules parser can't read a layout).

### Deploy
The `Dockerfile` builds the frontend and runs the API in one container; `render.yaml` deploys it on Render. Set `GEMINI_API_KEY` in the host's environment settings.

---

## Project structure

```
backend/app/
  main.py             API routes and the pipeline
  text_extraction.py  1. read PDFs and images (PyMuPDF, OCR)
  parsing.py          2. rules parser
  gemini_client.py    2/5. Gemini extraction and summaries, with retries and fallbacks
  matching.py         3. line matching (RapidFuzz)
  rules.py            4. discrepancy checks
  explain.py          5. glossary and summary
  codes.py            5. code explanations (Gemini + built-in)
  pricing.py          5. Medicare fair-price check
  deadlines.py        5. important dates
  report.py           6. PDF report
  models.py           Pydantic data models
backend/samples/      fictional bill and EOB (and the script that generates them)
backend/tests/        end-to-end tests
frontend/src/pages/   Home, About, Analyze
frontend/src/components/  upload, matching board, charts, findings, deadlines, services
```

---

## Limitations

- Bills and EOBs come in thousands of layouts; the rules parser covers common ones, and unusual layouts depend on Gemini being available.
- Compares one bill with one EOB for the same claim. Prior balances or charges from another visit can explain some differences.
- Medicare benchmarks currently cover office visits, ER visits and common imaging/ECG codes; lab tests use a separate Medicare schedule and aren't compared yet. Private insurance usually pays more than Medicare, so the ratio is a reference point, not a fair price.
- The appeal deadline is an estimate based on the EOB's processed date; plan documents have the exact date.

## Sources
- Peterson-KFF Health System Tracker, [An examination of surprise medical bills](https://www.healthsystemtracker.org/brief/an-examination-of-surprise-medical-bills-and-proposals-to-protect-consumers-from-them-3/) (2020)
- KFF, [Claims Denials and Appeals in ACA Marketplace Plans in 2024](https://www.kff.org/private-insurance/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/)
- HealthCare.gov, [Internal appeals](https://www.healthcare.gov/appeal-insurance-company-decision/internal-appeals/)
- CMS 2026 Medicare Physician Fee Schedule (national amounts, via [FastRVU](https://fastrvu.com/))
