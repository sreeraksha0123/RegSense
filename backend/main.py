import os
from datetime import datetime

from fastapi import FastAPI, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models import Obligation, Evidence, AuditLogEntry
from backend.extraction_agent import extract_obligations
from backend.rule_engine import ingest_obligations, gap_analysis
from backend import audit

app = FastAPI(title="RegSense — Agentic Compliance Engine")

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    buckets = gap_analysis(db)
    chain_ok = audit.verify_chain(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "buckets": buckets, "chain_ok": chain_ok},
    )


@app.post("/ingest")
def ingest_circular(
    circular_text: str = Form(...),
    intermediary_category: str = Form(...),
    source_circular: str = Form(...),
    db: Session = Depends(get_db),
):
    """Run the full pipeline: extraction agent -> rule engine -> persisted obligations."""
    raw_obligations = extract_obligations(circular_text, intermediary_category, source_circular)
    saved = ingest_obligations(db, raw_obligations)
    return {"ingested": len(saved), "obligations": [o.id for o in saved]}


@app.post("/obligations/{obligation_id}/evidence")
def submit_evidence(
    obligation_id: str,
    description: str = Form(...),
    status: str = Form(...),  # Compliant / Partial / Missing
    db: Session = Depends(get_db),
):
    evidence = Evidence(obligation_id=obligation_id, description=description, status=status)
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    audit.log_event(
        db, "evidence", evidence.id, "status_changed",
        {"obligation_id": obligation_id, "status": status, "description": description},
    )
    return {"evidence_id": evidence.id, "status": status}


@app.get("/audit-log")
def audit_log(db: Session = Depends(get_db)):
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.timestamp.asc()).all()
    return {
        "chain_valid": audit.verify_chain(db),
        "entries": [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "action": e.action,
                "payload_hash": e.payload_hash,
                "prev_hash": e.prev_hash,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries
        ],
    }


@app.get("/obligations")
def list_obligations(db: Session = Depends(get_db)):
    obligations = db.query(Obligation).all()
    return [
        {
            "id": o.id,
            "source_circular": o.source_circular,
            "source_clause": o.source_clause,
            "intermediary_category": o.intermediary_category,
            "requirement_summary": o.requirement_summary,
            "action_type": o.action_type,
            "frequency": o.frequency,
            "evidence_required": o.evidence_required,
            "version": o.version,
            "status": o.status,
        }
        for o in obligations
    ]
