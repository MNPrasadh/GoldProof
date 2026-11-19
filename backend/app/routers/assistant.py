"""Tamil & English Voice-First AI Assistant and Speech capability router."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import assert_transaction_access, get_current_user
from app.database import get_db
from app.models.entities import User
from app.schemas.assistant import AssistantQuestionRequest, AssistantQuestionResponse
from app.services.assistant_service import answer_transaction_question
from app.services.speech_service import get_speech_capabilities
from app.services.transaction_service import load_transaction_full

router = APIRouter(prefix="/api/assistant", tags=["Tamil & English Assistant"])


@router.post("/ask", response_model=AssistantQuestionResponse)
async def ask_assistant(
    payload: AssistantQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Answer a Tamil or English question grounded strictly in the transaction's database evidence."""
    tx = load_transaction_full(db, payload.transaction_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    assert_transaction_access(db, current_user, tx)

    result = await answer_transaction_question(
        tx=tx,
        question=payload.question,
        requested_language=payload.language,
    )
    return AssistantQuestionResponse(**result)


@router.get("/capabilities")
def assistant_capabilities():
    """Return active speech and LLM provider configuration status."""
    return get_speech_capabilities()
