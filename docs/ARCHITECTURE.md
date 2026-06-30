# Architecture — RegSense

## High-level diagram

```
                    ┌──────────────────────────┐
                    │   SEBI Circular (text)    │
                    │  master circular / PDF    │
                    └────────────┬──────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────┐
                │      EXTRACTION AGENT           │
                │  (Claude API, JSON-only system  │
                │   prompt, clause-level parsing) │
                │                                 │
                │  Input : raw clause text         │
                │  Output: Obligation[] JSON       │
                └────────────────┬────────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────┐
                │         RULE ENGINE             │
                │  - schema validation             │
                │  - dedupe vs existing obligations│
                │  - version bump on amendment     │
                │  - map → intermediary category   │
                │  - map → operational workflow id │
                └────────────────┬────────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────┐
                │      COMPLIANCE TRACKER         │
                │  - obligation x evidence linkage │
                │  - status computation:           │
                │    Compliant/Partial/Gap/Overdue │
                │  - deadline monitoring           │
                └────────────────┬────────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────┐
                │        AUDIT TRAIL              │
                │  SHA-256 hash-chained log of     │
                │  every obligation/evidence/      │
                │  status change — tamper-evident  │
                └────────────────┬────────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────┐
                │   COMPLIANCE OFFICER DASHBOARD   │
                │  obligations · gaps · deadlines  │
                │  audit history · evidence upload │
                └────────────────────────────────┘
```

## Data model

**Obligation**
| field | type | description |
|---|---|---|
| id | str (uuid) | unique obligation id |
| source_circular | str | circular reference number |
| source_clause | str | verbatim clause id/section the obligation derives from |
| intermediary_category | str | e.g. "stockbroker" |
| requirement_summary | str | plain-language summary of the obligation |
| action_type | str | e.g. "reporting", "disclosure", "process_control" |
| frequency | str | e.g. "daily", "annual", "one_time" |
| deadline | datetime/null | next due date if applicable |
| evidence_required | str | what counts as proof of fulfilment |
| version | int | increments on regulatory amendment |
| created_at | datetime | |

**Evidence**
| field | type | description |
|---|---|---|
| id | str (uuid) | |
| obligation_id | str (fk) | |
| description | str | what was submitted |
| submitted_at | datetime | |
| status | str | Compliant / Partial / Missing |

**AuditLogEntry**
| field | type | description |
|---|---|---|
| id | str (uuid) | |
| entity_type | str | obligation / evidence |
| entity_id | str | |
| action | str | created / updated / status_changed |
| payload_hash | str | SHA-256 of the event payload |
| prev_hash | str | hash of the previous log entry (chain) |
| timestamp | datetime | |

## Why this design

- **Separation of extraction from rule storage** means re-running the agent on an
  amended circular doesn't blindly overwrite history — the Rule Engine diffs and
  versions, which is what "auditable compliance logic" requires.
- **Hash-chaining the audit log** gives regulator-grade tamper evidence without the
  operational overhead of a real distributed ledger — any edit to a past entry breaks
  the chain and is immediately detectable.
- **Decoupled Compliance Tracker** means the same obligation schema can later support
  any intermediary category (depositories, AMCs, RTAs, investment advisers) by
  swapping the workflow mapping table, not the core pipeline.
