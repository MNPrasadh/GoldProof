"""Assistant, OCR, and Passport schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class AssistantQuestionRequest(BaseModel):
    transaction_id: str
    question: str = Field(min_length=1, max_length=1000)
    language: Optional[Literal["en", "ta"]] = None


class AssistantQuestionResponse(BaseModel):
    transaction_id: str
    transaction_code: str
    language: str
    answer: str
    citations: list[str]
    missing_information: list[str]
    provider_mode: str
    is_external_llm: bool


class IssuePassportRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=300)
