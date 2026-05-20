# dme-document-classifier

A production-oriented pipeline that classifies DME medical PDFs and evaluates patient workflow readiness.

Built as a take-home engineering exercise. Intentionally goes beyond the minimum spec to demonstrate operational thinking, AI integration reasoning, and production-oriented architecture.

---

## What It Does

1. Reads a folder of DME PDFs
2. Classifies each document using GPT-4o-mini
3. Groups documents by patient
4. Checks whether each patient file is complete enough to start a workflow
5. Flags low-confidence or failed classifications for human review
6. Writes results to JSON, CSV, and SQLite

---

## Quick Start

```powershell
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your OpenAI API key
# Create a .env file in the project root:
OPENAI_API_KEY=your_key_here

# 4. Place PDFs in the documents/ folder

# 5. Run the pipeline
python -m src.classify --input documents --output output

# Optional: override confidence threshold (default 0.80)
python -m src.classify --input documents --output output --threshold 0.80
```

---

## Outputs

```text
output/
  classifications.json    <- machine-readable, for pipeline integration
  classifications.csv     <- human-readable, for coordinator review
  dme_classifier.db       <- SQLite audit trail, taxonomy, and history
```

---

## Run Tests

```powershell
python -m pytest -v
```

Tests use mocked OpenAI calls — no API key required.

A small integration spike is included at `scratch/test_pdf_api.py`. This script uploads a few real PDFs to OpenAI using the Files API and Responses API flow to validate end-to-end PDF ingestion independently from the main pipeline.

---

## How To Read This Repository

| Document | What It Contains |
|---|---|
| `PROJECT_CONTEXT.md` | Full project context, architecture summary, current status, validation findings |
| `dashboard/index.html` | Results of the end-end pipeline run against the provided DME documents. |
| `docs/AI_OBSERVATIONS.md` | What we learned building this — prompt design, API findings, rate limits, confidence scoring |
| `docs/PRD.md` | Problem statement, jobs to be done, goals, scope |
| `docs/ARCHITECTURE.md` | System design, module responsibilities, data flow, production roadmap |
| `docs/adr/` | Individual technical decisions with options, trade-offs, and conditions for reversal |

---

## Repository Structure

```text
src/
  classify.py       pipeline entry point and CLI
  extractor.py      PDF ingestion from local disk (S3 stub for production)
  classifier.py     OpenAI Files API integration and classification
  completeness.py   patient workflow completeness evaluation
  storage.py        JSON, CSV, and SQLite output
  database.py       taxonomy configuration and SQLite schema

tests/
  unit tests for all modules — 42 passing

docs/
  PRD.md
  ARCHITECTURE.md
  AI_OBSERVATIONS.md
  adr/
    ADR-001 through ADR-005

dashboard/
  index.html        open in browser to review sample test run results

scratch/
  test_pdf_api.py   isolated OpenAI API integration spike

documents/          place input PDFs here
output/             generated results (gitignored)
```

---

## Validation Summary

Validated against 21 sample DME PDFs:

- PDF ingestion via OpenAI Files API and Responses API
- Classification across all 6 document types
- Graceful handling of rate limits and failures
- Patient completeness evaluation
- Persistence to JSON, CSV, and SQLite

## Dashboard

Open `dashboard/index.html` in a browser to view the results from a full end-to-end pipeline run against the 21 provided DME documents.

## Notable findings

- `Prescription 2.pdf` was classified as Order — the document content contained HCPCS codes, equipment quantities, and an electronic physician signature. The model's finding was defensible.
- Intentionally incomplete patient files confirmed the value of completeness checking beyond classification
- Sequential batch processing surfaced rate limit behavior — documented in `docs/AI_OBSERVATIONS.md`

See `PROJECT_CONTEXT.md` and `docs/AI_OBSERVATIONS.md` for full discussion.

