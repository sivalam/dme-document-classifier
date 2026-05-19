# ADR-003: Output Format

**Status:** Accepted  
**Date:** 2024-11  
**Deciders:** Engineering Lead  
**Decision:** All three — JSON + CSV + SQLite, each serving a distinct purpose

---

## Context

The exercise asks us to "store the classification in some file." The format choice is left open. The problem statement hints at two requirements: ease of verification by humans, and ease of integration into software systems. These are different needs that point to different formats.

We also identified a third need during design: auditability and analytics over time — knowing what was classified, when, with what confidence, and whether any corrections were made.

---

## Options Comparison

| | Option 1: CSV Only | Option 2: JSON Only | Option 3: Database Only | Option 4: JSON + CSV + SQLite ✅ |
|---|---|---|---|---|
| **Human readable** | ✅ Opens in Excel | ❌ Requires tooling | ❌ Requires SQL client | ✅ CSV handles this |
| **Machine readable** | ⚠️ Parseable but not structured | ✅ Native for APIs and services | ✅ Queryable | ✅ JSON handles this |
| **Schema enforcement** | ❌ No types, no nesting | ✅ Nested structure, typed fields | ✅ Strong schema | ✅ All three enforced |
| **Audit trail** | ❌ Overwritten each run | ❌ Overwritten each run | ✅ Append per run, full history | ✅ SQLite handles this |
| **Analytics over time** | ❌ Manual | ❌ Manual | ✅ SQL queries | ✅ SQLite handles this |
| **Pipeline integration** | ⚠️ Extra parsing needed | ✅ Direct consumption | ⚠️ Requires DB client | ✅ JSON handles this |
| **Portability** | ✅ Any tool | ✅ Any tool | ❌ File must travel with schema | ✅ JSON and CSV are portable |
| **Complexity to produce** | Low | Low | Medium | Medium — but one pass writes all three |

---

## Decision

**Produce all three outputs — JSON, CSV, and SQLite.**

Each serves a different consumer:

- **JSON** — the primary output. Consumed by downstream software systems and workflow engines. Contains the full result including patient completeness status and exceptions.
- **CSV** — for human verification. A coordinator or reviewer opens it in Excel to spot-check results. Intentionally flat and simple.
- **SQLite** — for persistence and auditability. Every run appends a new batch of records. Supports analytics queries over time. The corrections table is schema-defined now so any future human-override workflow can integrate without a migration.

All three are written in a single pass by `storage.py` — no duplication of logic.

---

## Trade-offs Accepted

| Trade-off | Mitigation |
|---|---|
| Three outputs adds some complexity | All written by one module in one pass |
| SQLite not suitable for concurrent writes | V1 is single-process batch. Migrate to Postgres when concurrent access needed |
| Schema changes require migration | Use run_id versioning. SQLite ALTER TABLE for additive changes |

---

## When to Revisit

| Trigger | Action |
|---|---|
| Pipeline needs real-time event-driven routing | Add message queue output (SQS, Pub/Sub) alongside JSON |
| Multiple workers processing documents concurrently | Replace SQLite with Postgres |
| Need semantic search over document content | Add vector store output (Pinecone, pgvector) |
| Reporting needs exceed what SQLite queries can serve | Migrate to data warehouse (BigQuery, Redshift) |