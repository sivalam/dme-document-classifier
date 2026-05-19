# ADR-001: Classification Approach — LLM vs Traditional ML

**Status:** Accepted  
**Date:** 2024-11  
**Deciders:** Engineering Lead  
**Decision:** Option 3 — LLM with zero-shot prompting

---

## Context

We need to classify 22 medical PDF documents into 6 known categories. The corpus is small, documents vary significantly in format and quality, and there is no existing labeled training dataset. We need to choose a classification approach.

---

## Options Comparison

| | Option 1: Classical ML (TF-IDF + SVM / BERT) | Option 2: Rules-Based / Keyword Matching | Option 3: LLM Zero-Shot Prompting ✅ |
|---|---|---|---|
| **How it works** | Extract text features, train a classifier on labeled examples | Define keyword rules per document type, match against extracted text | Send document content to LLM with taxonomy description, receive classification |
| **Training data required** | Yes — hundreds of labeled examples minimum | No | No |
| **Works with 22 documents** | No — far too few for reliable training | Yes | Yes |
| **Handles scanned/image docs** | No — requires clean text input | No — requires clean text input | Yes — vision-capable LLMs handle images natively |
| **Handles handwritten content** | No | No | Yes |
| **Setup time** | Weeks — data collection, labeling, training, evaluation | Hours — but brittle | Hours |
| **Accuracy on ambiguous docs** | Low without sufficient training data | Low — breaks on format variations | High — understands semantic context |
| **Explainability** | Limited | High — rules are readable | High — model returns reasoning with classification |
| **Maintenance** | Retrain when document formats change | Update rules manually | Update prompt |
| **Cost** | High upfront (engineering time) | Low | Per-call API cost |
| **Latency** | Fast at inference | Very fast | API round-trip per document |

---

## Decision

**Option 3 — LLM with zero-shot prompting.**

Classical ML requires training data we do not have. Rules-based matching breaks on the document variety in this corpus — especially scanned and handwritten documents. The LLM approach requires no training data, handles all document types including scanned images, and can explain its reasoning. For 22 documents at a startup moving fast, this is the right call.

---

## Trade-offs Accepted

| Trade-off | Mitigation |
|---|---|
| Per-call API cost | Negligible at this scale — under $0.05 for all 21 documents |
| Non-determinism across model versions | Pin exact model version, run regression tests on upgrade |
| External API dependency | Abstract provider behind interface — swap if needed |
| Context window limits on large docs | Send first page only for classification — type is always apparent from header |
| PHI sent to external API | Documents de-identified for this exercise. Production requires OpenAI BAA or self-hosted model |

---

## When to Revisit

| Trigger | Switch To |
|---|---|
| Volume > 10,000 docs/month, cost sensitivity | Fine-tuned smaller model hosted internally |
| Latency requirement < 500ms synchronous | Locally hosted model via Ollama |
| HIPAA requirement, no cloud BAA | Self-hosted open source model (Llama 3 via Ollama) |
| Accuracy on a specific doc type falls below threshold | Add few-shot examples to prompt first; fine-tune if that fails |