# ADR-004: OpenAI Model Choice (GPT-4o-mini)

**Status:** Accepted

## Context

Classification requires both text understanding and image (vision) capability for scanned PDFs. Cost and latency matter for batch processing.

## Decision

Use `gpt-4o-mini` for both text classification and vision-based extraction.

## Alternatives Considered

| Model | Reason Not Chosen |
|-------|-------------------|
| `gpt-4o` | Higher cost per token; capability not needed for structured 6-class classification |
| `gpt-3.5-turbo` | No vision support; cannot handle scanned PDFs |
| Local LLaMA 3 (Ollama) | No built-in vision; would require a separate OCR step; harder to set up cross-platform |

## Consequences

**Positive**
- Single model handles both text and vision paths.
- Low cost relative to GPT-4o for the classification task.
- Fast inference suitable for batch of 22 documents.

**Negative**
- Requires an internet connection and valid OpenAI API key.
- Model behaviour may change with OpenAI API updates.
