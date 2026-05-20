# ADR-004: Model Choice

**Status:** Accepted  
**Date:** 2026-05  
**Approvers:** Engineering Lead  
**Decision:** GPT-4o-mini

---

## Context

We need to select an LLM for document classification. Given our PDF processing decision (ADR-002), the model must support native PDF input via the Files API and Responses API — this is not optional. Our documents contain a mix of digital text and scanned images, so the model must handle both content types from a single PDF file.

Additional requirements: reliable structured JSON output, strong medical document understanding, and accessible via API without significant setup overhead.

---

## Options Comparison

| | GPT-4o (OpenAI) | GPT-4o-mini (OpenAI) ✅ | Claude Sonnet (Anthropic) | Llama 3 via Ollama |
|---|---|---|---|---|
| **Native PDF input (Files API)** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No — requires extraction pipeline |
| **Handles text + scanned images in one PDF** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Limited in smaller variants |
| **JSON output reliability** | ✅ Strong | ✅ Good with explicit instructions | ✅ Excellent | ⚠️ Needs more prompt engineering |
| **Medical document understanding** | ✅ Strong | ✅ Sufficient for classification | ✅ Strong | ⚠️ Weaker on specialised forms |
| **Cost** | High | Low | Medium | Hardware only |
| **Latency** | Fast | Fast | Fast | Depends on hardware |
| **API setup** | Simple | Simple | Simple | Requires GPU + model download |
| **HIPAA BAA available** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Data never leaves machine |
| **Pipeline coupling** | Coupled to PDF-capable model | Coupled to PDF-capable model | Coupled to PDF-capable model | Decoupled — but needs extraction layer |
| **Best suited for** | Complex reasoning tasks | Routine classification at low cost | High accuracy structured output | Air-gapped / HIPAA-strict environments |

---

## Decision

**GPT-4o-mini.**

GPT-4o-mini provided the best balance of:
- native PDF ingestion support via Files API and Responses API
- acceptable structured output reliability for a well-defined classification task
- low operational overhead for iterative development and testing
- low cost for experimentation and validation
- simple local developer setup with minimal configuration

The selection was not purely about cost. After implementation, the critical factor became API workflow maturity — specifically, reliable support for the Files API upload and Responses API reference flow that the architecture depends on. See the implementation finding below.

---

## Trade-offs Accepted

| Trade-off | Mitigation |
|---|---|
| Pipeline coupled to PDF-capable models | Extractor module is isolated — adding an extraction layer later is a contained change |
| Slightly higher cost than text-only model | Negligible at this scale. Revisit above 10K docs/month |
| Less control over internal extraction | Acceptable for classification. V2 structured extraction may need more control |
| OpenAI dependency | Provider dependency remains reasonably isolated inside classifier.py, reducing future migration complexity |

---

## Important Implementation Finding

Model capability documentation alone was not sufficient to validate integration behavior.

Although GPT-4o-mini supported PDF ingestion, the implementation still required:
- correct Files API upload flow
- Responses API integration
- validation with real PDFs before building architecture around assumed behavior
- operational testing against rate limits and malformed responses

The model choice decision therefore became tightly coupled not just to model quality, but to API workflow maturity and operational reliability. The initial implementation attempted to send PDFs via `chat.completions` image_url — this failed with an invalid MIME type error. The correct Files API + Responses API flow was only confirmed through an isolated spike test.

This is documented in `docs/AI_OBSERVATIONS.md` section 5 and `docs/adr/ADR-002`.

---

## When to Revisit

| Trigger | Action |
|---|---|
| Need HIPAA compliance without a cloud BAA | Switch to Llama 3 via Ollama + add extraction pipeline (ADR-002 Option 1) |
| GPT-4o-mini accuracy insufficient for a doc type | Upgrade to GPT-4o or add few-shot examples to prompt |
| Cost becomes a concern at scale | Evaluate fine-tuned smaller model or OCR + text-only model |
| Want to reduce OpenAI dependency | Switch to Claude Sonnet — changes remain isolated to classifier.py |
| OpenAI changes or deprecates Files API + Responses API | Add extraction pipeline (ADR-002 Option 1) |