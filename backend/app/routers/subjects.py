"""Router for subject search, filtering, and subject detail retrieval."""

import re
from typing import Optional, List, Set, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.models import Subject, Unit, Topic
from app.schemas import SubjectOut, SubjectSummary, SearchResponse, SemesterInfo

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])

ROMAN_MAP = {
    "i": "1",
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "v": "5",
    "vi": "6",
    "vii": "7",
    "viii": "8",
    "ix": "9",
    "x": "10",
}
REV_ROMAN = {v: k for k, v in ROMAN_MAP.items()}

SEM_EXACT_PATTERNS = [
    re.compile(r"^\s*(?:sem(?:ester)?|s)\s*[-:]?\s*([0-9]+|[ivxlcdm]+)\s*$", re.IGNORECASE),
    re.compile(r"^\s*([0-9]+)(?:st|nd|rd|th)?\s*(?:sem(?:ester)?)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:electives?|pe|oec)\s*$", re.IGNORECASE),
]

SEM_CONTAINS_PATTERNS = [
    re.compile(r"\b(?:sem(?:ester)?|s)\s*[-:]?\s*([0-9]+|[ivxlcdm]+)\b", re.IGNORECASE),
    re.compile(r"\b([0-9]+)(?:st|nd|rd|th)?\s*(?:sem(?:ester)?)\b", re.IGNORECASE),
    re.compile(r"\b(electives?)\b", re.IGNORECASE),
]


def parse_semester_search(q: str) -> Tuple[Optional[str], str]:
    """
    Parses query string for semester references.
    Returns (semester_normalized_value, remaining_query).
    """
    cleaned = q.strip()
    if not cleaned:
        return None, ""

    # Check exact semester match (e.g., 'sem 6', 'semester 6', '6th sem', 'electives')
    for pat in SEM_EXACT_PATTERNS:
        m = pat.match(cleaned)
        if m:
            raw = (m.group(1) if m.groups() else m.group(0)).lower()
            if raw.startswith("elec"):
                return "elective", ""
            norm = ROMAN_MAP.get(raw, raw)
            return norm, ""

    # Check embedded semester match (e.g., 'sem 6 distributed', 'machine learning sem 5')
    for pat in SEM_CONTAINS_PATTERNS:
        m = pat.search(cleaned)
        if m:
            raw = (m.group(1) if m.groups() else m.group(0)).lower()
            if raw.startswith("elec"):
                norm = "elective"
            else:
                norm = ROMAN_MAP.get(raw, raw)
            rem = pat.sub("", cleaned).strip()
            rem = re.sub(r"[\s\-_]+", " ", rem).strip()
            return norm, rem

    return None, cleaned


def get_semester_candidates(sem_norm: str) -> Set[str]:
    """
    Generate set of possible database representations for a given semester string.
    """
    sem_str = str(sem_norm).lower().strip()
    if sem_str == "elective":
        return {"elective", "electives", "pe", "oec", "5-8", "5-7"}

    cands = {sem_str, sem_str.zfill(2)}
    if sem_str in REV_ROMAN:
        roman = REV_ROMAN[sem_str]
        cands.add(roman.lower())
        cands.add(roman.upper())

    extended = set(cands)
    for c in list(cands):
        extended.add(f"sem {c}")
        extended.add(f"sem-{c}")
        extended.add(f"semester {c}")
        extended.add(f"semester-{c}")
    return {c.lower() for c in extended}


@router.get("/semesters", response_model=List[SemesterInfo])
def list_semesters(db: Session = Depends(get_db)):
    """Return all distinct semesters present in the database with subject counts."""
    rows = (
        db.query(Subject.semester, func.count(Subject.id))
        .filter(Subject.semester.isnot(None))
        .group_by(Subject.semester)
        .all()
    )

    sem_counts = {}
    for sem_val, count in rows:
        if not sem_val:
            continue
        cleaned = sem_val.strip().lower()
        if cleaned.startswith("elec") or cleaned in {"pe", "oec", "5-8", "5-7"}:
            norm = "elective"
        else:
            norm = ROMAN_MAP.get(cleaned, cleaned)
        sem_counts[norm] = sem_counts.get(norm, 0) + count

    def sort_key(s):
        try:
            return (0, int(s))
        except ValueError:
            return (1, s)

    result = []
    for s in sorted(sem_counts.keys(), key=sort_key):
        if s.isdigit():
            display = f"Semester {s}"
        elif s == "elective":
            display = "Electives"
        else:
            display = f"Semester {s.upper()}"
        result.append(SemesterInfo(semester=s, display_name=display, count=sem_counts[s]))

    return result


@router.get("/search", response_model=SearchResponse)
def search_subjects(
    q: Optional[str] = Query(default=None, description="Subject name, code, or semester (e.g. 'sem 6')"),
    semester: Optional[str] = Query(default=None, description="Explicit semester filter"),
    limit: int = Query(default=100, le=200),
    db: Session = Depends(get_db),
):
    """
    Search subjects by name, subject code, semester, or regulation.
    Smartly detects queries like 'sem 6', 'semester 4', 'IT23401', 'Operating Systems', 'Regulation 2023'.
    """
    q_val = q if isinstance(q, str) else None
    sem_val = semester if isinstance(semester, str) else None
    lim_val = limit if isinstance(limit, int) else 100

    query_str = (q_val or "").strip()
    detected_sem = None
    rest_q = query_str

    if sem_val:
        cleaned_sem = sem_val.strip().lower()
        if cleaned_sem.startswith("elec"):
            detected_sem = "elective"
        else:
            detected_sem = ROMAN_MAP.get(cleaned_sem, cleaned_sem)

        # Clean semester references from query_str so they don't corrupt text search
        sem_from_q, rem_q = parse_semester_search(query_str)
        if sem_from_q:
            rest_q = rem_q
        elif rest_q.lower() in {
            f"sem {cleaned_sem}",
            f"semester {cleaned_sem}",
            f"{cleaned_sem}th sem",
            cleaned_sem,
            "sem",
            "semester",
        }:
            rest_q = ""
    elif query_str:
        detected_sem, rest_q = parse_semester_search(query_str)

    # Clean rest_q if only noise left
    if rest_q and rest_q.lower() in {"sem", "semester", "s", "elective", "electives"}:
        rest_q = ""

    query = db.query(Subject)

    if detected_sem:
        cands = list(get_semester_candidates(detected_sem))
        sem_condition = func.lower(func.trim(Subject.semester)).in_(cands)

        if rest_q:
            rest_clean = rest_q.strip()
            text_condition = or_(
                func.upper(Subject.subject_code) == rest_clean.upper(),
                Subject.subject_code.ilike(f"%{rest_clean}%"),
                Subject.subject_name.ilike(f"%{rest_clean}%"),
                Subject.regulation.ilike(f"%{rest_clean}%"),
                Subject.course_type.ilike(f"%{rest_clean}%"),
            )
            results = (
                query.filter(sem_condition, text_condition)
                .order_by(
                    (func.upper(Subject.subject_code) == rest_clean.upper()).desc(),
                    Subject.subject_code,
                    Subject.subject_name,
                )
                .limit(lim_val)
                .all()
            )
        else:
            results = (
                query.filter(sem_condition)
                .order_by(Subject.subject_code, Subject.subject_name)
                .limit(lim_val)
                .all()
            )
    elif query_str:
        q_clean = query_str.strip()
        results = (
            query.filter(
                or_(
                    func.upper(Subject.subject_code) == q_clean.upper(),
                    Subject.subject_code.ilike(f"%{q_clean}%"),
                    Subject.subject_name.ilike(f"%{q_clean}%"),
                    Subject.regulation.ilike(f"%{q_clean}%"),
                    Subject.semester.ilike(f"%{q_clean}%"),
                    Subject.course_type.ilike(f"%{q_clean}%"),
                )
            )
            .order_by(
                (func.upper(Subject.subject_code) == q_clean.upper()).desc(),
                (func.upper(Subject.subject_name) == q_clean.upper()).desc(),
                Subject.subject_code,
            )
            .limit(lim_val)
            .all()
        )
    else:
        results = query.order_by(Subject.semester, Subject.subject_code).limit(lim_val).all()

    summaries = []
    for s in results:
        topic_count = sum(len(u.topics) for u in s.units)
        summaries.append(
            SubjectSummary(
                id=s.id,
                subject_code=s.subject_code,
                subject_name=s.subject_name,
                regulation=s.regulation or "Regulation 2023",
                semester=s.semester,
                credits=s.credits,
                course_type=s.course_type,
                unit_count=len(s.units),
                topic_count=topic_count,
            )
        )

    return SearchResponse(
        results=summaries,
        total=len(summaries),
        query=query_str,
        detected_semester=detected_sem,
    )


@router.get("/all", response_model=SearchResponse)
def list_all_subjects(
    semester: Optional[str] = Query(default=None),
    limit: int = Query(default=200, le=500),
    db: Session = Depends(get_db),
):
    """List all subjects in the database, with optional semester filter."""
    query = db.query(Subject)
    detected_sem = None

    if semester:
        detected_sem = ROMAN_MAP.get(semester.strip().lower(), semester.strip().lower())
        cands = list(get_semester_candidates(detected_sem))
        query = query.filter(func.lower(func.trim(Subject.semester)).in_(cands))

    subjects = query.order_by(Subject.semester, Subject.subject_code).limit(limit).all()

    summaries = []
    for s in subjects:
        topic_count = sum(len(u.topics) for u in s.units)
        summaries.append(
            SubjectSummary(
                id=s.id,
                subject_code=s.subject_code,
                subject_name=s.subject_name,
                regulation=s.regulation or "Regulation 2023",
                semester=s.semester,
                credits=s.credits,
                course_type=s.course_type,
                unit_count=len(s.units),
                topic_count=topic_count,
            )
        )
    return SearchResponse(
        results=summaries,
        total=len(summaries),
        query="",
        detected_semester=detected_sem,
    )


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    """Get full subject details including all units and topics."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")
    return subject
