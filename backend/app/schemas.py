from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Topic ────────────────────────────────────────────────────────────────────

class TopicBase(BaseModel):
    topic_name: str
    topic_order: int
    description: Optional[str] = None


class TopicOut(TopicBase):
    id: int
    unit_id: int

    class Config:
        from_attributes = True


class UnitBase(BaseModel):
    unit_number: int
    unit_title: str
    description: Optional[str] = None
    hours: Optional[int] = None

    practicals: List[str] = []
    suggested_activities: List[str] = []
    suggested_evaluation_methods: List[str] = []

class UnitOut(UnitBase):
    id: int
    subject_id: int
    topics: List[TopicOut] = []

    class Config:
        from_attributes = True


# ─── Subject ──────────────────────────────────────────────────────────────────

class CourseOutcomeItem(BaseModel):
    code: str
    description: str


class SubjectBase(BaseModel):
    subject_code: str
    subject_name: str
    regulation: Optional[str] = "Regulation 2023"
    semester: Optional[str] = None
    credits: Optional[int] = None
    lecture_hours: Optional[int] = None
    tutorial_hours: Optional[int] = None
    practical_hours: Optional[int] = None
    course_type: Optional[str] = None
    department: Optional[str] = None
    course_objectives: Optional[List[str]] = []
    course_outcomes: Optional[List[dict]] = []


class SubjectCreate(SubjectBase):
    pass


class SubjectOut(SubjectBase):
    id: int
    units: List[UnitOut] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubjectSummary(BaseModel):
    id: int
    subject_code: str
    subject_name: str
    regulation: Optional[str] = "Regulation 2023"
    semester: Optional[str] = None
    credits: Optional[int] = None
    course_type: Optional[str] = None
    unit_count: int = 0
    topic_count: int = 0

    class Config:
        from_attributes = True


# ─── Teacher Class ─────────────────────────────────────────────────────────────

class TeacherClassCreate(BaseModel):
    subject_id: int
    batch: Optional[str] = None
    department: Optional[str] = None
    section: Optional[str] = None
    semester: Optional[str] = None


class TopicProgressOut(BaseModel):
    id: int
    topic_id: int
    topic_name: str
    unit_id: int
    unit_title: str
    unit_number: int
    topic_order: int
    is_completed: bool
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeacherClassOut(BaseModel):
    id: int
    subject_id: int
    subject_name: str
    subject_code: str
    batch: Optional[str] = None
    department: Optional[str] = None
    section: Optional[str] = None
    semester: Optional[str] = None
    total_topics: int = 0
    completed_topics: int = 0
    progress_percent: float = 0.0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Topic Progress ────────────────────────────────────────────────────────────

class ToggleProgressRequest(BaseModel):
    is_completed: bool


# ─── RAG / Chat ───────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # 'user' or 'model'
    content: str


class ChatRequest(BaseModel):
    teacher_class_id: int
    topic_id: int
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    context_used: Optional[str] = None


# ─── PDF Upload ────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    message: str
    subjects_created: int
    subjects: List[SubjectSummary] = []


# ─── Search & Semesters ─────────────────────────────────────────────────────────

class SemesterInfo(BaseModel):
    semester: str
    display_name: str
    count: int


class SearchResponse(BaseModel):
    results: List[SubjectSummary]
    total: int
    query: str
    detected_semester: Optional[str] = None


# ─── Auth / User ───────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    role: Optional[str] = "teacher"
    department: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
