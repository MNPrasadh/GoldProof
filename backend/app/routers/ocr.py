"""Document OCR extraction router with mandatory human confirmation."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.security import require_roles
from app.models.entities import User
from app.services.ocr_service import run_ocr_extraction

router = APIRouter(prefix="/api/ocr", tags=["OCR & Document Intelligence"])

ALLOWED_DOC_TYPES = {"handwritten_register", "paper_receipt", "assay_report", "valuation_document"}


@router.post("/extract")
async def extract_document_fields(
    file: UploadFile = File(...),
    document_type: str = Form(default="paper_receipt"),
    current_user: User = Depends(require_roles("jeweller", "admin")),
):
    """Extract fields from an uploaded register/receipt/assay image for human confirmation."""
    if document_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"document_type must be one of: {', '.join(sorted(ALLOWED_DOC_TYPES))}",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 10 MB limit.")

    return run_ocr_extraction(
        file_bytes=content,
        filename=file.filename or "upload.png",
        document_type=document_type,
    )
