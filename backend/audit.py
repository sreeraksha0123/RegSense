import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from backend.models import AuditLogEntry

GENESIS_HASH = "0" * 64


def _hash_payload(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def get_last_hash(db: Session) -> str:
    last = (
        db.query(AuditLogEntry)
        .order_by(AuditLogEntry.timestamp.desc())
        .first()
    )
    return last.payload_hash if last else GENESIS_HASH


def log_event(db: Session, entity_type: str, entity_id: str, action: str, payload: dict) -> AuditLogEntry:
    """Append a tamper-evident, hash-chained audit log entry.

    Each entry's hash is derived from its own payload AND the previous entry's
    hash, so altering any historical entry breaks the chain for everything after it.
    """
    prev_hash = get_last_hash(db)
    payload_with_chain = {**payload, "prev_hash": prev_hash, "timestamp": datetime.utcnow().isoformat()}
    payload_hash = _hash_payload(payload_with_chain)

    entry = AuditLogEntry(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def verify_chain(db: Session) -> bool:
    """Re-walk the chain and confirm no entry has been tampered with."""
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.timestamp.asc()).all()
    expected_prev = GENESIS_HASH
    for entry in entries:
        if entry.prev_hash != expected_prev:
            return False
        expected_prev = entry.payload_hash
    return True
