# CLAUDE.md — ashvin-doc-classifier

## Project Summary

Python CLI that classifies DME medical PDF documents into 6 types using the OpenAI API, then checks per-patient file completeness.

## Tech Stack

- **Language:** Python 3.11+
- **LLM API:** OpenAI `gpt-4o-mini` (chat completions + vision)
- **PDF extraction:** `pdfplumber` (digital PDFs), GPT-4o-mini vision (scanned/image PDFs)
- **Config:** `python-dotenv` reading `.env`

## Document Types

1. Prescription
2. Sleep Study Report
3. Physician Notes
4. Compliance Report
5. Order
6. Delivery Ticket

## Dual-Path PDF Extraction

- Try `pdfplumber` first.
- If extracted text is **fewer than 50 characters**, treat as scanned: convert pages to images and send to GPT-4o-mini vision API.
- Threshold is set by `TEXT_THRESHOLD = 50` in `extractor.py`.

## Coding Standards

- **Type hints** on every function signature (parameters and return type).
- **Dataclasses** for all data models (`ExtractionResult`, `ClassificationResult`, `PatientRecord`).
- **Docstrings** on every function (one-line summary + Args/Returns).
- Never hardcode API keys — read from `.env` via `python-dotenv`.
- All output is written to `output/`; this directory is git-ignored.

## Key Files

| File | Role |
|------|------|
| `src/extractor.py` | Dual-path PDF text extraction |
| `src/classifier.py` | LLM classification with confidence score |
| `src/completeness.py` | Per-patient document completeness check |
| `src/storage.py` | JSON serialisation of results |
| `src/classify.py` | CLI entry-point / pipeline orchestrator |

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key |
| `CONFIDENCE_THRESHOLD` | Min confidence to accept a classification (default 0.80) |
