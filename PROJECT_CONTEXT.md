# PROJECT_CONTEXT — dme-document-classifier

## Project Goal

Build a production-oriented Python pipeline that classifies DME medical PDFs, stores results, and checks whether each patient file is complete enough for workflow processing.

The assignment asks for code that:
1. Classifies all documents in a folder.
2. Stores the classification in a file.

This implementation intentionally goes beyond the minimum to demonstrate:
- operational workflow thinking
- AI integration reasoning
- auditability
- extensibility
- production-oriented architecture
- handling ambiguity in underspecified startup requirements

---

## Business Context

DME providers receive mixed batches of PDFs from:
- faxes
- emails
- provider portals
- manual uploads

Coordinators must identify document types and determine whether a patient packet is complete before:
- insurance processing
- equipment delivery
- billing
- compliance workflows

The core business question is not only:

> What type is this document?

It is also:

> Can this patient workflow start, and what is missing?

This led the system to evolve beyond document classification into:
- patient-level completeness checking
- workflow readiness evaluation
- review flagging
- operational outputs

---

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

---

## Implemented Modules

### `extractor.py`

Responsibilities:
- reads local PDF files
- returns:
  - raw PDF bytes
  - filename
  - page count

Design notes:
- extraction boundary intentionally isolated
- future migration to:
  - S3
  - blob storage
  - queue ingestion
  requires changes only at extractor boundary

---

### `classifier.py`

Responsibilities:
- uploads PDFs through OpenAI Files API
- classifies documents using GPT-4o-mini + Responses API
- returns structured classification results

Current classification output:
- document type
- confidence
- patient id
- reasoning
- requires_review
- model metadata
- processing metadata

Design notes:
- taxonomy generated dynamically from database
- Unknown supported intentionally
- graceful degradation on failures
- review queue treated as part of workflow design

---

### `database.py`

Responsibilities:
- owns SQLite schema
- stores taxonomy configuration
- seeds workflow definitions

Current schema includes:
- equipment types
- document types
- classifications
- completeness results
- corrections

Design notes:
- business rules intentionally separated from prompts/code
- taxonomy/configuration should evolve independently from classifier implementation

---

### `completeness.py`

Responsibilities:
- groups documents by patient
- determines missing required documents
- evaluates workflow readiness

Design notes:
- workflow rules intentionally deterministic
- required document logic stays outside LLM prompts
- completeness requirements loaded dynamically from database

---

### `storage.py`

Responsibilities:
- writes:
  - JSON output
  - CSV output
  - SQLite persistence

Design notes:
- JSON optimized for integrations
- CSV optimized for human review
- SQLite acts as audit/history layer

---

### `classify.py`

Responsibilities:
- CLI orchestration layer
- batch processing
- pipeline coordination

Pipeline flow:
- extract
- classify
- completeness
- persist outputs

Design notes:
- batch continues even if individual documents fail
- small delay added between documents to reduce OpenAI rate-limit pressure
- orchestration intentionally kept simple for V1 clarity

---

## Key Decisions

- Use LLM classification instead of traditional ML because the provided dataset is too small for supervised training
- Use direct PDF ingestion through OpenAI Files API + Responses API instead of building OCR infrastructure in V1
- Store taxonomy and workflow rules in SQLite instead of hardcoded constants
- Keep deterministic workflow/completeness logic outside AI prompts
- Support Unknown + requires_review instead of forcing hard classifications
- JSON for systems, CSV for humans, SQLite for audit/history

Detailed rationale lives in:
- `docs/adr/`
- `docs/AI_OBSERVATIONS.md`

---

## Current Status

Implemented:
- PDF extraction
- OpenAI PDF classification
- database-backed taxonomy
- patient completeness checks
- JSON output
- CSV output
- SQLite persistence
- CLI orchestration
- graceful failure handling
- review flagging
- unit tests

Current test status:

```text
42 tests passing
```

Validated:
- end-to-end pipeline execution against the provided DME PDF dataset
- OpenAI Files API + Responses API PDF ingestion
- persistence to JSON, CSV, and SQLite
- patient completeness evaluation
- graceful handling of rate limits and classification failures

---

## Latest Validation Findings

End-to-end execution against 21 sample DME PDFs surfaced several important operational findings:

- direct PDF ingestion worked successfully through OpenAI Files API + Responses API
- sequential batch processing hit OpenAI TPM rate limits during larger document processing
- failed classifications degraded gracefully to:
  - `Unknown`
  - `requires_review=True`
- one document labeled `Prescription 2.pdf` was classified as `Order` because the document content itself strongly resembled an order form
- intentionally incomplete patient files reinforced the importance of completeness checking beyond document classification

Key implementation insight:

> AI integration contracts should be validated early with isolated real-world spikes before building architecture around assumed API behavior.

---

## Current Known Limitations

Current implementation intentionally keeps infrastructure simple.

Not yet implemented:
- OCR fallback pipeline
- async processing
- queue-based throttling
- production retry scheduling
- human review UI
- document deduplication
- PHI redaction workflows

The current system is intentionally optimized for:
- clarity
- modularity
- operational reasoning
- explainability
- iterative evolution

---

## Repository Navigation

Primary entry points:

- `README.md`
  - setup
  - run instructions
  - output review

- `docs/ARCHITECTURE.md`
  - architecture and module responsibilities

- `docs/AI_OBSERVATIONS.md`
  - implementation findings
  - AI integration learnings
  - debugging observations
  - operational tradeoffs

- `docs/adr/`
  - focused engineering decisions and tradeoffs

---

## Working Style

Keep implementation:
- incremental
- production-oriented
- testable
- understandable by another engineer/model

Avoid unnecessary frameworks or overengineering unless they clearly improve the next stage of the system.