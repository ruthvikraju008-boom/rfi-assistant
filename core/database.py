"""
Database engine / session management + small CRUD helpers used across the app.
"""
from contextlib import contextmanager

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from core.config import DATABASE_URL
from core.models import Base, RFI, AuditLogEntry, utcnow

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
# expire_on_commit=False: Streamlit code commonly reads objects returned from
# `with get_session() as session: ...` after the block (and thus the session)
# has already closed. Without this, SQLAlchemy would try to lazily re-fetch
# attributes from a closed session and raise DetachedInstanceError.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db():
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(engine)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def create_rfi(session, fields: dict, actor: str = "hackathon_user", status: str = "approved") -> RFI:
    rfi = RFI(
        rfi_uuid=fields.get("rfi_uuid"),
        application_id=fields.get("application_id"),
        evaluation_process=fields.get("evaluation_process"),
        msc=fields.get("msc"),
        section_parts=fields.get("section_parts"),
        section_document=fields.get("section_document"),
        consideration_number=fields.get("consideration_number"),
        consideration_text=fields.get("consideration_text", ""),
        sponsor_response=fields.get("sponsor_response", ""),
        changes_made=fields.get("changes_made"),
        reason_for_request=fields.get("reason_for_request"),
        due_date=fields.get("due_date"),
        response_date=fields.get("response_date"),
        date_submitted=fields.get("date_submitted"),
        status=status,
        source_filename=fields.get("source_filename"),
        full_text=fields.get("full_text"),
        created_by=actor,
    )
    session.add(rfi)
    session.flush()  # get rfi.id

    session.add(AuditLogEntry(
        rfi_id=rfi.id, action="created", actor=actor,
        note=f"RFI record created with status='{status}'.",
    ))
    return rfi


def update_status(session, rfi_id: int, new_status: str, actor: str, note: str = ""):
    rfi = session.get(RFI, rfi_id)
    if rfi is None:
        return None
    rfi.status = new_status
    rfi.reviewed_by = actor
    rfi.reviewed_at = utcnow()
    session.add(AuditLogEntry(
        rfi_id=rfi.id, action=new_status, actor=actor, note=note,
    ))
    return rfi


def all_rfis(session, statuses=None):
    q = session.query(RFI)
    if statuses:
        q = q.filter(RFI.status.in_(statuses))
    return q.order_by(RFI.created_at.desc()).all()


def get_audit_trail(session, rfi_id: int):
    return (
        session.query(AuditLogEntry)
        .filter(AuditLogEntry.rfi_id == rfi_id)
        .order_by(AuditLogEntry.timestamp.asc())
        .all()
    )


def keyword_search(session, terms: list, statuses=None):
    """Very simple OR-based keyword pre-filter against consideration/response text."""
    q = session.query(RFI)
    if statuses:
        q = q.filter(RFI.status.in_(statuses))
    if terms:
        clauses = []
        for t in terms:
            like = f"%{t}%"
            clauses.append(RFI.consideration_text.ilike(like))
            clauses.append(RFI.sponsor_response.ilike(like))
            clauses.append(RFI.section_parts.ilike(like))
            clauses.append(RFI.msc.ilike(like))
        q = q.filter(or_(*clauses))
    return q.all()
