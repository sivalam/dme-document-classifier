# dme-document-classifier

A production-oriented pipeline that classifies DME medical PDFs and evaluates patient workflow readiness.

Built as a take-home engineering exercise. Intentionally goes beyond the minimum spec to demonstrate operational thinking, AI integration reasoning, and production-oriented architecture.

---

## Quick Start

### 1. Clone the repo

```powershell
git clone https://github.com/sivalam/dme-document-classifier.git
cd dme-document-classifier
```

### 2. Create and activate virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Create a .env file in the project root

```env
OPENAI_API_KEY=your_openai_key_here
CONFIDENCE_THRESHOLD=0.80
```

### 5. Add your PDFs to the documents/ folder

```text
documents/
  your_document_1.pdf
  your_document_2.pdf
  ...
```

### 6. Run the pipeline

```powershell
python -m src.classify --input documents --output output
```

Optional: override confidence threshold (default 0.80)

```powershell
python -m src.classify --input documents --output output --threshold 0.80
```

### 7. To Run unit tests (optional — no API key required)

```powershell
python -m pytest -v
```
---

## What It Does

1. Reads PDFs from the `documents/` folder
2. Classifies each document using GPT-4o-mini via OpenAI Files API + Responses API
3. Groups documents by patient
4. Checks whether each patient file is complete enough to start a workflow
5. Flags low-confidence or failed classifications for human review
6. Writes results to JSON, CSV, and SQLite

> **Note:** The pipeline is currently configured for OpenAI GPT-4o-mini. The classifier is isolated in `src/classifier.py` — switching to a different model or provider is a contained change.

---

## Outputs

```text
output/
  classifications.json    <- machine-readable, for pipeline integration
  classifications.csv     <- human-readable, for coordinator review
  dme_classifier.db       <- SQLite audit trail, document types, and history
```

---

## Run Tests

```powershell
python -m pytest -v
```

Tests use mocked OpenAI calls — no API key required to run the test suite.

A small integration spike is included at `scratch/test_pdf_api.py`. This script uploads a real PDF to OpenAI using the Files API and Responses API to validate end-to-end ingestion independently from the main pipeline.

---

## Dashboard

View a live dashboard of results from an end-to-end run against the provided DME documents:

**https://sivalam.github.io/dme-document-classifier/dashboard/index.html**

Or open `dashboard/index.html` locally in any browser after running the pipeline against your own documents.

---

## How To Read This Repository

| Document | What It Contains |
|---|---|
| `PROJECT_CONTEXT.md` | Full project context, architecture summary, current status, validation findings |
| `docs/PRD.md` | Problem statement, jobs to be done, goals, scope |
| `docs/ARCHITECTURE.md` | System design, module responsibilities, data flow, production roadmap |
| `docs/AI_OBSERVATIONS.md` | What we learned building this — prompt design, API findings, rate limits, operational non-determinism |
| `docs/HIPAA_AND_PRIVACY.md` | PHI handling strategy and compliance requirements for production |
| `docs/adr/` | Individual technical decisions with options, trade-offs, and conditions for reversal |

Start with `PROJECT_CONTEXT.md` for the full picture.

---

## Repository Structure

```text
src/
  classify.py       pipeline entry point and CLI
  extractor.py      PDF ingestion from local disk (S3 stub for production)
  classifier.py     OpenAI Files API integration and classification
  completeness.py   patient workflow completeness evaluation
  storage.py        JSON, CSV, and SQLite output
  database.py       document type configuration and SQLite schema

tests/
  unit tests for all modules 

docs/
  PRD.md
  ARCHITECTURE.md
  AI_OBSERVATIONS.md
  HIPAA_AND_PRIVACY.md
  adr/
    ADR-001 through ADR-005

dashboard/
  index.html        live results dashboard

scratch/
  test_pdf_api.py   isolated OpenAI API integration spike

documents/          place your PDFs here to run the pipeline
output/             generated results — gitignored
```

---

## Validation Summary

Validated against 21 sample DME PDFs:

- PDF ingestion via OpenAI Files API and Responses API
- Classification across all 6 document types
- Graceful handling of rate limits and failures
- Patient completeness evaluation
- Persistence to JSON, CSV, and SQLite

**Notable findings:**

- `Prescription 2.pdf` was classified as Order — the document content contained HCPCS codes, equipment quantities, and an electronic physician signature. The model's classification was defensible.
- Intentionally incomplete patient files confirmed the value of completeness checking beyond classification
- Rate limits introduced operational non-determinism — same documents produced different completeness outcomes across runs depending on API load at runtime
- Sequential batch processing improved with per-document sleep but did not fully eliminate rate limit failures on large documents

See `PROJECT_CONTEXT.md` and `docs/AI_OBSERVATIONS.md` for full discussion.