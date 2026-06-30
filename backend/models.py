import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_id() -> str:
    return str(uuid.uuid4())


class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(String, primary_key=True, default=gen_id)
    source_circular = Column(String, nullable=False)
    source_clause = Column(String, nullable=False)
    intermediary_category = Column(String, nullable=False, index=True)
    requirement_summary = Column(Text, nullable=False)
    action_type = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=True)
    evidence_required = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    evidence = relationship("Evidence", back_populates="obligation", cascade="all, delete-orphan")

    @property
    def status(self) -> str:
        if not self.evidence:
            return "Gap"
        latest = sorted(self.evidence, key=lambda e: e.submitted_at)[-1]
        return latest.status


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=gen_id)
    obligation_id = Column(String, ForeignKey("obligations.id"), nullable=False)
    description = Column(Text, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False, default="Partial")  # Compliant / Partial / Missing

    obligation = relationship("Obligation", back_populates="evidence")


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=gen_id)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    payload_hash = Column(String, nullable=False)
    prev_hash = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
