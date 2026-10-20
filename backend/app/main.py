from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from sqlalchemy import text
from app.routers import pdf, subjects, classes, ai, auth

# Create all tables on startup
Base.metadata.create_all(bind=engine)
try:
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE teacher_classes ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS regulation VARCHAR(50) DEFAULT 'Regulation 2023';"
            )
        )
except Exception:
    pass

app = FastAPI(
    title="SyllabusAI API",
    description="Teacher-focused platform — converts university syllabi into structured, searchable databases with AI-powered class planning.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(pdf.router)
app.include_router(subjects.router)
app.include_router(classes.router)
app.include_router(ai.router)



@app.get("/")
def root():
    return {"message": "SyllabusAI API is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
