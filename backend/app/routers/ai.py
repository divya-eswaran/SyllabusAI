"""Router for the RAG AI Teaching Assistant chatbot."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.services.rag_service import chat_with_rag

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    RAG-powered chat endpoint.
    Retrieves relevant syllabus context and calls Gemini for a grounded response.
    """
    if not payload.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    reply = await chat_with_rag(
        db=db,
        teacher_class_id=payload.teacher_class_id,
        topic_id=payload.topic_id,
        messages=[m.model_dump() for m in payload.messages],
    )

    return ChatResponse(reply=reply)
