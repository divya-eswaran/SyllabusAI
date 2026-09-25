"""Router for subject search and subject detail retrieval."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, cast, String

from app.database import get_db
from app.models import Subject, Unit, Topic
from app.schemas import SubjectOut, SubjectSummary, SearchResponse

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])


@router.get("/search", response_model=SearchResponse)
def search_subjects(
    q: str = Query(..., min_length=1, description="Subject name or code"),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """
    Search subjects by name or code.
    Tries exact match first, then ILIKE partial match.
    """
    q = q.strip()
    results = (
        db.query(Subject)
        .filter(
            or_(
                func.upper(Subject.subject_code) == q.upper(),
                func.upper(Subject.subject_name) == q.upper(),
                Subject.subject_name.ilike(f"%{q}%"),
                Subject.subject_code.ilike(f"%{q}%"),
            )
        )
        .order_by(Subject.subject_name)
        .limit(limit)
        .all()
    )

    summaries = []
    for s in results:
        topic_count = sum(len(u.topics) for u in s.units)
        summaries.append(
            SubjectSummary(
                id=s.id,
                subject_code=s.subject_code,
                subject_name=s.subject_name,
                semester=s.semester,
                credits=s.credits,
                course_type=s.course_type,
                unit_count=len(s.units),
                topic_count=topic_count,
            )
        )

    return SearchResponse(results=summaries, total=len(summaries), query=q)


@router.get("/all", response_model=SearchResponse)
def list_all_subjects(
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    """List all subjects in the database."""
    subjects = db.query(Subject).order_by(Subject.subject_name).limit(limit).all()
    summaries = []
    for s in subjects:
        topic_count = sum(len(u.topics) for u in s.units)
        summaries.append(
            SubjectSummary(
                id=s.id,
                subject_code=s.subject_code,
                subject_name=s.subject_name,
                semester=s.semester,
                credits=s.credits,
                course_type=s.course_type,
                unit_count=len(s.units),
                topic_count=topic_count,
            )
        )
    return SearchResponse(results=summaries, total=len(summaries), query="")


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    """Get full subject details including all units and topics."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")
    return subject
