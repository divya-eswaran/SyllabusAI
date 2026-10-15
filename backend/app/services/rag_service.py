"""
RAG Service — retrieves relevant syllabus context and streams a response
from Google Gemini, grounded in the teacher's actual syllabus content.
"""

import json
import logging
import numpy as np
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Subject, Unit, Topic, SyllabusChunk, TeacherClass

logger = logging.getLogger(__name__)

# Lazy-loaded globals (avoid slow import at startup)
_embedding_model = None
_gemini_client = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(settings.embedding_model)
        logger.info(f"Embedding model '{settings.embedding_model}' loaded")
    return _embedding_model


def _get_groq():
    global _gemini_client
    if _gemini_client is None:
        from groq import Groq
        _gemini_client = Groq(api_key=settings.groq_api_key)
    return _gemini_client


def embed_text(text: str) -> list[float]:
    model = _get_embedding_model()
    emb = model.encode(text, normalize_embeddings=True)
    return emb.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-10))


def build_syllabus_chunks(subject_id: int, db: Optional[Session] = None) -> None:
    """
    Build and store syllabus chunks + embeddings for a subject.
    Called once after PDF import.
    """
    from app.database import SessionLocal
    own_db = False
    if db is None:
        db = SessionLocal()
        own_db = True

    try:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            return

        # Clear existing chunks
        db.query(SyllabusChunk).filter(SyllabusChunk.subject_id == subject_id).delete()

        chunks_to_add = []

        # Objectives
        if subject.course_objectives:
            for obj in subject.course_objectives:
                chunks_to_add.append(
                    SyllabusChunk(
                        subject_id=subject_id,
                        chunk_text=f"Course Objective: {obj}",
                        chunk_type="objective",
                        embedding=embed_text(obj),
                    )
                )

        # Outcomes
        if subject.course_outcomes:
            for co in subject.course_outcomes:
                text = f"{co.get('code', '')}: {co.get('description', '')}"
                chunks_to_add.append(
                    SyllabusChunk(
                        subject_id=subject_id,
                        chunk_text=f"Course Outcome {text}",
                        chunk_type="outcome",
                        embedding=embed_text(text),
                    )
                )

        # Units and topics
        for unit in subject.units:
            unit_header = f"Unit {unit.unit_number}: {unit.unit_title}"
            topic_names = [t.topic_name for t in unit.topics]
            unit_chunk = f"{unit_header}\nTopics: {', '.join(topic_names)}"
            chunks_to_add.append(
                SyllabusChunk(
                    subject_id=subject_id,
                    unit_id=unit.id,
                    chunk_text=unit_chunk,
                    chunk_type="unit",
                    embedding=embed_text(unit_chunk),
                )
            )

            for topic in unit.topics:
                chunk_text = f"{unit_header} > {topic.topic_name}"
                chunks_to_add.append(
                    SyllabusChunk(
                        subject_id=subject_id,
                        unit_id=unit.id,
                        chunk_text=chunk_text,
                        chunk_type="topic",
                        embedding=embed_text(chunk_text),
                    )
                )

        db.add_all(chunks_to_add)
        db.commit()
        logger.info(f"Built {len(chunks_to_add)} chunks for subject {subject_id}")
    except Exception as e:
        logger.error(f"Error building syllabus chunks for subject {subject_id}: {e}")
    finally:
        if own_db:
            db.close()



def retrieve_context(
    db: Session,
    subject_id: int,
    topic_id: int,
    query: str,
    top_k: int = 8,
) -> str:
    """
    Retrieve the most relevant syllabus chunks for a query via cosine similarity.
    Always includes the target topic's unit context.
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        return ""

    unit = db.query(Unit).filter(Unit.id == topic.unit_id).first()

    # Build query embedding
    query_embedding = embed_text(f"{topic.topic_name} {query}")

    # Load all chunks for this subject
    chunks = db.query(SyllabusChunk).filter(SyllabusChunk.subject_id == subject_id).all()

    # Score by similarity
    scored = []
    for chunk in chunks:
        if chunk.embedding:
            score = cosine_similarity(query_embedding, chunk.embedding)
            scored.append((score, chunk.chunk_text))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [text for _, text in scored[:top_k]]

    # Prepend unit context always
    if unit:
        unit_ctx = f"Unit {unit.unit_number}: {unit.unit_title}"
        if unit_ctx not in top_chunks:
            top_chunks.insert(0, unit_ctx)

    return "\n".join(top_chunks)


def build_system_prompt(
    subject_name: str,
    subject_code: str,
    unit_title: str,
    topic_name: str,
    syllabus_context: str,
    teacher_class_info: Optional[str] = None,
) -> str:
    return f"""You are an expert AI teaching assistant helping a university professor prepare for their class.

Subject: {subject_name} ({subject_code})
Unit: {unit_title}
Topic: {topic_name}

{f"Class Info: {teacher_class_info}" if teacher_class_info else ""}

Below is the relevant syllabus content for context:
---
{syllabus_context}
---

Your role is to help the teacher:
- Create detailed lesson plans (timing, activities, explanations)
- Generate examples, analogies, and demonstrations suitable for university students
- Create quiz questions and assessments
- Suggest board notes and visual aids
- Connect this topic to prerequisites and upcoming topics from the syllabus
- Suggest teaching strategies appropriate to the course level

Always base your responses on the syllabus content provided. Be specific, practical, and educator-focused.
"""


async def chat_with_rag(
    db: Session,
    teacher_class_id: int,
    topic_id: int,
    messages: list[dict],
) -> str:
    """
    Main RAG chat function: retrieves context from DB, builds a grounded prompt,
    and calls Gemini to generate a response.
    """
    teacher_class = db.query(TeacherClass).filter(TeacherClass.id == teacher_class_id).first()
    if not teacher_class:
        return "Teacher class not found."

    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        return "Topic not found."

    unit = db.query(Unit).filter(Unit.id == topic.unit_id).first()
    subject = db.query(Subject).filter(Subject.id == teacher_class.subject_id).first()

    if not subject or not unit:
        return "Subject or unit data missing."

    # Use the last user message as the query for retrieval
    last_user_message = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            last_user_message = msg["content"]
            break

    # Retrieve relevant syllabus context
    context = retrieve_context(db, subject.id, topic_id, last_user_message)

    # Build class info string
    class_info = f"Batch: {teacher_class.batch}, Department: {teacher_class.department}, Section: {teacher_class.section}"

    # Build system prompt
    system_prompt = build_system_prompt(
        subject_name=subject.subject_name,
        subject_code=subject.subject_code,
        unit_title=unit.unit_title,
        topic_name=topic.topic_name,
        syllabus_context=context,
        teacher_class_info=class_info,
    )

    try:
        client = _get_groq()

        # Build conversation history in OpenAI-compatible format
        chat_messages = [
            {"role": "system", "content": system_prompt},
        ]
        for msg in messages[:-1]:  # all but last
            role = "user" if msg["role"] == "user" else "assistant"
            chat_messages.append({"role": role, "content": msg["content"]})
        chat_messages.append({"role": "user", "content": last_user_message})

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=chat_messages,
            max_tokens=2048,
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            return "⚠️ Groq API key not configured. Please check your GROQ_API_KEY in the backend/.env file."
        return f"AI service error: {str(e)}"
