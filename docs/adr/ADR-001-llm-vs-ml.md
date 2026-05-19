# ADR-001: LLM vs Classical ML for Classification

**Status:** Accepted

## Context

Only 22 labelled documents are available. Classical ML (SVM, Naive Bayes, fine-tuned BERT) requires hundreds-to-thousands of labelled examples to generalise reliably.

## Decision

Use a zero-shot/few-shot LLM (GPT-4o-mini) for classification rather than training a classical ML model.

## Consequences

**Positive**
- No labelled training data required.
- Six document types are semantically distinct; GPT-4o-mini handles them well out-of-the-box.
- Prompt can be updated without retraining.

**Negative**
- Per-call API cost vs. a locally hosted model.
- Latency dependent on OpenAI API availability.
- Less interpretable than a feature-weight model.
