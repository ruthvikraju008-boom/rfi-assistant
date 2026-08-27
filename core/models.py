"""
SQLAlchemy ORM models for the RFI Knowledge Assistant.

RFI            -> one row per Request-for-Information consideration/response pair.
AuditLogEntry  -> simple, append-only audit trail per RFI (created / reviewed / approved / rejected).
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class RFI(Base):
    __tablename__ = "rfis"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identity / traceability fields (Feature 1 - Automated RFI Document Processing)
    rfi_uuid = Column(String(120), index=True)              # e.g. CT-2024-123456-12-00-SM01-001
    application_id = Column(String(60), index=True)          # e.g. 2024-123456-12-00
    evaluation_process = Column(String(120))                 # e.g. Validation
    msc = Column(String(120), index=True)                    # Member State Concerned / country
    section_parts = Column(String(255), index=True)          # e.g. "Part II - France"
    section_document = Column(Text)                          # e.g. "Subject information and informed consent form"

    consideration_number = Column(String(20))
    consideration_text = Column(Text, nullable=False)
    sponsor_response = Column(Text)

    changes_made = Column(String(20))       # Yes / No
    reason_for_request = Column(String(255))

    due_date = Column(String(40))
    response_date = Column(String(40))
    date_submitted = Column(String(40))

    # Workflow / knowledge-loop fields (Feature 5 - Continuous Knowledge Loop)
    status = Column(String(30), default="approved", index=True)
    # one of: draft | pending_review | approved | rejected

    source_filename = Column(String(255))     # original uploaded file, if any
    full_text = Column(Text)                  # raw extracted text, kept for context / re-parsing

    created_by = Column(String(120), default="hackathon_user")
    created_at = Column(DateTime, default=utcnow)

    reviewed_by = Column(String(120))
    reviewed_at = Column(DateTime)

    audit_entries = relationship(
        "AuditLogEntry", back_populates="rfi", cascade="all, delete-orphan"
    )

    def searchable_text(self) -> str:
        """Text blob used for keyword + semantic search."""
        parts = [
            self.consideration_text or "",
            self.sponsor_response or "",
            self.section_parts or "",
            self.section_document or "",
            self.msc or "",
        ]
        return " \n".join(p for p in parts if p)


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfi_id = Column(Integer, ForeignKey("rfis.id"), index=True)
    action = Column(String(60))          # created | submitted_for_review | approved | rejected
    actor = Column(String(120))
    note = Column(Text)
    timestamp = Column(DateTime, default=utcnow)

    rfi = relationship("RFI", back_populates="audit_entries")
