# CLAUDE.md — dme-document-classifier

## Project Summary

Python CLI that classifies DME medical PDF documents into 6 types using the OpenAI API, then checks per-patient file completeness and writes results to JSON, CSV, and SQLite.

## Tech Stack

- **Language:** Python 3.11+
- **LLM API:** OpenAI `gpt-4o-mini` via Files API + Responses API
- **PDF handling:** `pypdf` for page counting only — full PDF sent to OpenAI for classification
- **Database:** SQLite via standard library `sqlite3`
- **Config:** `python-dotenv` reading `.env`

## How PDF Classification Works

PDFs are uploaded via the OpenAI Files API and referenced in a Responses API call. The model handles both digital text and scanned/image content natively. No OCR or text extraction is performed before classification.

Note: sending PDFs via `chat.completions` image_url fails — only the Files API + Responses API flow works for PDF input.

## Document Types

1. Prescription
2. Sleep Study Report
3. Physician Notes
4. Compliance Report
5. Order
6. Delivery Ticket

Unknown is a valid classification — documents that do not match any known type are flagged for human review rather than forced into a category.

## Document Type Configuration

Document types are stored in SQLite (`document_types` table), not hardcoded. The classifier queries them at runtime and builds the prompt dynamically. Adding support for a new DME equipment type is a database insert — no code change required.

## Coding Standards

- **Type hints** on every function signature (parameters and return type)
- **Dataclasses** for all data models (`ExtractedContent`, `ClassificationResult`, `PatientStatus`)
- **Docstrings** on every function (one-line summary + Args/Returns)
- Never hardcode API keys — read from `.env` via `python-dotenv`
- All output written to `output/` — git-ignored
- Tests use mocked OpenAI calls — no API key required to run the test suite

## Key Files

| File | Role |
|---|---|
| `src/classify.py` | CLI entry point and pipeline orchestrator |
| `src/extractor.py` | Reads PDF from disk, returns bytes and page count. S3 stub for production. |
| `src/classifier.py` | Uploads PDF via Files API, classifies via Responses API, returns structured result |
| `src/completeness.py` | Groups documents by patient, checks required document set, returns workflow readiness |
| `src/storage.py` | Writes JSON, CSV, and SQLite outputs in a single pass |
| `src/database.py` | SQLite schema, document type seed data, taxonomy queries |

## Environment Variables

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `CONFIDENCE_THRESHOLD` | Minimum confidence to auto-route (default 0.80) |

## Running

```powershell
python -m src.classify --input documents --output output
```

## Tests

```powershell
python -m pytest -v
```

Comprehensive pytest coverage with mocked OpenAI calls.