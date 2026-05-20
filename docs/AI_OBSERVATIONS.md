# AI Observations: Working With LLMs as Part of the Application Stack

**Author:** Madhavi Sivala   
**Context:** Building a DME document classification pipeline using GPT-4o-mini

---

## 1. Start With the Workflow, Not the Model

My first instinct was to think of this as a classification problem. Feed PDFs in, get labels out.

But the actual question the business needs answered is simpler and more useful: can this patient's workflow proceed, and what is blocking it?

That reframe changed the whole system. What started as document classification became patient-level workflow readiness — completeness checking, review flagging, operational outputs that a coordinator can act on.

This led to building completeness.py, patient grouping, required-document logic, and review workflows — none of which were in the original spec. They came from understanding the workflow first.

---

## 2. Read the Data Before Designing the Solution

I opened the PDFs before writing any code. A few things came up right away.

A lot of the documents were scanned or image-heavy — not text PDFs you can extract from. Patient files were intentionally incomplete. Filenames were not always reliable. Document boundaries and document type labels were ambiguous in places.

One specific example: Prescription 2.pdf was classified as Order.

When I looked at the document itself it showed an Order ID, an Order Date, and equipment selection sections. The filename said Prescription. The document said Order. The model's classification was defensible.

This reinforced something important early on — AI classification quality depends on clear document type definitions as much as model quality. Filenames are not ground truth. The classifier has to work on content.

---

## 3. The Prompt Became a Core Artifact

The prompt went through several iterations before it worked reliably.

It ended up encoding explicit document type definitions, key identifiers per document type, structured JSON output requirements, and an instruction to return Unknown rather than guess.

That is not just a string passed to an API. It is business logic. It became document type documentation and a model contract at the same time.

The practical implication: the prompt should be version controlled and treated like code. A change to the prompt is a change to system behavior. Without a regression test set against known documents, you would not catch a prompt change breaking a document category until it shows up in production.

---

## 4. Business Rules Belong in Data, Not Prompts

The first version hardcoded document types directly in the classifier. It worked for CPAP. It would not scale to other DME equipment types.

The system was redesigned so document type definitions live in SQLite. Document types, their descriptions, their key identifiers, and whether they are required for a complete patient file all come from the database. The classifier builds the prompt dynamically from those rows.

This matters because DME workflows vary across equipment types — CPAP, oxygen therapy, cardiac monitoring, mobility equipment. Adding a new workflow should mean updating the document type configuration, not changing classifier code.

Adding support for a new equipment type is primarily a configuration change rather than a classifier code change.

---

## 5. Validate the AI API Contract Before Building Around It

The original implementation tried to send PDFs through the image_url path inside chat.completions. It failed. The image_url field accepts image MIME types — not application/pdf.

This was only discovered during end-to-end testing, after the architecture was already built around that assumption.

The fix was switching to the Files API and Responses API with uploaded file references. That worked. But the lesson was clear: AI API contracts need to be validated with a real isolated spike before building architecture around them. Not assumed. Actually called with a real file that comes back successfully.

AI-assisted development can move quickly from assumption to integrated implementation. That speed is a liability if the external contract turns out to be different from what was assumed.

---

## 6. AI-Assisted Coding Can Outpace Human Understanding

This was the most unexpected part of the project and it was not a technical problem.

AI tools accelerated architecture generation, test generation, and implementation faster than a solid understanding of each piece was forming. That felt productive. It became a problem during debugging — small integration changes were hard to reason about because the mental model had not kept up with the code.

The most effective workflow turned out to be smaller iterative steps. Generate a module, understand it, test it in isolation, then move on. Generating large changes all at once and then trying to debug them was slower, not faster — even though it felt faster while it was happening.

The right mental model: AI writes a first draft, you review and understand it, then you own it. Not: AI builds it, you run it.

---

## 7. Confidence Scores Are Useful but Not Sufficient

The model returned high confidence on most classifications. But confidence alone was not enough to trust a result.

A document can strongly resemble an Order in structure while the business labels it as a Prescription based on context the model did not have. The model can return 0.95 confidence and still be wrong by the operational definition.

Confidence is most useful as a routing signal — above threshold, auto-route; below threshold, human review. In a healthcare workflow where a misclassification can delay care or cause a billing failure, the human review queue is not a fallback. It is a designed part of the system.

---

## 8. Human Review Is Part of the Design

The system intentionally supports requires_review, Unknown, and graceful degradation rather than forcing a hard classification on every document.

This became important during malformed responses, document type ambiguity, API failures, and rate limit exhaustion. Documents that cannot be classified confidently are surfaced for human review rather than silently dropped or guessed at.

In a healthcare context this is not optional. The system needs to know what it does not know.

---

## 9. Rate Limits Introduce Operational Non-Determinism

Sequential batch processing of 21 documents hit OpenAI TPM rate limits during testing. Large documents like Physician Notes consumed significant token volume per call.

The observed behavior was automatic retries, eventual retry exhaustion, and fallback to Unknown with requires_review=True. Documents that hit the limit were surfaced for review rather than silently lost.

Running the same batch twice produced different results. In run 1, Physician Notes 2 and 3 both failed due to rate limits. In run 2 with a sleep between documents, Physician Notes 3 succeeded and only Physician Notes 2 failed.

This is an important distinction: the model itself is consistent — the same document classified successfully always returned the same result. The non-determinism was operational, not model-level. Whether a classification succeeds depends on token availability at runtime, not on model behavior.

This means a pipeline running the same documents on different days, or at different times of day, can produce different completeness outcomes for the same patient. That is a production reliability concern that confidence scores alone cannot surface — a document is not flagged as uncertain, it simply fails to classify at all.

The V1 mitigation was sequential processing with a delay between documents. A production implementation needs queue-based throttling, token-aware scheduling, and async workers with proper retry budgets.

---

## 10. A Few Things Worth Passing On

**Start with the workflow.** The technical decisions in this project followed naturally from understanding how DME intake actually works. Starting with the model would have produced a labeler. Starting with the workflow produced something useful.

**Validate external API contracts early.** Do not build architecture around assumed behavior. Run a real spike first.

**The prompt is code.** Version it, review changes, test regressions when it changes.

**Smaller steps work better with AI assistance.** Generate, understand, verify, move on.

**Human review is a feature, not a fallback.** A system that surfaces uncertainty is more trustworthy in healthcare than one that always returns an answer.

**Ambiguity is the job.** This exercise was deliberately underspecified. That is what early stage product work feels like. The job is to identify what is unknown, make reasonable decisions, write down the reasoning, and keep moving.

---

## 11. Completeness Checking Revealed a Workflow Order Problem

The initial completeness logic treated all missing documents equally. A patient file was either complete or it was not.

Running the pipeline against real data exposed a subtlety. Patient 4 was missing only a Delivery Ticket. The system marked them as cannot_start. That was wrong.

A Delivery Ticket comes at the end of the workflow — it is proof of delivery and triggers billing. A patient missing a Delivery Ticket absolutely can start their workflow. They have a Prescription, clinical documentation, and an Order. Everything needed to begin is present. The missing document only matters at the final step.

A missing Prescription is different. Without it nothing can proceed — there is no clinical authorization to order equipment, no basis for insurance, no workflow to run.

The documents have order dependencies that flat completeness checking does not capture:

- Missing Prescription → cannot start at all
- Missing Sleep Study or Physician Notes → cannot get prior authorization
- Missing Order → cannot fulfill equipment
- Missing Delivery Ticket → cannot trigger billing, but earlier steps can proceed
- Missing Compliance Report → cannot renew coverage, but initial workflow can proceed

This is a V2 improvement — the completeness check should understand document position in the workflow, not just presence or absence. The current system surfaces the missing-document gap, but does not yet distinguish between a gap that blocks everything and a gap that only blocks a downstream step.

The finding reinforced something broader: deterministic workflow logic needs domain knowledge, not just document checklists. That domain knowledge should live in the database — each document type should carry its workflow position and what it blocks.

---

## 12. Using Multiple Models as Independent Reviewers

One practical workflow insight from this project was using multiple AI models to review the same implementation decisions independently.

Different models made different mistakes:
- one model tended to move quickly and generate large architectural changes confidently
- another was better at consistency checking and identifying contradictions between implementation and documentation
- neither was consistently reliable enough to trust without verification

Using a second model as a reviewer often surfaced:
- incorrect assumptions
- stale documentation
- implementation/documentation drift
- API misuse
- tests that passed for the wrong reason
- architectural claims not actually implemented

This ended up feeling less like "using more AI" and more like introducing independent reviewers into the engineering workflow.

The important realization was that AI-assisted development still requires:
- architectural ownership
- implementation verification
- operational reasoning
- deliberate review checkpoints

Without that discipline, AI can accelerate both implementation speed and implementation drift simultaneously.