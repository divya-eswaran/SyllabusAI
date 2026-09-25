from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import pdf, subjects, classes, ai

# Create all tables on startup
Base.metadata.create_all(bind=engine)

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
