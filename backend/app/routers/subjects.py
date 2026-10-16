"""Router for subject search and subject detail retrieval."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, cast, String

from app.database import get_db
from app.models import Subject, Unit, Topic
from app.schemas import SubjectOut, SubjectSummary, SearchResponse

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])


import re

ROMAN_TO_ARABIC = {
    "I": "1", "II": "2", "III": "3", "IV": "4",
    "V": "5", "VI": "6", "VII": "7", "VIII": "8"
}
ARABIC_TO_ROMAN = {
    1: "I", 2: "II", 3: "III", 4: "IV",
    5: "V", 6: "VI", 7: "VII", 8: "VIII"
}


@router.get("/search", response_model=SearchResponse)
def search_subjects(
    q: str = Query(..., min_length=1, description="Subject name, code, semester, or regulation"),
    limit: int = Query(default=30, le=100),
    db: Session = Depends(get_db),
):
    """
    Search subjects by name, code, semester (e.g. 'semester 6', 'sem 6'), or regulation.
    """
    query_str = q.strip()
    filters = []

    # Check if query is searching for a semester (e.g. "sem 6", "semester 6", "s6", "sem-vi")
    sem_match = re.search(
        r"\b(?:sem(?:ester)?|s)\s*[-:]?\s*([1-8]|i{1,3}|iv|v|vi{0,3}|vii|viii)\b",
        query_str,
        re.IGNORECASE,
    )

    if sem_match:
        val = sem_match.group(1).upper()
        arabic_sem = ROMAN_TO_ARABIC.get(val, val)
        roman_sem = ARABIC_TO_ROMAN.get(int(arabic_sem) if arabic_sem.isdigit() else 0, val)

        sem_conditions = [
            Subject.semester == arabic_sem,
            Subject.semester == roman_sem,
            Subject.semester.ilike(f"%{arabic_sem}%"),
            Subject.semester.ilike(f"%{roman_sem}%"),
        ]
        # Match college course codes where semester is embedded (e.g. IT23601 -> digit after 23 is 6)
        for yr in ["23", "21", "17", "19", "20", "22", "24"]:
            sem_conditions.append(Subject.subject_code.ilike(f"%{yr}{arabic_sem}__"))

        filters.append(or_(*sem_conditions))
    else:
        # Standard search across code, name, and regulation
        reg_clean = re.sub(r"^(?:reg(?:ulation)?|r)\s*[-:]?\s*", "", query_str, flags=re.IGNORECASE).strip()
        standard_conditions = [
            func.upper(Subject.subject_code) == query_str.upper(),
            func.upper(Subject.subject_name) == query_str.upper(),
            Subject.subject_name.ilike(f"%{query_str}%"),
            Subject.subject_code.ilike(f"%{query_str}%"),
            Subject.regulation.ilike(f"%{query_str}%"),
        ]
        if reg_clean and reg_clean != query_str:
            standard_conditions.append(Subject.regulation.ilike(f"%{reg_clean}%"))

        filters.append(or_(*standard_conditions))

    results = (
        db.query(Subject)
        .filter(*filters)
        .order_by(Subject.subject_code, Subject.subject_name)
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
                regulation=s.regulation,
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
    subjects = db.query(Subject).order_by(Subject.subject_code).limit(limit).all()
    summaries = []
    for s in subjects:
        topic_count = sum(len(u.topics) for u in s.units)
        summaries.append(
            SubjectSummary(
                id=s.id,
                subject_code=s.subject_code,
                subject_name=s.subject_name,
                semester=s.semester,
                regulation=s.regulation,
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
