"""Router for teacher class management and progress tracking."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.auth import get_optional_current_user
from app.models import Subject, TeacherClass, Topic, TopicProgress, Unit, User

from app.schemas import (
    TeacherClassCreate,
    TeacherClassOut,
    TopicProgressOut,
    ToggleProgressRequest,
)

router = APIRouter(prefix="/api/classes", tags=["Classes"])
def _build_class_out(tc: TeacherClass) -> TeacherClassOut:
    subject = tc.subject
    # Count all topics for this subject
    all_topics = []
    for unit in subject.units:
        all_topics.extend(unit.topics)

    total = len(all_topics)
    completed_ids = {tp.topic_id for tp in tc.topic_progress if tp.is_completed}
    completed = len(completed_ids)
    pct = round((completed / total) * 100, 1) if total > 0 else 0.0

    return TeacherClassOut(
        id=tc.id,
        subject_id=tc.subject_id,
        subject_name=subject.subject_name,
        subject_code=subject.subject_code,
        batch=tc.batch,
        department=tc.department,
        section=tc.section,
        semester=tc.semester,
        total_topics=total,
        completed_topics=completed,
        progress_percent=pct,
        created_at=tc.created_at,
    )




@router.post("", response_model=TeacherClassOut)
def create_class(
    payload: TeacherClassCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Add a new teacher class."""
    subject = db.query(Subject).filter(Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")

    tc = TeacherClass(
        subject_id=payload.subject_id,
        user_id=current_user.id if current_user else None,
        batch=payload.batch,
        department=payload.department,
        section=payload.section,
        semester=payload.semester,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return _build_class_out(tc)


@router.get("", response_model=List[TeacherClassOut])
def list_classes(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """List teacher classes, prioritizing the user's classes if logged in."""
    query = db.query(TeacherClass)
    if current_user:
        query = query.filter(
            or_(
                TeacherClass.user_id == current_user.id,
                TeacherClass.user_id.is_(None),
            )
        )
    classes = query.order_by(TeacherClass.created_at.desc()).all()
    return [_build_class_out(tc) for tc in classes]



@router.get("/{class_id}", response_model=TeacherClassOut)
def get_class(class_id: int, db: Session = Depends(get_db)):
    tc = db.query(TeacherClass).filter(TeacherClass.id == class_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Class not found.")
    return _build_class_out(tc)


@router.get("/{class_id}/progress", response_model=List[TopicProgressOut])
def get_class_progress(class_id: int, db: Session = Depends(get_db)):
    """Get all topics with completion status for a class."""
    tc = db.query(TeacherClass).filter(TeacherClass.id == class_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Class not found.")

    subject = tc.subject
    progress_map = {tp.topic_id: tp for tp in tc.topic_progress}

    result = []
    for unit in sorted(subject.units, key=lambda u: u.unit_number):
        for topic in sorted(unit.topics, key=lambda t: t.topic_order):
            tp = progress_map.get(topic.id)
            result.append(
                TopicProgressOut(
                    id=tp.id if tp else 0,
                    topic_id=topic.id,
                    topic_name=topic.topic_name,
                    unit_id=unit.id,
                    unit_title=unit.unit_title,
                    unit_number=unit.unit_number,
                    topic_order=topic.topic_order,
                    is_completed=tp.is_completed if tp else False,
                    completed_at=tp.completed_at if tp else None,
                )
            )

    return result


@router.patch("/{class_id}/topics/{topic_id}/progress", response_model=TopicProgressOut)
def toggle_topic_progress(
    class_id: int,
    topic_id: int,
    payload: ToggleProgressRequest,
    db: Session = Depends(get_db),
):
    """Mark a topic as completed or not completed."""
    tc = db.query(TeacherClass).filter(TeacherClass.id == class_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Class not found.")

    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found.")

    unit = db.query(Unit).filter(Unit.id == topic.unit_id).first()

    # Find or create TopicProgress record
    tp = (
        db.query(TopicProgress)
        .filter(
            TopicProgress.teacher_class_id == class_id,
            TopicProgress.topic_id == topic_id,
        )
        .first()
    )

    if tp is None:
        tp = TopicProgress(
            teacher_class_id=class_id,
            topic_id=topic_id,
            is_completed=payload.is_completed,
            completed_at=datetime.now(timezone.utc) if payload.is_completed else None,
        )
        db.add(tp)
    else:
        tp.is_completed = payload.is_completed
        tp.completed_at = datetime.now(timezone.utc) if payload.is_completed else None

    db.commit()
    db.refresh(tp)

    return TopicProgressOut(
        id=tp.id,
        topic_id=topic.id,
        topic_name=topic.topic_name,
        unit_id=unit.id,
        unit_title=unit.unit_title,
        unit_number=unit.unit_number,
        topic_order=topic.topic_order,
        is_completed=tp.is_completed,
        completed_at=tp.completed_at,
    )


@router.delete("/{class_id}")
def delete_class(class_id: int, db: Session = Depends(get_db)):
    tc = db.query(TeacherClass).filter(TeacherClass.id == class_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Class not found.")
    db.delete(tc)
    db.commit()
    return {"message": "Class deleted successfully."}
