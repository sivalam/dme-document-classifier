# PROJECT_CONTEXT — ashvin-doc-classifier

## Project Goal

Build a production-oriented Python pipeline that classifies DME medical PDFs, stores results, and checks whether each patient file is complete enough for workflow processing.

The assignment asks for code that:
1. Classifies all documents in a folder.
2. Stores the classification in a file.

This implementation intentionally goes beyond the minimum to show senior-level reasoning around ambiguous startup requirements, machine learning tradeoffs, auditability, extensibility, and production evolution.

## Business Context

DME providers receive mixed batches of PDFs from faxes, emails, portals, and manual uploads. Coordinators must identify document types and determine whether the patient packet is complete before workflow, insurance, delivery, and billing can proceed.

The core business question is not only:

> What type is this document?

It is also:

> Can this patient workflow start, and what is missing?

## Current Architecture

Pipeline flow:

```text
documents/
  → extractor.py
  → classifier.py
  → completeness.py
  → storage.py
  → output/
```

## Implemented Modules

- `extractor.py`: reads local PDF files and returns raw bytes, filename, and page count.
- `classifier.py`: sends raw PDF bytes to GPT-4o-mini and returns document type, confidence, reasoning, review flag, and audit metadata.
- `database.py`: owns SQLite schema and database-backed taxonomy.
- `completeness.py`: groups classifications by patient and checks required document completeness.

## Not Yet Implemented

- `storage.py`
- `classify.py`
- JSON output writer
- CSV output writer
- SQLite persistence for results
- CLI orchestration
- End-to-end run over the full document folder