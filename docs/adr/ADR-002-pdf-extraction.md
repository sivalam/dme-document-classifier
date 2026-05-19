# ADR-002: Dual-Path PDF Extraction Strategy

**Status:** Accepted

## Context

57 % of documents are scanned image PDFs with no embedded text layer. A single extraction strategy cannot serve both document types.

## Decision

Use `pdfplumber` for digital PDFs. If extracted text is fewer than 50 characters, treat the file as a scanned image and route to the GPT-4o-mini vision API (page images encoded as base64).

## Consequences

**Positive**
- Handles both digital and scanned PDFs without manual triage.
- 50-char threshold is a pragmatic heuristic; adjustable via config.

**Negative**
- Vision path is slower and more expensive than pdfplumber.
- Threshold may misclassify PDFs with very short but valid text content.
