import json
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    ForeignKey,
    DateTime,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Subject(Base):
    """Official syllabus data extracted from PDF — never modified by AI."""

    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    subject_code = Column(String(50), unique=True, index=True, nullable=False)
    subject_name = Column(String(255), nullable=False, index=True)
    semester = Column(String(20))
    credits = Column(Integer)
    lecture_hours = Column(Integer)
    tutorial_hours = Column(Integer)
    practical_hours = Column(Integer)
    course_type = Column(String(100))
    department = Column(String(100))
    course_objectives = Column(JSON)  # list of strings
    course_outcomes = Column(JSON)   # list of dicts: {code, description}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    units = relationship("Unit", back_populates="subject", cascade="all, delete-orphan")
    teacher_classes = relationship("TeacherClass", back_populates="subject")


class Unit(Base):
    """A unit/module within a subject."""

    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    unit_number = Column(Integer, nullable=False)
    unit_title = Column(String(255), nullable=False)
    description = Column(Text)
    hours = Column(Integer)

    subject = relationship("Subject", back_populates="units")
    topics = relationship("Topic", back_populates="unit", cascade="all, delete-orphan")


class Topic(Base):
    """A single topic within a unit."""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    topic_order = Column(Integer, nullable=False)
    topic_name = Column(String(500), nullable=False)
    description = Column(Text)
    embedding = Column(JSON)  # stored as list of floats

    unit = relationship("Unit", back_populates="topics")
    progress_records = relationship("TopicProgress", back_populates="topic")


class SyllabusChunk(Base):
    """Chunked text from the syllabus for RAG retrieval."""

    __tablename__ = "syllabus_chunks"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    chunk_text = Column(Text, nullable=False)
    chunk_type = Column(String(50))  # 'topic', 'objective', 'outcome', 'description'
    embedding = Column(JSON)  # stored as list of floats
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TeacherClass(Base):
    """A class/batch that a teacher is currently handling."""

    __tablename__ = "teacher_classes"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    batch = Column(String(20))           # e.g. 2025-2029
    department = Column(String(100))
    section = Column(String(10))
    semester = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subject = relationship("Subject", back_populates="teacher_classes")
    topic_progress = relationship(
        "TopicProgress", back_populates="teacher_class", cascade="all, delete-orphan"
    )


class TopicProgress(Base):
    """Tracks completion of each topic per teacher class."""

    __tablename__ = "topic_progress"

    id = Column(Integer, primary_key=True, index=True)
    teacher_class_id = Column(Integer, ForeignKey("teacher_classes.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    teacher_class = relationship("TeacherClass", back_populates="topic_progress")
    topic = relationship("Topic", back_populates="progress_records")
