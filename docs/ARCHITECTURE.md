# Architecture: DME Document Intelligence Pipeline

**Version:** 1.0  
**Status:** Current

---

## System Overview

The pipeline takes a folder of medical PDFs and produces structured, machine-readable classification results. Designed as a batch processor for V1 with a clear path to a real-time service.

```
┌─────────────────────────────────────────────────────────────────┐
│                     INPUT: PDF Folder                           │
│         (21 documents — mix of digital and scanned)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  extractor.py                                   │
│                                                                 │
│   Reads each PDF as raw bytes                                   │
│   No text extraction — model handles that internally            │
│   Returns: filename, raw bytes, page count                      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  classifier.py                                  │
│                                                                 │
│   Sends raw PDF bytes to GPT-4o-mini                            │
│   Model handles text + scanned image content natively           │
│   Prompt: taxonomy, output schema, disambiguation guidance      │
│   Returns: { document_type, confidence, reasoning }             │
│                                                                 │
│   confidence < 0.80 → requires_review = true                    │
│   type not in taxonomy → classified as "Unknown"                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                completeness.py                                  │
│                                                                 │
│   Groups documents by patient_id (parsed from filename)         │
│   Checks each patient against required 6-document set           │
│   Emits: complete | incomplete | cannot_start                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   storage.py                                    │
│                                                                 │
│   ├── classifications.json   (primary — pipeline integration)   │
│   ├── classifications.csv    (human verification)               │
│   └── classifications.db     (SQLite — audit + analytics)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Decision: Direct PDF Input

The documents in this corpus are a mix of digital PDFs (text-extractable) and scanned image PDFs (photographs, faxes). 57% are scanned with zero extractable text.

Rather than building a custom extraction pipeline to handle both types, we send the raw PDF directly to GPT-4o-mini. The model natively processes both text content and embedded images and handles the extraction internally.

**Why this matters:** This corpus includes handwritten prescriptions, faxed orders, and scanned physician notes. A text-only approach fails on the majority of documents. A vision-only approach works but costs more. Sending the PDF directly lets the model decide how to read each page — simpler code, same accuracy.

**The trade-off:** This couples the pipeline to models that support direct PDF input. If we switch to a model without this capability we need to add an extraction layer. The extractor module is isolated so that change stays contained to one file.

See ADR-002 for full options comparison. See ADR-004 for model selection rationale.

---

## Module Responsibilities

### `classify.py` — Entrypoint
- Parses CLI arguments (`--input`, `--output`, `--threshold`)
- Orchestrates the pipeline: extract → classify → completeness → store
- Handles top-level errors and exit codes
- Prints a run summary on completion

### `extractor.py` — PDF Reader
- `extract(filepath) → ExtractedContent`
- Reads the PDF as raw bytes
- Returns filename, bytes, and page count
- Intentionally simple — no extraction logic here
- If we need to add a text/vision extraction path later, this is the only file that changes

### `classifier.py` — LLM Classification
- `classify(content: ExtractedContent) → ClassificationResult`
- Sends PDF bytes to GPT-4o-mini with classification prompt
- Parses structured JSON response
- Retries once on malformed response, then marks as Unknown
- Temperature = 0 for consistent output

### `completeness.py` — Patient File Check
- `check_completeness(classifications) → Dict[str, PatientStatus]`
- Pure function — no API calls, fully deterministic
- Groups by patient_id parsed from filename
- Returns status and missing document list per patient
- Easiest module to unit test

### `storage.py` — Output Writing
- `write_all(results, output_dir)`
- Writes JSON, CSV, and SQLite in a single pass
- Appends to existing DB with new run_id — never overwrites history

---

## Data Models

### ClassificationResult

```python
@dataclass
class ClassificationResult:
    filename: str
    document_type: str       # One of 6 known types or "Unknown"
    confidence: float        # 0.0 - 1.0
    patient_id: str          # Parsed from filename ("1", "2", etc.)
    reasoning: str           # LLM explanation
    requires_review: bool    # True if confidence < threshold or Unknown
    model: str               # Exact model version used
    processed_at: str        # ISO 8601 timestamp
    pages_processed: int
```

### PatientStatus

```python
@dataclass
class PatientStatus:
    patient_id: str
    status: str                  # "complete" | "incomplete" | "cannot_start"
    documents_found: List[str]
    documents_missing: List[str]
    can_start_workflow: bool     # False if Prescription is missing
```

---

## Document Taxonomy

| Type | Key Identifiers |
|---|---|
| `Prescription` | Rx symbol, DEA number, physician signature, device ordered |
| `Sleep Study Report` | AHI score, sleep stages, diagnostic findings |
| `Physician Notes` | SOAP format, diagnosis, clinical narrative |
| `Compliance Report` | Usage hours, compliance percentage, date range |
| `Order` | HCPCS codes, equipment list, physician signature |
| `Delivery Ticket` | Delivery date, patient signature, serial numbers |
| `Unknown` | Does not match any known type — route to human review |

---

## Error Handling

| Scenario | Behavior |
|---|---|
| PDF cannot be opened | Log error, add to exceptions, continue processing |
| LLM returns malformed JSON | Retry once; if still fails mark as Unknown with requires_review=true |
| LLM API timeout | Retry with exponential backoff — 3 attempts |
| Confidence below threshold | Set requires_review=true; result still written to output |
| Unknown document type | Written to exceptions block in JSON output |
| Missing patient documents | Surfaced in patients completeness block — not an error |

---

## Output JSON Schema

```json
{
  "run_id": "2024-11-16T10:30:00Z",
  "model": "gpt-4o-mini",
  "total_documents": 21,
  "documents": [
    {
      "filename": "Prescription 1.pdf",
      "document_type": "Prescription",
      "confidence": 0.97,
      "patient_id": "1",
      "reasoning": "Document shows Rx letterhead, DEA number, handwritten device instructions, and physician signature.",
      "requires_review": false,
      "processed_at": "2024-11-16T10:30:05Z",
      "pages_processed": 1
    }
  ],
  "patients": {
    "1": {
      "status": "incomplete",
      "documents_found": ["Prescription", "Sleep Study Report", "Physician Notes", "Order", "Delivery Ticket"],
      "documents_missing": ["Compliance Report"],
      "can_start_workflow": true
    },
    "2": {
      "status": "complete",
      "documents_found": ["Prescription", "Sleep Study Report", "Physician Notes", "Compliance Report", "Order", "Delivery Ticket"],
      "documents_missing": [],
      "can_start_workflow": true
    }
  },
  "exceptions": []
}
```

---

## Evolution Roadmap

### V2: Structured Extraction Agents
Classification unlocks the next step — extracting structured data fields from each document type. Once we know what a document is, a specialized agent pulls the relevant fields:

```
Classification → Document Type → Specialized Agent
                                        │
                 ┌──────────────────────┼──────────────────┐
                 ▼                      ▼                   ▼
          Prescription Agent       Order Agent       Compliance Agent
          ─────────────────        ───────────       ───────────────
          - Device ordered          - HCPCS codes     - Usage hours
          - Diagnosis code          - ICD-10 codes    - Compliance %
          - Date issued             - Physician NPI   - Payor
```

### V3: Real-Time Service
```
Document Upload (S3/GCS)
      → Event (SNS/Pub-Sub)
      → Classification Service (FastAPI)
      → Results (Postgres + event to workflow engine)
```

### V4: Feedback Loop
Human corrections logged to corrections table (schema defined in V1). Patterns inform prompt improvements. At sufficient volume, corrections become fine-tuning examples.

### V5: Confidence-Driven Routing
```
Classification result
      ├── confidence ≥ 0.90 → auto-route
      ├── confidence 0.70–0.90 → coordinator review queue
      └── confidence < 0.70 → hold for manual classification
```

---

## Production Readiness Checklist

Not built in V1 but required before production:

| Concern | Approach |
|---|---|
| HIPAA compliance | OpenAI BAA or switch to self-hosted model + extraction pipeline |
| PII redaction | AWS Comprehend Medical or Microsoft Presidio before LLM call |
| Model version pinning | Pin exact version string — never use "latest" in production |
| Observability | Log model, token count, latency, confidence per call |
| Cost tracking | Alert when cost per document exceeds threshold |
| Prompt versioning | Prompts in source control, regression tested on every change |
| Parallelism | Async processing with queue for > 100 docs/run |
| CI/CD | Eval run on every PR — fail build if accuracy drops |
| PDF support dependency | If model loses PDF input support, add extraction layer (ADR-002 Option 1) |