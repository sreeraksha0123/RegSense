# RegSense — Agentic Compliance: From Regulatory Text to Operational Action

**SEBI Securities Market TechSprint — Problem Statement 2 (Agentic Compliance)**

RegSense is an AI agent pipeline that ingests SEBI regulatory text (circulars, master
circulars) and converts it into structured, machine-actionable, auditable compliance
obligations for market intermediaries — closing the gap between regulatory issuance
and operational compliance action.

**Intermediary category covered (prototype scope):** Stockbrokers
**Regulatory corpus used:** SEBI Master Circular for Stockbrokers (clauses on KYC,
margin reporting, risk disclosure, client fund segregation — sample excerpts in
`data/sample_circular.txt`, used for demonstration)

---

## The two problems we solve

1. **Dynamic regulatory translation** — turn a new/amended circular into structured
   obligation objects (who it applies to, what action is required, by when, what
   evidence proves compliance) instead of manual legal reading.
2. **Ongoing compliance management** — track each obligation against evidence
   submitted by the intermediary, auto-compute compliance status, surface gaps
   before they become regulatory findings, and keep an immutable audit trail.

## How it works (pipeline)

```
SEBI Circular (raw text/PDF)
        │
        ▼
[1] Extraction Agent  (Claude API, structured-JSON prompting)
    → parses unstructured clauses into Obligation objects
        │
        ▼
[2] Rule Engine
    → validates schema, dedupes, versions obligations,
      maps each to intermediary category + operational workflow step
        │
        ▼
[3] Compliance Tracker
    → intermediary uploads/links evidence per obligation
    → engine computes status: Compliant / Partial / Gap / Overdue
        │
        ▼
[4] Audit Trail
    → every state change is hash-chained (tamper-evident log)
      for regulator-grade auditability
        │
        ▼
[5] Dashboard
    → compliance officer view: obligations, gaps, deadlines, audit history
```

See `docs/ARCHITECTURE.md` for the detailed diagram and data model.

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite (swap for Postgres in prod)
- **Agentic extraction:** Anthropic Claude API (`claude-sonnet-4-6`), structured
  JSON-only system prompt, one circular clause → one or more Obligation records
- **Frontend:** Server-rendered dashboard (Jinja2 + vanilla JS/CSS) — compliance
  officer view of obligations, statuses, gaps, and audit trail
- **Auditability:** SHA-256 hash-chained append-only audit log (blockchain-style
  tamper evidence without the overhead of an actual chain)

## Repository layout

```
regsense/
├── backend/
│   ├── main.py              FastAPI app & routes
│   ├── extraction_agent.py  Claude-powered regulatory text → JSON obligations
│   ├── models.py            SQLAlchemy models
│   ├── database.py          DB session/engine setup
│   ├── rule_engine.py       Mapping, dedupe, gap analysis logic
│   └── audit.py             Hash-chained audit log
├── frontend/
│   ├── templates/           Dashboard HTML (Jinja2)
│   └── static/              CSS
├── data/
│   └── sample_circular.txt  Sample SEBI stockbroker circular clauses for demo
├── docs/
│   ├── ARCHITECTURE.md      Detailed architecture & data model
│   └── DEMO_SCRIPT.md       3-minute demo video script
├── requirements.txt
└── README.md
```

## Running locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
uvicorn backend.main:app --reload
```

Then open `http://localhost:8000` for the dashboard, or `POST /ingest` with a
circular text file to run the extraction pipeline end-to-end.

## Demonstrated scenario

We feed in a SEBI Master Circular excerpt for stockbrokers covering: (1) client
KYC re-verification cadence, (2) daily margin reporting to the exchange, (3) client
fund segregation in a separate bank account. RegSense extracts three structured
obligations, maps each to the stockbroker workflow, lets a mock compliance officer
mark evidence as submitted/missing, computes live compliance status, and logs every
action to the tamper-evident audit trail — visible on the dashboard.

## Roadmap beyond prototype

- Ingest full SEBI circular RSS/repository automatically (diff-based change detection)
- Multi-intermediary support (depositories, AMCs, RTAs, investment advisers)
- Confidence scoring + human-in-the-loop review queue for low-confidence extractions
- Integration hooks (webhook/API) into intermediaries' existing GRC tooling
