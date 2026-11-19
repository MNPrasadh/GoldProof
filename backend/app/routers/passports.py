"""Digital Gold Passport issuance, public verification, and QR image endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.crypto import generate_qr_png_bytes
from app.core.security import assert_transaction_access, require_roles
from app.database import get_db
from app.models.entities import DigitalPassport, User
from app.schemas.assistant import IssuePassportRequest
from app.services.passport_service import issue_digital_passport, verify_digital_passport
from app.services.transaction_service import load_transaction_full, serialize_transaction_detail

router = APIRouter(prefix="/api/passports", tags=["Digital Gold Passports"])


@router.post("/{tx_id}/issue")
def issue_passport_endpoint(
    tx_id: str,
    payload: IssuePassportRequest | None = None,
    current_user: User = Depends(require_roles("jeweller")),
    db: Session = Depends(get_db),
):
    """Sign canonical transaction record with Ed25519 and generate QR Digital Gold Passport."""
    tx = load_transaction_full(db, tx_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    assert_transaction_access(db, current_user, tx)

    issue_digital_passport(db=db, tx=tx, actor_user=current_user, require_jeweller_ack=True)
    db.commit()
    refreshed = load_transaction_full(db, tx.id)
    return serialize_transaction_detail(db, refreshed)  # type: ignore[arg-type]


@router.get("/verify/{transaction_code}")
def public_verify_passport(transaction_code: str, db: Session = Depends(get_db)):
    """Public verification endpoint for QR code scans and transaction lookup."""
    return verify_digital_passport(db, transaction_code.strip())


@router.get("/{transaction_code}/qr.png")
def public_passport_qr_png(transaction_code: str, db: Session = Depends(get_db)):
    """Serve QR code PNG encoding the public passport verification URL."""
    passport = (
        db.query(DigitalPassport)
        .filter(DigitalPassport.transaction_code == transaction_code.strip())
        .first()
    )
    if passport is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital Gold Passport '{transaction_code}' not found.",
        )
    png_bytes = generate_qr_png_bytes(passport.verification_url)
    return Response(content=png_bytes, media_type="image/png")
