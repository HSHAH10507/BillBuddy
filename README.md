# BillBuddy Health — Medical Bill Explainer

BillBuddy compares a provider's **medical bill** with the insurer's **Explanation of Benefits (EOB)**.
It extracts every charge from both documents, matches them line by line (even when the wording differs),
runs deterministic reconciliation checks, and explains anything a human should review — with the exact
values and source rows behind every finding.

Built for HackRU Fall 2026 (Social Good track).

---

## What it does

| Feature | How |
|---|---|
| 1. Upload & extraction | PDFs (pdfplumber / PyMuPDF) or photos and scanned PDFs (Tesseract OCR), parsed into structured data validated by Pydantic. A rules parser handles standard layouts offline; Gemini is used only when a layout isn't recognised. |
| 2. Smart matching | Each bill line is scored against each EOB line on billing code, service date, description similarity (RapidFuzz + medical-abbreviation normalisation, e.g. "CBC w/ auto diff" ≈ "Blood count; complete, automated") and amount. |
| 3. Discrepancy engine | Plain Python checks: amount due vs. EOB "you owe", unmatched or duplicate lines, different charges/dates/codes for the same service, EOB lines whose parts don't sum, totals vs. sum of lines, bill balance arithmetic, insurance payment posted vs. paid. It also tests whether the flagged lines **fully explain** the total gap. |
| 4. Plain-English explanations | A glossary filled in with the user's own numbers. Gemini (optional) writes a short summary of the rule-based findings — it never decides what is a discrepancy. |
| 5. Evidence report | Each finding lists what was detected, the compared values and the document rows they came from, why it was flagged, what the app can't determine, and a copyable question for the provider or insurer. |

### The demo story (fictional sample documents)

The bill asks for **$299.00**, the EOB says the patient owes **$254.00**. BillBuddy finds:

- a venipuncture charge billed **twice** (+$35),
- a metabolic panel billed at $210 vs. $190 on the claim (+$20),
- an EOB line where "you owe" is $94 but deductible + coinsurance = $84 (−$10),
- an A1c test dated a day apart,

and shows that **$35 + $20 − $10 = $45**, the entire gap. The office visit and CBC match even though their descriptions are worded differently.

---

## Project structure

```
billbuddy/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI routes + pipeline
│   │   ├── text_extraction.py  # PDF text layer, OCR fallback
│   │   ├── parsing.py          # rules-based structured extraction
│   │   ├── gemini_client.py    # optional Gemini extraction + summary
│   │   ├── matching.py         # line-item matching (RapidFuzz)
│   │   ├── rules.py            # discrepancy detection engine
│   │   ├── explain.py          # glossary + summaries
│   │   └── models.py           # Pydantic models
│   ├── samples/                # fictional bill/EOB + generator script
│   ├── tests/test_pipeline.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/                   # React + TypeScript + Vite + Tailwind + Recharts
    └── src/components/         # upload, match board, charts, findings, glossary
```

---

## Setup

### Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.10 or newer | `python --version` |
| Node.js | 18 or newer (20+ recommended) | `node --version` |
| Tesseract OCR | any recent version | `tesseract --version` |
| Git | any | `git --version` |

**Installing Tesseract** (only needed for photos and scanned PDFs; text PDFs work without it):

- **macOS:** `brew install tesseract`
- **Ubuntu/Debian:** `sudo apt install tesseract-ocr`
- **Windows:** install from the [UB Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki). If `tesseract --version` doesn't work in a new terminal afterward, set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` in `backend/.env`.

### 1. Backend (FastAPI)

```bash
cd backend

# create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows (PowerShell or cmd)

pip install -r requirements.txt

# optional configuration (Gemini key, extractor mode)
cp .env.example .env               # Windows: copy .env.example .env

# run the API on http://127.0.0.1:8000
uvicorn app.main:app --reload --port 8000
```

Check it's running: open <http://127.0.0.1:8000/api/health>. Interactive API docs are at <http://127.0.0.1:8000/docs>.

### 2. Frontend (React + Vite)

In a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server forwards `/api` requests to the backend on port 8000, so both must be running.

### 3. Try it

1. Click **Load sample documents** (or **a photographed bill (OCR)** to exercise Tesseract).
2. Click **Compare documents**.
3. Click any amber or red row in *Charge matching* to jump to its finding.

You can also upload your own PDFs or photos. The two files can be dropped in either order — BillBuddy detects which one is the EOB.

---

## Gemini (optional)

BillBuddy runs fully without an API key. Adding one enables:

- extraction for document layouts the rules parser doesn't recognise, and
- a short AI-written summary of the findings.

1. Get a key at <https://aistudio.google.com/apikey>.
2. Put it in `backend/.env`: `GEMINI_API_KEY=your-key`
3. Restart the backend. `/api/health` should show `"gemini_enabled": true`.

Settings in `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `GEMINI_MODEL` | `gemini-flash-latest` | Model name. Change it if Google renames the alias. |
| `EXTRACTOR` | `auto` | `auto` = rules first, Gemini only if needed · `rules` = never use Gemini for extraction · `gemini` = always use Gemini |

Discrepancy detection is always done in Python, never by the model.

---

## Useful commands

```bash
# backend tests (from backend/, venv active)
pytest -q

# regenerate the fictional sample documents
python samples/generate_samples.py

# see what BillBuddy extracts from one document
curl -F "file=@samples/sample_eob.pdf" http://127.0.0.1:8000/api/extract

# production build of the frontend
cd frontend && npm run build
```

### API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/analyze` | multipart form with `bill` and `eob` files → full analysis |
| `POST` | `/api/extract` | one `file` → extracted structured data (debugging) |
| `POST` | `/api/analyze-samples` | analyse the bundled sample documents |
| `GET` | `/api/samples/{name}` | download a sample document |
| `GET` | `/api/health` | status and whether Gemini is enabled |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Frontend shows "Request failed… Is the backend running?" | Start the backend on port 8000 (step 1). |
| `TesseractNotFoundError` | Install Tesseract, or set `TESSERACT_CMD` in `backend/.env` (Windows). |
| `pip install` fails on PyMuPDF | Upgrade pip: `python -m pip install --upgrade pip`, then retry. |
| Port 8000 or 5173 already in use | Backend: `--port 8001` and change the target in `frontend/vite.config.ts`. Frontend: `npm run dev -- --port 5174` and add that origin to `CORS_ORIGINS`. |
| Your own document finds no charges | Add a `GEMINI_API_KEY` so unusual layouts fall back to Gemini, or check the raw text under *How BillBuddy read your documents*. |

---

## Limitations & responsible use

- BillBuddy prepares questions; it doesn't confirm billing errors or give medical, legal, or financial advice.
- Findings say "may need review" and always list what the app can't determine.
- The bundled documents are fictional. Don't commit real medical documents to the repo.
