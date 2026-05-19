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
classify.py
  → extractor.py
  → classifier.py
  → completeness.py
  → storage.py
  → output/
```

## Implemented Modules

- `extractor.py`
  - Reads local PDF files
  - Returns raw bytes, filename, and page count
  - Designed so future S3 migration only changes extractor boundary

- `classifier.py`
  - Sends raw PDF bytes directly to GPT-4o-mini
  - Returns structured classification result:
    - document type
    - confidence
    - patient id
    - reasoning
    - review flag
    - audit metadata
  - Uses database-backed taxonomy instead of hardcoded document types

- `database.py`
  - Owns SQLite schema and taxonomy configuration
  - Stores:
    - equipment types
    - document types
    - classifications
    - patient completeness
    - corrections
  - Seeds CPAP document taxonomy

- `completeness.py`
  - Groups documents by patient
  - Determines missing required documents
  - Keeps workflow/business rules outside the LLM
  - Reads required document types from database

- `storage.py`
  - Writes:
    - JSON output
    - CSV output
    - SQLite persistence
  - SQLite acts as audit/history layer

- `classify.py`
  - CLI orchestration layer
  - Runs:
    - extract
    - classify
    - completeness
    - storage
  - Continues processing batch even if one document fails

## Key Decisions

- Use LLM classification instead of traditional ML because dataset is too small for supervised training
- Send PDFs directly to multimodal model instead of building OCR pipeline in V1
- Keep taxonomy and workflow rules in SQLite instead of hardcoded constants
- Keep deterministic workflow/completeness logic outside AI prompts
- JSON output for systems, CSV for humans, SQLite for audit/history

Detailed rationale lives in ADRs.

## Current Status

Implemented:
- extraction
- classification
- taxonomy database
- completeness checks
- persistence
- CLI orchestration
- unit tests

Current test status:

```text
41 tests passing
```

Not yet done:
- run against actual provided PDF dataset
- inspect generated outputs
- analyze classification quality
- capture AI behavior observations
- prepare final presentation/demo

## Next Step

Run the pipeline end-to-end on the real documents and evaluate:
- classification accuracy
- low-confidence classifications
- unknown document handling
- completeness results
- model confusion patterns
- usefulness of reasoning field

Then update:
- `AI_OBSERVATIONS.md`
- final presentation/demo notes

## Working Style

Keep implementation:
- incremental
- production-oriented
- testable
- easy for another engineer/model to continue

Avoid unnecessary frameworks or overengineering unless they clearly improve the next stage of the system.