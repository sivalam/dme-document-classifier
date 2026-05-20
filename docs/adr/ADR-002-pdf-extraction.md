# ADR-002: PDF Processing Strategy

**Status:** Accepted  
**Date:** 2026-05  
**Deciders:** Engineering Lead    
**Decision:** Option 3 — Direct PDF ingestion through OpenAI Files API + Responses API

---

## Context

The document corpus contains a mix of:
- machine-generated digital PDFs
- scanned image PDFs
- faxed medical forms
- handwritten prescriptions
- low-quality provider documents

This reflects real DME operational workflows. Physicians still use paper prescription pads. Orders arrive by fax. Physician notes are frequently scanned. Document quality varies significantly between providers.

A text-only extraction strategy is insufficient — many documents contain little or no reliably extractable text. The system needs to handle both digital and image-heavy content without requiring separate processing pipelines for each.

---

## Options Comparison

| | Option 1: Extract Then Classify | Option 2: OCR Everything First | Option 3: Direct PDF via Files API ✅ |
|---|---|---|---|
| **How it works** | Detect PDF type → extract text (pdfplumber) or render to image (pillow) → send to LLM | Run all PDFs through OCR service (Textract, Tesseract) → extract text → send to any LLM | Upload PDF via OpenAI Files API, reference via Responses API. Model handles text and scanned content natively |
| **Code complexity** | High — two extraction paths, auto-detection logic | Medium — one path but external service dependency | Low — no extraction layer needed |
| **Dependencies** | openai, pdfplumber, pillow | openai + OCR service (Tesseract or AWS Textract) | openai only |
| **Handwriting support** | Poor — Tesseract struggles with handwritten Rx pads | Poor — same OCR limitation | Good — model vision handles handwriting natively |
| **Cost at low volume** | Low | Low–Medium (Textract charges per page) | Low |
| **Cost at high volume** | Lowest — text tokens cheaper than images | Low with Tesseract, higher with Textract | Higher — model processes full PDF each time |
| **Model flexibility** | Works with any LLM | Works with any LLM | Requires Files API + Responses API support |
| **Pipeline coupling** | Decoupled — swap models freely | Decoupled — swap models freely | Coupled to OpenAI Files API + Responses API |
| **Visibility** | Full — log exactly what was extracted | Full — extracted text is auditable | Limited — extraction happens inside the model |
| **Local setup friction** | High — extra installs required | High — OCR service setup | Low — one SDK, one API key |
| **HIPAA path** | Works with self-hosted models | Works with self-hosted models | Requires OpenAI BAA or switch to self-hosted + Option 1 |
| **API contract validation** | Testable without live API | Testable without live API | Must be validated with a real file before building around it |

---

## Decision

**Option 3 — Direct PDF ingestion via OpenAI Files API + Responses API.**

For V1, simplicity wins. No extraction layer, no additional dependencies, and the model handles the full range of document quality natively — digital text, scanned images, handwritten content, and faxed forms.

---

## Important: API Contract Validation Finding

During end-to-end testing, the initial implementation attempted to send PDFs via the `image_url` path inside `chat.completions`. This failed:

```
Error: Invalid MIME type. Only image types are supported.
```

The `image_url` field accepts image MIME types — not `application/pdf`. This was only discovered during full pipeline execution, after the architecture had been built around that assumption.

The correct approach is:
1. Upload the PDF using the OpenAI Files API
2. Reference the uploaded file ID in a Responses API call
3. File cleanup should be added in production to avoid unnecessary accumulation and storage costs.

**Key lesson:** External AI API contracts should be validated with a real isolated spike before building architecture around assumed behavior. Both pipeline runs are preserved in the SQLite audit trail — the first showing the failed attempt, the second showing the corrected flow.

---

## Trade-offs Accepted

| Trade-off | Mitigation |
|---|---|
| Coupled to OpenAI Files API + Responses API | Extractor module is isolated — if API changes, only extractor/classifier boundary needs updating |
| Slightly higher cost than text-only | Negligible at this scale. Revisit above 10K docs/month |
| Limited visibility into what the model extracted | Acceptable for classification. V2 structured extraction may require more control |
| Must validate API contract before building | Isolated spike test documented in scratch/test_pdf_api.py |

---

## When to Revisit

| Trigger | Switch To |
|---|---|
| Need to run on a model without Files API support | Option 1 — add dual-path extraction |
| Volume > 10,000 docs/month, cost pressure | Option 2 — dedicated OCR + text-only model |
| Need full text audit trail of what was extracted | Option 1 — log extracted text per document |
| HIPAA requirement, no cloud BAA available | Self-hosted model + Option 1 or Option 2 |
| OpenAI changes or deprecates Files API + Responses API | Option 1 or Option 2 |