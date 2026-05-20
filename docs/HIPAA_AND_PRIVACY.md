# HIPAA and Privacy Considerations

**Status:** Not implemented in V1  
**Required before:** Any production deployment processing real patient data

---

## Why This Document Exists

This pipeline sends medical PDF documents to an external AI API (OpenAI). In production, those documents contain Protected Health Information (PHI) — patient names, dates of birth, diagnosis codes, physician identifiers, device serial numbers.

Sending PHI to a third-party service without proper safeguards is a HIPAA violation. This document explains what is required before this pipeline handles real patient data.

---

## Why the Exercise Is Safe

The sample documents provided for this exercise have been de-identified. Patient names, dates of birth, provider NPI numbers, and other identifiers have been redacted (visible as blue boxes in the scanned documents).

This means the exercise pipeline can run against OpenAI without HIPAA concerns. **This would not be true in production.**

---

## What HIPAA Requires

HIPAA applies when a system creates, receives, maintains, or transmits PHI. This pipeline does all four.

Before processing real patient documents, the organization must have one of the following in place:

**Option 1 — Business Associate Agreement (BAA) with OpenAI**

A BAA is a legal contract where OpenAI agrees to handle PHI in compliance with HIPAA. OpenAI offers BAAs for enterprise customers.

What this enables:
- Documents with PHI can be sent to OpenAI APIs
- OpenAI is contractually bound to HIPAA standards
- Data is not used for model training

What this requires:
- An enterprise OpenAI agreement
- Review and signing of the BAA before any PHI is processed
- Ongoing compliance monitoring

**Option 2 — Self-Hosted Model**

Run the classification model on infrastructure you control. No data leaves your environment.

What this requires:
- GPU hardware or a cloud VPC with appropriate controls
- A capable open-source model (Llama 3, Mistral, or similar)
- An extraction pipeline — self-hosted models do not support direct PDF input, so text extraction or OCR must be added (see ADR-002 Option 1)
- Significantly more infrastructure to maintain

**Option 3 — PII Redaction Before API Call**

Strip PHI from documents before sending them to any external service. The classifier only needs document structure and content type — not patient identity.

What this requires:
- A PHI detection and redaction step between extractor.py and classifier.py
- Tools: AWS Comprehend Medical, Microsoft Presidio, or a custom NER model
- Validation that redaction does not degrade classification accuracy
- Audit logging of what was redacted and when

---

## Where PII Redaction Fits in the Pipeline

If Option 3 is chosen, redaction sits between extraction and classification:

```
extractor.py
    → reads PDF bytes from disk or S3

privacy.py  ← NEW in production
    → detects PHI using AWS Comprehend Medical or Presidio
    → redacts: patient names, DOBs, SSNs, addresses, phone numbers,
               NPI numbers, device serial numbers, dates of service
    → logs redaction events for audit trail
    → returns sanitized content

classifier.py
    → receives sanitized content
    → sends to OpenAI — no PHI present
```

This approach works with any model provider, including those without a BAA, and adds an audit trail of every redaction event.

---

## Patient Consent

Patients consent to their DME provider processing their records for treatment and billing purposes. Whether that consent extends to AI processing is a legal and compliance question that engineering needs to surface — not answer.

Before deploying this pipeline, the organization should confirm:

- Whether existing patient consent forms cover AI-assisted document processing
- Whether additional consent or notice is required under state law
- Whether patients have a right to opt out of AI processing

---

## PHI Categories Present in These Documents

Based on review of the sample document types, the following PHI categories are present in real (non-de-identified) versions:

| Document Type | PHI Present |
|---|---|
| Prescription | Patient name, DOB, address, physician name, DEA number, diagnosis |
| Sleep Study Report | Patient name, DOB, physician name, facility, dates of service, diagnosis codes |
| Physician Notes | Patient name, DOB, medical history, diagnosis, treatment plan, NPI |
| Compliance Report | Patient name, device serial number, usage dates, provider info |
| Order | Patient name, DOB, physician NPI, diagnosis codes, equipment codes |
| Delivery Ticket | Patient name, address, signature, equipment serial numbers, delivery date |

---

## Minimum Requirements Before Production

| Requirement | Owner | Status |
|---|---|---|
| OpenAI BAA signed OR self-hosted model deployed | Legal / Engineering | Not started |
| PII redaction pipeline implemented and tested | Engineering | Not started |
| Patient consent language reviewed | Legal / Compliance | Not started |
| PHI audit logging implemented | Engineering | Not started |
| Security review of data flow | Security | Not started |
| Staff training on HIPAA obligations | Operations | Not started |

---

## References

- [HIPAA Business Associate Agreements](https://www.hhs.gov/hipaa/for-professionals/covered-entities/sample-business-associate-agreement-provisions/index.html)
- [OpenAI Enterprise Privacy](https://openai.com/enterprise-privacy)
- [Microsoft Presidio — open source PII detection](https://github.com/microsoft/presidio)
- [AWS Comprehend Medical](https://aws.amazon.com/comprehend/medical/)
