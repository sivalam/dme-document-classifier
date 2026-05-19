# PRD: DME Document Intelligence — Intake & Classification

**Status:** Draft  
**Author:** Sivalam  
**Last Updated:** May 19, 2026

---

## 1. Background & Context

### The Business

This platform automates the workflow for DME (Durable Medical Equipment) providers — companies that supply patients with equipment like CPAP machines, wheelchairs, and oxygen concentrators. The end-to-end workflow spans:

```
Prescription received
       ↓
Supporting documents gathered (Sleep Study, Physician Notes)
       ↓
Insurance prior authorization
       ↓
Order created and signed
       ↓
Equipment delivered (Delivery Ticket)
       ↓
Compliance verified → Billing triggered
```

Today, much of this process is manual. Coordinators receive faxes, emails, and portal uploads — often a dump of unsorted PDFs — and must manually identify, sort, and route each document to the right step in the workflow.

### The Problem

**Document intake is the bottleneck at the start of every patient workflow.**

When a DME provider receives a new patient referral, they typically receive a batch of PDFs with no consistent naming, structure, or format. Before any workflow automation can begin, someone must answer:

- What documents did we receive?
- What type is each one?
- Do we have everything we need to proceed?
- What is missing, and who do we chase to get it?

This is currently done by hand. It is slow, error-prone, and does not scale.

**Every day a coordinator spends sorting documents is a day the patient waits for equipment and the DME provider waits for payment.**

---

## 2. Problem Statement

> DME providers cannot efficiently begin patient workflows because incoming document batches are unstructured, mixed-format, and incomplete — requiring manual triage that delays care and revenue.

---

## 3. Goals

| Goal | Success Metric |
|---|---|
| Automatically classify all incoming documents by type | ≥ 95% classification accuracy |
| Detect incomplete patient files at intake | 100% recall on missing document detection |
| Produce machine-readable output for downstream workflow routing | Valid JSON output for every processed document |
| Handle real-world document quality (scanned, faxed, handwritten) | Zero failures on image-based PDFs |
| Surface exceptions for human review | Low-confidence classifications flagged, not silently passed |

---

## 4. Out of Scope (V1)

- Extracting structured data fields from documents (V2)
- Routing documents to downstream workflow agents (V2)
- A user-facing UI for coordinators (V2)
- Real-time / streaming processing (V1 is batch)
- Training or fine-tuning a custom model (deliberate — see ADR-001)

---

## 5. Jobs To Be Done

### JOB 1 — Classify Incoming Documents *(Core)*
**When** a batch of PDFs arrives for a new patient,  
**I want** the system to identify the type of each document,  
**So that** the workflow knows what it is working with and can route accordingly.

**Acceptance criteria:**
- Each document assigned one of 6 known types: `Prescription`, `Physician Notes`, `Sleep Study Report`, `Compliance Report`, `Order`, `Delivery Ticket`
- Unknown document types classified as `Unknown` and flagged
- Confidence score accompanies every classification
- Classifications below confidence threshold routed to human review

---

### JOB 2 — Detect Patient File Completeness *(High Value)*
**When** a patient's documents have been classified,  
**I want** the system to check whether the required document set is complete,  
**So that** coordinators are immediately alerted to missing documents rather than discovering gaps days later.

**Acceptance criteria:**
- Each patient evaluated against the required document checklist
- Missing documents listed explicitly
- Status is one of: `complete`, `incomplete`, `cannot_start` (missing Prescription)
- Output groups results by patient

**Required document set for a complete CPAP patient file:**
1. Prescription
2. Sleep Study Report
3. Physician Notes
4. Order
5. Compliance Report
6. Delivery Ticket

---

### JOB 3 — Produce Integration-Ready Output *(Required)*
**When** classification is complete,  
**I want** results stored in a structured, machine-readable format,  
**So that** downstream systems can consume them without additional parsing.

**Acceptance criteria:**
- JSON output with defined schema
- CSV output for human spot-checking
- SQLite database for persistence, audit trail, and analytics
- All outputs written atomically

---

### JOB 4 — Handle Document Quality Gracefully *(Real-World Requirement)*
**When** a document is a scanned image, fax, or photograph,  
**I want** the system to still classify it correctly,  
**So that** the pipeline does not silently fail on the majority of real-world inputs.

**Acceptance criteria:**
- System auto-detects whether a PDF is text-extractable or image-based
- Image-based PDFs rendered and sent to the LLM vision API
- No manual intervention required for either document type
- Processing strategy logged per document

---

### JOB 5 — Audit Every Decision *(Compliance & Trust)*
**When** a classification decision is made,  
**I want** the reasoning, confidence, model version, and timestamp logged,  
**So that** we can debug errors, track accuracy over time, and meet compliance requirements.

**Acceptance criteria:**
- Every record includes: filename, document_type, confidence, reasoning, model, timestamp, extraction_method
- Failed classifications logged with error detail
- Correction events schema-defined for future implementation

---

## 6. User Personas

**DME Intake Coordinator**
Receives document batches, currently sorts manually. Benefits from automated classification and completeness alerts. Primary consumer of CSV output and exception queue.

**DME Workflow System**
Downstream automation platform. Consumes JSON output to trigger the right workflow step. Needs schema stability and reliable classification.

**DME Operations Manager**
Monitors intake throughput, error rates, and document patterns. Benefits from SQLite analytics over time.

**Engineering Team**
Maintains, debugs, and improves the pipeline. Benefits from audit logs, confidence scores, and ADR documentation.

---

## 7. Constraints

- **Data sensitivity:** Documents contain PHI. In production, all processing must be HIPAA-compliant. For this exercise, documents have been de-identified.
- **Document quality:** Real-world inputs include handwritten prescriptions, faxed forms, scanned paper.
- **Scale (V1):** Designed for batch processing of tens to low hundreds of documents.
- **Cost:** LLM API calls have per-token cost. Strategy should minimize unnecessary calls.

---

## 8. Future Roadmap

- **V2 — Structured extraction agents:** Once classified, each document type routes to a specialized agent that extracts key fields (ICD-10 codes, AHI scores, HCPCS codes, compliance percentages)
- **V3 — Real-time service:** Replace batch script with async queue-based service
- **V4 — Feedback loop:** Human corrections feed back into prompt improvement and eventual fine-tuning
- **V5 — Prior auth automation:** Submit to insurance payers based on extracted clinical data