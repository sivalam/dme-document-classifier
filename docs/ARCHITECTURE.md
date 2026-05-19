# Architecture — ashvin-doc-classifier

## System Overview

```
documents/
    └── *.pdf
         │
         ▼
    extractor.py
    ┌────────────────────────────┐
    │  pdfplumber (digital PDF)  │  ← text ≥ 50 chars
    │  vision API  (scanned PDF) │  ← text < 50 chars
    └────────────────────────────┘
         │ ExtractionResult
         ▼
    classifier.py  (GPT-4o-mini chat)
         │ ClassificationResult
         ▼
    completeness.py
         │ PatientRecord (with missing_types)
         ▼
    storage.py
         │
    output/
    ├── classifications.json
    └── completeness.json
```

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `extractor.py` | Dual-path text extraction from PDFs |
| `classifier.py` | LLM-based document type classification |
| `completeness.py` | Per-patient completeness check |
| `storage.py` | Serialise results to JSON |
| `classify.py` | CLI orchestrator |

## Key Design Decisions

See `docs/adr/` for Architecture Decision Records.
