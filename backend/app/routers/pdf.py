"""Router for PDF upload and syllabus import."""

import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UploadResponse, SubjectSummary
from app.models import Subject, Unit, Topic, SyllabusChunk, TopicProgress
from app.services.pdf_service import process_pdf
from app.services.rag_service import build_syllabus_chunks

router = APIRouter(prefix="/api/pdf", tags=["PDF"])
logger = logging.getLogger(__name__)

def _save_subjects_to_db(db: Session, subjects_data: list[dict]) -> list[Subject]:
    """Persist parsed subjects to the database, updating existing subjects."""
    saved = []

    for data in subjects_data:
        existing = db.query(Subject).filter(
            Subject.subject_code == data["subject_code"]
        ).first()

        if existing:
            logger.info(
                f"Subject {data['subject_code']} already exists, updating"
            )

            subject = existing

            # Update subject information
            subject.subject_name = data["subject_name"]
            subject.semester = data.get("semester")
            subject.credits = data.get("credits")
            subject.lecture_hours = data.get("lecture_hours")
            subject.tutorial_hours = data.get("tutorial_hours")
            subject.practical_hours = data.get("practical_hours")
            subject.course_type = data.get("course_type")
            subject.course_objectives = data.get("course_objectives", [])
            subject.course_outcomes = data.get("course_outcomes", [])

            # Get old units
            old_units = list(subject.units)
            old_unit_ids = [unit.id for unit in old_units]

            # Delete RAG chunks that reference old units
            if old_unit_ids:
                db.query(SyllabusChunk).filter(
                    SyllabusChunk.unit_id.in_(old_unit_ids)
                ).delete(synchronize_session=False)

            # Get old topic IDs
            old_topic_ids = []

            for unit in old_units:
                for topic in unit.topics:
                    old_topic_ids.append(topic.id)

            # Delete progress records for old topics
            if old_topic_ids:
                db.query(TopicProgress).filter(
                    TopicProgress.topic_id.in_(old_topic_ids)
                ).delete(synchronize_session=False)

            # Delete old units.
            # Because Unit.topics has delete-orphan,
            # deleting the units also deletes their topics.
            for old_unit in old_units:
                db.delete(old_unit)

            db.flush()

        else:
            subject = Subject(
                subject_code=data["subject_code"],
                subject_name=data["subject_name"],
                semester=data.get("semester"),
                credits=data.get("credits"),
                lecture_hours=data.get("lecture_hours"),
                tutorial_hours=data.get("tutorial_hours"),
                practical_hours=data.get("practical_hours"),
                course_type=data.get("course_type"),
                course_objectives=data.get("course_objectives", []),
                course_outcomes=data.get("course_outcomes", []),
            )

            db.add(subject)
            db.flush()

        # Create new units
        for unit_data in data.get("units", []):
            unit = Unit(
                subject_id=subject.id,
                unit_number=unit_data["unit_number"],
                unit_title=unit_data["unit_title"],
                description=unit_data.get("description"),
                hours=unit_data.get("hours"),
            )

            db.add(unit)
            db.flush()

            # Create new topics
            for order, topic_name in enumerate(
                unit_data.get("topics", []),
                start=1
            ):
                topic = Topic(
                    unit_id=unit.id,
                    topic_order=order,
                    topic_name=topic_name,
                )

                db.add(topic)

        db.commit()
        db.refresh(subject)
        saved.append(subject)

    return saved

def _build_summary(subject: Subject) -> SubjectSummary:
    total_topics = sum(len(u.topics) for u in subject.units)
    return SubjectSummary(
        id=subject.id,
        subject_code=subject.subject_code,
        subject_name=subject.subject_name,
        semester=subject.semester,
        credits=subject.credits,
        course_type=subject.course_type,
        unit_count=len(subject.units),
        topic_count=total_topics,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Parse PDF
        # Parse PDF
    try:
        subjects_data = await process_pdf(pdf_bytes)

        print("\n========== PDF PARSER DEBUG ==========")
        print("Subjects extracted:", len(subjects_data))

        for subject in subjects_data:
            total_topics = sum(
                len(unit.get("topics", []))
                for unit in subject.get("units", [])
            )

            print(
                f"{subject['subject_code']} | "
                f"{subject['subject_name']} | "
                f"Units: {len(subject.get('units', []))} | "
                f"Topics: {total_topics}"
            )

            if subject["subject_code"] == "IT23C02":
                print("\n===== IT23C02 DETAILS =====")
                print("Name:", subject["subject_name"])
                print("Units:", len(subject.get("units", [])))

                for unit in subject.get("units", []):
                    print(
                        f"  Unit {unit['unit_number']}: "
                        f"{unit['unit_title']} | "
                        f"{len(unit.get('topics', []))} topics"
                    )

        print("=====================================\n")

    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse PDF: {str(e)}"
        )

    if not subjects_data:
        raise HTTPException(
            status_code=422,
            detail="No subjects detected in PDF. Ensure the PDF contains standard university syllabus formatting.",
        )

    # Save to DB
    created = _save_subjects_to_db(db, subjects_data)

    # Build RAG embeddings in background
    for subject in created:
        background_tasks.add_task(build_syllabus_chunks, subject.id)

    summaries = [_build_summary(s) for s in created]

    return UploadResponse(
        message=f"Successfully imported {len(created)} subject(s) from PDF.",
        subjects_created=len(created),
        subjects=summaries,
    )