# ADR-002: PDF Processing Strategy

**Status:** Accepted  
**Date:** 2024-11  
**Deciders:** Engineering Lead  
**Decision:** Option 3 — Send PDF directly to a multimodal model

---

## Context

The document corpus contains two types of PDFs discovered during initial analysis:

- **Digital PDFs (43%)** — machine-generated, text is directly extractable. Examples: Compliance Reports, Delivery Tickets.
- **Scanned/Image PDFs (57%)** — faxed or photographed documents embedded as images, zero extractable text. Examples: Prescriptions, Orders, Physician Notes.

This is not an edge case. It reflects how medical documents actually arrive in DME workflows. Physicians use paper Rx pads. Orders come by fax. Any processing strategy must handle both reliably.

---

## Options Comparison

| | Option 1: Extract Then Classify | Option 2: OCR Everything First | Option 3: Direct PDF to Multimodal Model ✅ |
|---|---|---|---|
| **How it works** | Detect PDF type → extract text (pdfplumber) or render to image (pillow) → send to LLM | Run all PDFs through OCR service (Textract, Tesseract) → extract text → send to any LLM | Send raw PDF bytes directly to GPT-4o-mini. Model handles text and images internally |
| **Code complexity** | High — two extraction paths, auto-detection logic | Medium — one OCR path but external service dependency | Low — no extraction layer needed |
| **Dependencies** | openai, pdfplumber, pillow | openai + OCR service (Tesseract or AWS Textract) | openai only |
| **Handwriting support** | Poor — Tesseract struggles with handwritten Rx pads | Poor — same OCR limitation | Good — model vision handles handwriting natively |
| **Cost at low volume** | Low | Low–Medium (Textract charges per page) | Low |
| **Cost at high volume** | Lowest — text tokens cheaper than images | Low with Tesseract, higher with Textract | Higher — model processes full PDF each time |
| **Model flexibility** | Works with any LLM | Works with any LLM | Requires a model with native PDF support |
| **Pipeline coupling** | Decoupled — swap models freely | Decoupled — swap models freely | Coupled — pipeline breaks if model loses PDF support |
| **Visibility** | Full — log exactly what was extracted | Full — extracted text is auditable | Limited — extraction happens inside the model |
| **Local setup friction** | High — extra installs required | High — OCR service setup | Low — one SDK, one API key |
| **HIPAA path** | Works with self-hosted models | Works with self-hosted models | Requires OpenAI BAA or switch to self-hosted + Option 1 |

---

## Decision

**Option 3 — Send PDF directly to GPT-4o-mini.**

For V1, simplicity wins. Fewer dependencies, less code, easier for anyone to run locally, and the model handles the mixed document reality natively. The handwriting problem (prescriptions, orders) is solved without any custom OCR logic.

---

## Trade-offs Accepted

The main trade-off is coupling. This pipeline depends on using a model that accepts PDF input natively. If we switch to a model without that capability we need to add an extraction layer first.

This is a conscious decision, not an oversight. The extractor module is isolated behind a clean interface so if we need to add extraction later the change stays in one place and nothing else breaks.

---

## When to Revisit

| Trigger | Switch To |
|---|---|
| Need to run on a model without PDF support | Option 1 — add dual-path extraction |
| Volume > 10,000 docs/month, cost pressure | Option 2 — dedicated OCR + text-only model |
| Need full text audit trail of extracted content | Option 1 — log extracted text per document |
| HIPAA requirement, no cloud BAA available | Self-hosted model + Option 1 or Option 2 |
| Handwriting accuracy becomes a quality issue | Dedicated handwriting OCR → Option 1 or Option 2 |