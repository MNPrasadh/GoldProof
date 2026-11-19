"""Digital Gold Passport creation, canonical hashing, Ed25519 signing, and public verification."""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.core.crypto import (
    canonical_json,
    compute_sha256_hex,
    generate_qr_data_uri,
    sign_hash_ed25519,
    verify_hash_ed25519,
)
from app.models.entities import DigitalPassport, Transaction, User
from app.services.audit_service import record_audit_event

VERIFICATION_SCOPE_NOTICE = (
    "A valid Ed25519 signature proves this signed Digital Gold Passport has not been altered since "
    "signing. It does not independently verify the physical truthfulness of manually entered weights "
    "or purity readings."
)


def mask_mobile(mobile: Optional[str]) -> str:
    if not mobile:
        return "Not provided"
    clean = mobile.strip()
    if len(clean) <= 4:
        return "****"
    return ("*" * max(len(clean) - 4, 4)) + clean[-4:]


def build_canonical_passport_payload(tx: Transaction) -> dict[str, Any]:
    """Construct the canonical JSON-serializable payload from current transaction state."""
    if tx.measurement_record is None or tx.rate_record is None or tx.valuation_result is None:
        raise ValueError("Transaction is missing measurement, rate, or valuation records.")

    sorted_items = sorted(tx.jewellery_items, key=lambda i: i.item_description)
    sorted_deductions = sorted(
        tx.deductions,
        key=lambda d: (d.deduction_type, d.label, str(d.amount_inr)),
    )
    sorted_acks = sorted(tx.acknowledgements, key=lambda a: a.party_role)

    return {
        "schema_version": "1.0",
        "transaction_code": tx.transaction_code,
        "version_number": tx.version_number,
        "parent_transaction_id": tx.parent_transaction_id,
        "is_demo": bool(tx.is_demo),
        "jeweller": {
            "shop_name": tx.jeweller.shop_name if tx.jeweller else "Unknown Shop",
            "shop_code": tx.jeweller.shop_code if tx.jeweller else "",
            "city": tx.jeweller.city if tx.jeweller else "",
            "state": tx.jeweller.state if tx.jeweller else "",
            "bis_hallmark_license": tx.jeweller.bis_hallmark_license if tx.jeweller else None,
        },
        "customer": {
            "display_name": tx.customer_profile.full_name if tx.customer_profile else "Customer",
            "masked_mobile": mask_mobile(tx.customer_profile.mobile_number if tx.customer_profile else None),
        },
        "jewellery_items": [
            {
                "item_description": item.item_description,
                "category": item.category,
                "hallmark_huid": item.hallmark_huid,
                "stone_or_non_gold_description": item.stone_or_non_gold_description,
            }
            for item in sorted_items
        ],
        "measurement": {
            "gross_weight_g": tx.measurement_record.gross_weight_g,
            "non_gold_weight_g": tx.measurement_record.non_gold_weight_g,
            "net_gold_weight_g": tx.measurement_record.net_gold_weight_g,
            "purity_pct": tx.measurement_record.purity_pct,
            "purity_karat_label": tx.measurement_record.purity_karat_label,
            "measurement_source": tx.measurement_record.measurement_source,
            "instrument_name": tx.measurement_record.instrument_name,
            "test_report_ref": tx.measurement_record.test_report_ref,
            "measured_at": tx.measurement_record.measured_at,
            "ocr_extracted": bool(tx.measurement_record.ocr_extracted),
        },
        "rate": {
            "rate_24k_per_g": tx.rate_record.rate_24k_per_g,
            "rate_source": tx.rate_record.rate_source,
            "rate_timestamp": tx.rate_record.rate_timestamp,
            "is_simulated_rate": bool(tx.rate_record.is_simulated_rate),
        },
        "deductions": [
            {
                "deduction_type": d.deduction_type,
                "label": d.label,
                "amount_inr": d.amount_inr,
                "percentage_of_gross": d.percentage_of_gross,
                "reason": d.reason or "",
                "supporting_doc_ref": d.supporting_doc_ref,
            }
            for d in sorted_deductions
        ],
        "valuation": {
            "pure_gold_weight_g": tx.valuation_result.pure_gold_weight_g,
            "gross_reference_value_inr": tx.valuation_result.gross_reference_value_inr,
            "total_deductions_inr": tx.valuation_result.total_deductions_inr,
            "calculated_net_value_inr": tx.valuation_result.calculated_net_value_inr,
            "jeweller_offered_value_inr": tx.valuation_result.jeweller_offered_value_inr,
            "offer_difference_inr": tx.valuation_result.offer_difference_inr,
            "offer_difference_explanation": tx.valuation_result.offer_difference_explanation or "",
        },
        "acknowledgements": [
            {
                "party_role": ack.party_role,
                "acknowledged_by_name": ack.acknowledged_by_name,
                "acknowledged_at": ack.acknowledged_at,
                "method": ack.method,
            }
            for ack in sorted_acks
        ],
        "verification_scope_notice": VERIFICATION_SCOPE_NOTICE,
    }


def _load_full_transaction_by_code(db: Session, transaction_code: str) -> Optional[Transaction]:
    return (
        db.query(Transaction)
        .options(
            joinedload(Transaction.jeweller),
            joinedload(Transaction.customer_profile),
            joinedload(Transaction.jewellery_items),
            joinedload(Transaction.measurement_record),
            joinedload(Transaction.rate_record),
            joinedload(Transaction.deductions),
            joinedload(Transaction.valuation_result),
            joinedload(Transaction.anomaly_flags),
            joinedload(Transaction.acknowledgements),
            joinedload(Transaction.digital_passport),
        )
        .filter(Transaction.transaction_code == transaction_code)
        .first()
    )


def issue_digital_passport(
    db: Session,
    tx: Transaction,
    actor_user: Optional[User],
    require_jeweller_ack: bool = True,
    signed_at: Optional[datetime] = None,
) -> DigitalPassport:
    """Create canonical JSON, SHA-256 hash, and Ed25519 signature for a transaction."""
    if tx.digital_passport is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A signed Digital Gold Passport already exists for this transaction version.",
        )
    if tx.status == "amended":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot sign a superseded transaction. Sign the latest amended version instead.",
        )

    ack_roles = {a.party_role for a in tx.acknowledgements}
    if require_jeweller_ack and "jeweller" not in ack_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeweller acknowledgement is required before issuing a Digital Gold Passport.",
        )

    previous_passport_hash: Optional[str] = None
    if tx.parent_transaction_id:
        parent_passport = (
            db.query(DigitalPassport)
            .filter(DigitalPassport.transaction_id == tx.parent_transaction_id)
            .first()
        )
        if parent_passport is not None:
            previous_passport_hash = parent_passport.payload_sha256

    payload_dict = build_canonical_passport_payload(tx)
    canonical_str = canonical_json(payload_dict)
    sha256_hex = compute_sha256_hex(canonical_str)
    sig_b64, pub_b64, fingerprint = sign_hash_ed25519(sha256_hex)

    settings = get_settings()
    verification_url = f"{settings.APP_PUBLIC_URL.rstrip('/')}/verify/{tx.transaction_code}"

    passport = DigitalPassport(
        transaction_id=tx.id,
        transaction_code=tx.transaction_code,
        version_number=tx.version_number,
        previous_passport_hash=previous_passport_hash,
        canonical_payload_json=canonical_str,
        payload_sha256=sha256_hex,
        signature_algorithm="Ed25519",
        signature_b64=sig_b64,
        public_key_b64=pub_b64,
        public_key_fingerprint=fingerprint,
        verification_url=verification_url,
        signed_at=(signed_at or datetime.now(timezone.utc)).replace(microsecond=0),
        is_revoked_by_amendment=False,
    )
    tx.status = "signed"
    db.add(passport)
    db.flush()

    record_audit_event(
        db=db,
        action="DIGITAL_PASSPORT_ISSUED",
        actor_user=actor_user,
        transaction_id=tx.id,
        jeweller_id=tx.jeweller_id,
        details={
            "transaction_code": tx.transaction_code,
            "version_number": tx.version_number,
            "payload_sha256": sha256_hex,
            "public_key_fingerprint": fingerprint,
            "acknowledgements": sorted(ack_roles),
        },
        created_at=passport.signed_at,
    )
    return passport


def verify_digital_passport(db: Session, transaction_code: str) -> dict[str, Any]:
    """Verify Ed25519 signature, stored SHA-256 hash, and live database integrity."""
    tx = _load_full_transaction_by_code(db, transaction_code)
    if tx is None or tx.digital_passport is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No signed Digital Gold Passport found for code '{transaction_code}'.",
        )

    passport = tx.digital_passport

    # 1. Verify hash of stored canonical payload matches passport.payload_sha256
    recomputed_stored_hash = compute_sha256_hex(passport.canonical_payload_json)
    hash_matches_stored = recomputed_stored_hash == passport.payload_sha256

    # 2. Verify Ed25519 signature over stored payload_sha256
    signature_valid = verify_hash_ed25519(
        passport.payload_sha256,
        passport.signature_b64,
        passport.public_key_b64,
    )

    # 3. Verify live relational DB rows still hash to the signed payload hash
    current_canonical = canonical_json(build_canonical_passport_payload(tx))
    current_db_hash = compute_sha256_hex(current_canonical)
    matches_current_db = current_db_hash == passport.payload_sha256

    # Check if an amended child version exists
    child_tx = (
        db.query(Transaction)
        .filter(Transaction.parent_transaction_id == tx.id)
        .order_by(Transaction.version_number.desc())
        .first()
    )

    if not (signature_valid and hash_matches_stored and matches_current_db):
        integrity_status = "tampered"
        integrity_message = (
            "Integrity mismatch detected: the stored transaction data or canonical digest does not "
            "match the Ed25519 signature."
        )
    elif passport.is_revoked_by_amendment or tx.status == "amended":
        integrity_status = "superseded_by_amendment"
        integrity_message = (
            "Cryptographic signature is valid for this historical version, which has been superseded "
            "by a newer linked amendment."
        )
    else:
        integrity_status = "verified"
        integrity_message = (
            "Cryptographic verification passed: Ed25519 signature is valid and the transaction record "
            "matches the exact state at signing."
        )

    parent_code: Optional[str] = None
    if tx.parent_transaction_id:
        parent_tx = db.query(Transaction).filter(Transaction.id == tx.parent_transaction_id).first()
        parent_code = parent_tx.transaction_code if parent_tx else None

    return {
        "transaction_code": tx.transaction_code,
        "version_number": tx.version_number,
        "transaction_status": tx.status,
        "is_demo": bool(tx.is_demo),
        "integrity_status": integrity_status,
        "integrity_message": integrity_message,
        "signature_valid": signature_valid,
        "hash_matches_stored_payload": hash_matches_stored,
        "matches_current_db_record": matches_current_db,
        "payload_sha256": passport.payload_sha256,
        "current_db_sha256": current_db_hash,
        "previous_passport_hash": passport.previous_passport_hash,
        "signature_algorithm": passport.signature_algorithm,
        "signature_b64": passport.signature_b64,
        "public_key_b64": passport.public_key_b64,
        "public_key_fingerprint": passport.public_key_fingerprint,
        "signed_at": passport.signed_at,
        "verification_url": passport.verification_url,
        "qr_data_uri": generate_qr_data_uri(passport.verification_url),
        "verification_scope_notice": VERIFICATION_SCOPE_NOTICE,
        "parent_transaction_code": parent_code,
        "amended_by_transaction_code": child_tx.transaction_code if child_tx else None,
        "jeweller": {
            "shop_name": tx.jeweller.shop_name,
            "shop_code": tx.jeweller.shop_code,
            "city": tx.jeweller.city,
            "state": tx.jeweller.state,
            "bis_hallmark_license": tx.jeweller.bis_hallmark_license,
        },
        "customer_display": {
            "full_name": tx.customer_profile.full_name,
            "masked_mobile": mask_mobile(tx.customer_profile.mobile_number),
        },
        "jewellery_items": [
            {
                "item_description": i.item_description,
                "category": i.category,
                "hallmark_huid": i.hallmark_huid,
                "stone_or_non_gold_description": i.stone_or_non_gold_description,
            }
            for i in tx.jewellery_items
        ],
        "measurement": {
            "gross_weight_g": str(tx.measurement_record.gross_weight_g),
            "non_gold_weight_g": str(tx.measurement_record.non_gold_weight_g),
            "net_gold_weight_g": str(tx.measurement_record.net_gold_weight_g),
            "purity_pct": str(tx.measurement_record.purity_pct),
            "purity_karat_label": tx.measurement_record.purity_karat_label,
            "measurement_source": tx.measurement_record.measurement_source,
            "instrument_name": tx.measurement_record.instrument_name,
            "test_report_ref": tx.measurement_record.test_report_ref,
            "measured_at": tx.measurement_record.measured_at,
        },
        "rate": {
            "rate_24k_per_g": str(tx.rate_record.rate_24k_per_g),
            "rate_source": tx.rate_record.rate_source,
            "rate_timestamp": tx.rate_record.rate_timestamp,
            "is_simulated_rate": bool(tx.rate_record.is_simulated_rate),
        },
        "deductions": [
            {
                "deduction_type": d.deduction_type,
                "label": d.label,
                "amount_inr": str(d.amount_inr),
                "percentage_of_gross": str(d.percentage_of_gross),
                "reason": d.reason,
                "supporting_doc_ref": d.supporting_doc_ref,
            }
            for d in tx.deductions
        ],
        "valuation": {
            "pure_gold_weight_g": str(tx.valuation_result.pure_gold_weight_g),
            "gross_reference_value_inr": str(tx.valuation_result.gross_reference_value_inr),
            "total_deductions_inr": str(tx.valuation_result.total_deductions_inr),
            "calculated_net_value_inr": str(tx.valuation_result.calculated_net_value_inr),
            "jeweller_offered_value_inr": str(tx.valuation_result.jeweller_offered_value_inr),
            "offer_difference_inr": str(tx.valuation_result.offer_difference_inr),
            "offer_difference_explanation": tx.valuation_result.offer_difference_explanation,
            "calculation_steps": tx.valuation_result.calculation_steps_json,
        },
        "acknowledgements": [
            {
                "party_role": a.party_role,
                "acknowledged_by_name": a.acknowledged_by_name,
                "acknowledged_at": a.acknowledged_at,
                "method": a.method,
            }
            for a in tx.acknowledgements
        ],
        "anomaly_summary": [
            {
                "detection_method": f.detection_method,
                "code": f.code,
                "severity": f.severity,
                "title": f.title,
                "message": f.message,
            }
            for f in tx.anomaly_flags
        ],
    }
