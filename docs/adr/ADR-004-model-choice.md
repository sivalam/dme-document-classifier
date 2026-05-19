# ADR-004: Model Choice

**Status:** Accepted  
**Date:** 2024-11  
**Deciders:** Engineering Lead  
**Decision:** GPT-4o-mini

---

## Context

We need to select an LLM for document classification. Given our PDF processing decision (ADR-002), the model must support native PDF input — this is not optional. Our documents contain a mix of digital text and scanned images, so the model must handle both content types from a single PDF file.

Additional requirements: reliable structured JSON output, strong medical document understanding, and accessible via API without significant setup overhead.

---

## Options Comparison

| | GPT-4o (OpenAI) | GPT-4o-mini (OpenAI) ✅ | Claude Sonnet (Anthropic) | Llama 3 via Ollama |
|---|---|---|---|---|
| **Native PDF input** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No — requires extraction pipeline |
| **Handles text + scanned images in one PDF** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Limited in smaller variants |
| **JSON output reliability** | ✅ Strong | ✅ Good with explicit instructions | ✅ Excellent | ⚠️ Needs more prompt engineering |
| **Medical document understanding** | ✅ Strong | ✅ Sufficient for classification | ✅ Strong | ⚠️ Weaker on specialised forms |
| **Cost per 1M input tokens** | ~$5 | ~$0.15 | ~$3 | Free after hardware |
| **Latency** | Fast | Fast | Fast | Depends on hardware |
| **API setup** | Simple | Simple | Simple | Requires GPU + model download |
| **HIPAA BAA available** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Data never leaves machine |
| **Pipeline coupling** | Coupled to PDF-capable model | Coupled to PDF-capable model | Coupled to PDF-capable model | Decoupled — but needs extraction layer |
| **Best suited for** | Complex reasoning tasks | Routine classification at low cost | High accuracy structured output | Air-gapped / HIPAA-strict environments |

---

## Decision

**GPT-4o-mini.**

It meets the core requirement — native PDF input with mixed content support. For a classification task with a well-defined taxonomy, GPT-4o-mini performs comparably to full GPT-4o at a fraction of the cost. The API key was already available which reduced setup friction for this exercise.

---

## Trade-offs Accepted

| Trade-off | Mitigation |
|---|---|
| Pipeline coupled to PDF-capable models | Extractor module is isolated — adding an extraction layer later is a contained change |
| Slightly higher cost than text-only model | Negligible at this scale. Revisit above 10K docs/month |
| Less control over internal extraction | Acceptable for classification. For structured data extraction (V2), we may need more control |
| OpenAI dependency | Provider abstracted in classifier.py — can swap to Claude or self-hosted |

---

## When to Revisit

| Trigger | Action |
|---|---|
| Need HIPAA compliance without a cloud BAA | Switch to Llama 3 via Ollama + add extraction pipeline (ADR-002 Option 1) |
| GPT-4o-mini accuracy insufficient for a doc type | Upgrade to GPT-4o or add few-shot examples to prompt |
| Cost becomes a concern at scale | Evaluate fine-tuned smaller model or OCR + text-only model |
| Want to remove OpenAI dependency | Switch to Claude Sonnet — minimal code change via provider abstraction |
| OpenAI removes PDF input support | Add extraction pipeline (ADR-002 Option 1) |