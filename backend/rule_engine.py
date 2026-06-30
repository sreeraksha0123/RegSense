"""
Rule Engine
-----------
Takes raw obligation dicts from the extraction agent, validates/normalises
them, dedupes against what's already stored, and persists them with
versioning. Also provides gap-analysis helpers for the dashboard.
"""

from typing import List, Dict

from sqlalchemy.orm import Session

from backend.models import Obligation
from backend import audit

REQUIRED_FIELDS = {
    "source_clause",
    "intermediary_category",
    "requirement_summary",
    "action_type",
    "frequency",
    "evidence_required",
    "source_circular",
}


def _validate(ob: Dict) -> None:
    missing = REQUIRED_FIELDS - ob.keys()
    if missing:
        raise ValueError(f"Obligation missing required fields: {missing}")


def ingest_obligations(db: Session, obligations: List[Dict]) -> List[Obligation]:
    """Validate, dedupe (by source_circular + source_clause), version, and persist."""
    saved = []
    for ob in obligations:
        _validate(ob)

        existing = (
            db.query(Obligation)
            .filter_by(
                source_circular=ob["source_circular"],
                source_clause=ob["source_clause"],
                intermediary_category=ob["intermediary_category"],
            )
            .first()
        )

        if existing:
            # Regulatory amendment: bump version, update fields, log it.
            existing.requirement_summary = ob["requirement_summary"]
            existing.action_type = ob["action_type"]
            existing.frequency = ob["frequency"]
            existing.evidence_required = ob["evidence_required"]
            existing.version += 1
            db.commit()
            db.refresh(existing)
            audit.log_event(
                db, "obligation", existing.id, "updated",
                {"version": existing.version, "summary": existing.requirement_summary},
            )
            saved.append(existing)
        else:
            new_ob = Obligation(
                source_circular=ob["source_circular"],
                source_clause=ob["source_clause"],
                intermediary_category=ob["intermediary_category"],
                requirement_summary=ob["requirement_summary"],
                action_type=ob["action_type"],
                frequency=ob["frequency"],
                evidence_required=ob["evidence_required"],
            )
            db.add(new_ob)
            db.commit()
            db.refresh(new_ob)
            audit.log_event(
                db, "obligation", new_ob.id, "created",
                {"summary": new_ob.requirement_summary, "circular": new_ob.source_circular},
            )
            saved.append(new_ob)

    return saved


def gap_analysis(db: Session, intermediary_category: str = None) -> Dict[str, List[Obligation]]:
    """Bucket obligations by computed status for the dashboard."""
    query = db.query(Obligation)
    if intermediary_category:
        query = query.filter_by(intermediary_category=intermediary_category)
    obligations = query.all()

    buckets = {"Compliant": [], "Partial": [], "Gap": []}
    for ob in obligations:
        buckets.setdefault(ob.status, []).append(ob)
    return buckets
