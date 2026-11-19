"""Shared transaction lifecycle, valuation persistence, amendment, and serialization logic."""

import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.crypto import generate_qr_data_uri
from app.models.entities import (
    Acknowledgement,
    AnomalyFlag,
    AuditLog,
    ConsentRecord,
    CustomerProfile,
    Deduction,
    JewellerProfile,
    JewelleryItem,
    MeasurementRecord,
    RateRecord,
    Transaction,
    User,
    ValuationResult,
)
from app.schemas.transaction import TransactionCreateRequest
from app.services.audit_service import record_audit_event
from app.services.deduction_intelligence import evaluate_transaction_intelligence
from app.services.valuation import DeductionInput, calculate_valuation


def generate_transaction_code(is_demo: bool = False) -> str:
    year = datetime.now(timezone.utc).year
    suffix = secrets.token_hex(3).upper()
    prefix = "GP-DEMO" if is_demo else "GP"
    return f"{prefix}-{year}-{suffix}"


def load_transaction_full(db: Session, tx_id: str) -> Optional[Transaction]:
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
            joinedload(Transaction.consent_records),
        )
        .filter(Transaction.id == tx_id)
        .first()
    )


def _resolve_or_create_customer(
    db: Session,
    jeweller: JewellerProfile,
    full_name: str,
    mobile_number: str,
    preferred_language: str,
) -> tuple[CustomerProfile, Optional[str]]:
    clean_phone = mobile_number.strip()
    matched_user = db.query(User).filter(User.phone == clean_phone, User.role == "customer").first()

    profile = (
        db.query(CustomerProfile)
        .filter(
            CustomerProfile.jeweller_id == jeweller.id,
            CustomerProfile.mobile_number == clean_phone,
        )
        .first()
    )
    if profile is None:
        profile = CustomerProfile(
            user_id=matched_user.id if matched_user else None,
            jeweller_id=jeweller.id,
            full_name=full_name.strip(),
            mobile_number=clean_phone,
            preferred_language=preferred_language,
        )
        db.add(profile)
        db.flush()
    else:
        profile.full_name = full_name.strip()
        profile.preferred_language = preferred_language
        if matched_user and not profile.user_id:
            profile.user_id = matched_user.id
        db.flush()

    return profile, matched_user.id if matched_user else profile.user_id


def _apply_payload_to_transaction(
    db: Session,
    tx: Transaction,
    jeweller: JewellerProfile,
    actor_user: User,
    payload: TransactionCreateRequest,
) -> dict[str, Any]:
    """Compute valuation + intelligence and persist child records on a transaction."""
    deduction_inputs = [
        DeductionInput(
            deduction_type=d.deduction_type,
            label=d.label,
            amount_inr=d.amount_inr,
            reason=d.reason,
            supporting_doc_ref=d.supporting_doc_ref,
        )
        for d in payload.deductions
    ]

    valuation = calculate_valuation(
        gross_weight_g=payload.gross_weight_g,
        non_gold_weight_g=payload.non_gold_weight_g,
        net_gold_weight_g=payload.net_gold_weight_g,
        purity_pct=payload.purity_pct,
        rate_24k_per_g=payload.rate_24k_per_g,
        deductions=deduction_inputs,
        jeweller_offered_value_inr=payload.jeweller_offered_value_inr,
        offer_difference_explanation=payload.offer_difference_explanation,
        measurement_source=payload.measurement_source,
        rate_source=payload.rate_source,
        shop_conventions=jeweller.valuation_conventions,
    )

    intel = evaluate_transaction_intelligence(
        db=db,
        jeweller=jeweller,
        valuation=valuation,
        deductions=deduction_inputs,
        measurement_source=payload.measurement_source,
        instrument_name=payload.instrument_name,
        test_report_ref=payload.test_report_ref,
        benchmark_reference_rate_per_g=payload.benchmark_reference_rate_per_g,
        offer_difference_explanation=payload.offer_difference_explanation,
        exclude_transaction_id=tx.id,
        is_demo=payload.is_demo,
    )

    tx.status = "pending_review" if intel.requires_review else "pending_acknowledgement"
    tx.notes = payload.notes
    tx.is_demo = payload.is_demo
    if payload.client_updated_at:
        tx.client_updated_at = payload.client_updated_at

    # Replace child records cleanly on mutable draft/pending transactions
    tx.jewellery_items.clear()
    tx.deductions.clear()
    tx.anomaly_flags.clear()
    if tx.measurement_record is not None:
        db.delete(tx.measurement_record)
    if tx.rate_record is not None:
        db.delete(tx.rate_record)
    if tx.valuation_result is not None:
        db.delete(tx.valuation_result)
    db.flush()

    now = datetime.now(timezone.utc).replace(microsecond=0)

    db.add(
        JewelleryItem(
            transaction_id=tx.id,
            item_description=payload.item_description.strip(),
            category=payload.category,
            hallmark_huid=payload.hallmark_huid,
            stone_or_non_gold_description=payload.stone_or_non_gold_description,
        )
    )
    db.add(
        MeasurementRecord(
            transaction_id=tx.id,
            gross_weight_g=valuation.gross_weight_g,
            non_gold_weight_g=valuation.non_gold_weight_g,
            net_gold_weight_g=valuation.net_gold_weight_g,
            purity_pct=valuation.purity_pct,
            purity_karat_label=payload.purity_karat_label,
            measurement_source=payload.measurement_source,
            instrument_name=payload.instrument_name,
            test_report_ref=payload.test_report_ref,
            measured_at=(payload.measured_at or now).replace(microsecond=0),
            ocr_extracted=payload.ocr_extracted,
            ocr_confirmed_by_user_id=actor_user.id if payload.ocr_extracted else None,
        )
    )
    db.add(
        RateRecord(
            transaction_id=tx.id,
            rate_24k_per_g=valuation.rate_24k_per_g,
            rate_source=payload.rate_source.strip(),
            rate_timestamp=(payload.rate_timestamp or now).replace(microsecond=0),
            benchmark_reference_rate_per_g=payload.benchmark_reference_rate_per_g,
            is_simulated_rate=payload.is_simulated_rate or payload.measurement_source == "simulated_demo",
        )
    )
    for d_in, pct in zip(deduction_inputs, valuation.deduction_percentages):
        db.add(
            Deduction(
                transaction_id=tx.id,
                deduction_type=d_in.deduction_type,
                label=d_in.label,
                amount_inr=d_in.amount_inr,
                percentage_of_gross=pct,
                reason=d_in.reason,
                supporting_doc_ref=d_in.supporting_doc_ref,
            )
        )
    db.add(
        ValuationResult(
            transaction_id=tx.id,
            pure_gold_weight_g=valuation.pure_gold_weight_g,
            gross_reference_value_inr=valuation.gross_reference_value_inr,
            total_deductions_inr=valuation.total_deductions_inr,
            calculated_net_value_inr=valuation.calculated_net_value_inr,
            jeweller_offered_value_inr=valuation.jeweller_offered_value_inr,
            offer_difference_inr=valuation.offer_difference_inr,
            offer_difference_explanation=payload.offer_difference_explanation,
            assumptions_json=valuation.assumptions,
            calculation_steps_json=valuation.calculation_steps,
            computed_at=now,
        )
    )
    for flag in intel.flags:
        db.add(
            AnomalyFlag(
                transaction_id=tx.id,
                detection_method=flag.detection_method,
                code=flag.code,
                severity=flag.severity,
                title=flag.title,
                message=flag.message,
                evidence_json=flag.evidence,
            )
        )
    db.flush()
    return intel.ml_status


def create_transaction_record(
    db: Session,
    jeweller: JewellerProfile,
    actor_user: User,
    payload: TransactionCreateRequest,
    parent_transaction: Optional[Transaction] = None,
    amendment_reason: Optional[str] = None,
) -> Transaction:
    """Create and persist a complete gold exchange transaction with valuation, flags, consent, and audit."""
    customer_profile, customer_user_id = _resolve_or_create_customer(
        db=db,
        jeweller=jeweller,
        full_name=payload.customer_name,
        mobile_number=payload.customer_mobile,
        preferred_language=payload.customer_preferred_language,
    )

    version_num = (parent_transaction.version_number + 1) if parent_transaction else 1
    if parent_transaction:
        base_code = parent_transaction.transaction_code.split("-V")[0]
        tx_code = f"{base_code}-V{version_num}"
    else:
        tx_code = generate_transaction_code(is_demo=payload.is_demo)

    tx = Transaction(
        transaction_code=tx_code,
        jeweller_id=jeweller.id,
        customer_profile_id=customer_profile.id,
        customer_user_id=customer_user_id,
        status="pending_acknowledgement",
        version_number=version_num,
        parent_transaction_id=parent_transaction.id if parent_transaction else None,
        amendment_reason=amendment_reason,
        client_draft_id=payload.client_draft_id,
        client_updated_at=payload.client_updated_at,
        is_demo=payload.is_demo,
        notes=payload.notes,
        created_by_user_id=actor_user.id,
    )
    db.add(tx)
    db.flush()

    _apply_payload_to_transaction(db, tx, jeweller, actor_user, payload)

    db.add(
        ConsentRecord(
            transaction_id=tx.id,
            customer_profile_id=customer_profile.id,
            consent_type="transaction_recording",
            consent_granted=True,
            consent_text_version="v1.0-en-ta",
            captured_by_user_id=actor_user.id,
        )
    )
    db.flush()

    record_audit_event(
        db=db,
        action="TRANSACTION_AMENDED" if parent_transaction else "TRANSACTION_CREATED",
        actor_user=actor_user,
        transaction_id=tx.id,
        jeweller_id=jeweller.id,
        details={
            "transaction_code": tx.transaction_code,
            "version_number": tx.version_number,
            "parent_transaction_id": parent_transaction.id if parent_transaction else None,
            "amendment_reason": amendment_reason,
            "client_draft_id": payload.client_draft_id,
        },
    )
    db.commit()
    return load_transaction_full(db, tx.id)  # type: ignore[return-value]


def update_mutable_transaction(
    db: Session,
    tx: Transaction,
    jeweller: JewellerProfile,
    actor_user: User,
    payload: TransactionCreateRequest,
) -> Transaction:
    """Update an unsigned transaction; strictly rejects signed or amended records."""
    if tx.status in ("signed", "amended") or tx.digital_passport is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Signed transactions are immutable. Create a linked amendment instead of modifying "
                "the original record."
            ),
        )

    customer_profile, customer_user_id = _resolve_or_create_customer(
        db=db,
        jeweller=jeweller,
        full_name=payload.customer_name,
        mobile_number=payload.customer_mobile,
        preferred_language=payload.customer_preferred_language,
    )
    tx.customer_profile_id = customer_profile.id
    tx.customer_user_id = customer_user_id

    _apply_payload_to_transaction(db, tx, jeweller, actor_user, payload)

    record_audit_event(
        db=db,
        action="TRANSACTION_UPDATED",
        actor_user=actor_user,
        transaction_id=tx.id,
        jeweller_id=jeweller.id,
        details={"transaction_code": tx.transaction_code},
    )
    db.commit()
    return load_transaction_full(db, tx.id)  # type: ignore[return-value]


def record_acknowledgement(
    db: Session,
    tx: Transaction,
    actor_user: User,
    method: str,
    note: Optional[str],
) -> Transaction:
    """Record explicit jeweller or customer acknowledgement on a pre-signing transaction."""
    if tx.status in ("signed", "amended"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction is already signed or superseded and cannot be modified.",
        )
    if actor_user.role not in ("jeweller", "customer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only jeweller or customer parties can acknowledge a transaction.",
        )

    existing = (
        db.query(Acknowledgement)
        .filter(Acknowledgement.transaction_id == tx.id, Acknowledgement.party_role == actor_user.role)
        .first()
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if existing:
        existing.acknowledged_at = now
        existing.method = method
        existing.note = note
    else:
        db.add(
            Acknowledgement(
                transaction_id=tx.id,
                party_role=actor_user.role,
                acknowledged_by_user_id=actor_user.id,
                acknowledged_by_name=actor_user.full_name,
                acknowledged_at=now,
                method=method,
                note=note,
            )
        )
    db.flush()

    record_audit_event(
        db=db,
        action="PARTY_ACKNOWLEDGED",
        actor_user=actor_user,
        transaction_id=tx.id,
        jeweller_id=tx.jeweller_id,
        details={"party_role": actor_user.role, "method": method},
    )
    db.commit()
    return load_transaction_full(db, tx.id)  # type: ignore[return-value]


def serialize_transaction_summary(tx: Transaction) -> dict[str, Any]:
    m = tx.measurement_record
    v = tx.valuation_result
    first_item = tx.jewellery_items[0] if tx.jewellery_items else None
    review_flags = [f for f in tx.anomaly_flags if f.severity in ("review_required", "attention")]
    return {
        "id": tx.id,
        "transaction_code": tx.transaction_code,
        "status": tx.status,
        "version_number": tx.version_number,
        "is_demo": bool(tx.is_demo),
        "created_at": tx.created_at,
        "updated_at": tx.updated_at,
        "shop_name": tx.jeweller.shop_name if tx.jeweller else "",
        "customer_name": tx.customer_profile.full_name if tx.customer_profile else "",
        "item_description": first_item.item_description if first_item else "",
        "net_gold_weight_g": str(m.net_gold_weight_g) if m else "0.0000",
        "purity_pct": str(m.purity_pct) if m else "0.00",
        "purity_karat_label": m.purity_karat_label if m else "",
        "measurement_source": m.measurement_source if m else "manual",
        "total_deductions_inr": str(v.total_deductions_inr) if v else "0.00",
        "calculated_net_value_inr": str(v.calculated_net_value_inr) if v else "0.00",
        "jeweller_offered_value_inr": str(v.jeweller_offered_value_inr) if v else "0.00",
        "review_flag_count": len(review_flags),
        "has_passport": tx.digital_passport is not None,
        "acknowledgement_roles": sorted(a.party_role for a in tx.acknowledgements),
    }


def serialize_transaction_detail(db: Session, tx: Transaction) -> dict[str, Any]:
    parent_code = None
    if tx.parent_transaction_id:
        p = db.query(Transaction).filter(Transaction.id == tx.parent_transaction_id).first()
        parent_code = p.transaction_code if p else None

    child = (
        db.query(Transaction)
        .filter(Transaction.parent_transaction_id == tx.id)
        .order_by(Transaction.version_number.desc())
        .first()
    )
    tx_logs = (
        db.query(AuditLog)
        .filter(AuditLog.transaction_id == tx.id)
        .order_by(AuditLog.sequence_number.asc())
        .all()
    )

    m = tx.measurement_record
    r = tx.rate_record
    v = tx.valuation_result
    dp = tx.digital_passport

    # Recompute ML status summary lazily for visibility
    real_count = (
        db.query(Transaction)
        .filter(Transaction.jeweller_id == tx.jeweller_id, Transaction.is_demo.is_(False))
        .count()
    )

    return {
        "id": tx.id,
        "transaction_code": tx.transaction_code,
        "status": tx.status,
        "version_number": tx.version_number,
        "parent_transaction_id": tx.parent_transaction_id,
        "parent_transaction_code": parent_code,
        "amended_by_transaction_code": child.transaction_code if child else None,
        "amendment_reason": tx.amendment_reason,
        "client_draft_id": tx.client_draft_id,
        "is_demo": bool(tx.is_demo),
        "notes": tx.notes,
        "created_at": tx.created_at,
        "updated_at": tx.updated_at,
        "jeweller": {
            "id": tx.jeweller.id,
            "shop_name": tx.jeweller.shop_name,
            "shop_code": tx.jeweller.shop_code,
            "city": tx.jeweller.city,
            "state": tx.jeweller.state,
            "bis_hallmark_license": tx.jeweller.bis_hallmark_license,
            "policy_max_deduction_pct": str(tx.jeweller.policy_max_deduction_pct),
            "policy_max_fixed_deduction_inr": str(tx.jeweller.policy_max_fixed_deduction_inr),
        },
        "customer": {
            "id": tx.customer_profile.id,
            "full_name": tx.customer_profile.full_name,
            "mobile_number": tx.customer_profile.mobile_number,
            "preferred_language": tx.customer_profile.preferred_language,
        },
        "jewellery_items": [
            {
                "id": item.id,
                "item_description": item.item_description,
                "category": item.category,
                "hallmark_huid": item.hallmark_huid,
                "stone_or_non_gold_description": item.stone_or_non_gold_description,
            }
            for item in tx.jewellery_items
        ],
        "measurement": {
            "gross_weight_g": str(m.gross_weight_g),
            "non_gold_weight_g": str(m.non_gold_weight_g),
            "net_gold_weight_g": str(m.net_gold_weight_g),
            "purity_pct": str(m.purity_pct),
            "purity_karat_label": m.purity_karat_label,
            "measurement_source": m.measurement_source,
            "instrument_name": m.instrument_name,
            "test_report_ref": m.test_report_ref,
            "measured_at": m.measured_at,
            "ocr_extracted": bool(m.ocr_extracted),
        }
        if m
        else None,
        "rate": {
            "rate_24k_per_g": str(r.rate_24k_per_g),
            "rate_source": r.rate_source,
            "rate_timestamp": r.rate_timestamp,
            "benchmark_reference_rate_per_g": str(r.benchmark_reference_rate_per_g)
            if r.benchmark_reference_rate_per_g is not None
            else None,
            "is_simulated_rate": bool(r.is_simulated_rate),
        }
        if r
        else None,
        "deductions": [
            {
                "id": d.id,
                "deduction_type": d.deduction_type,
                "label": d.label,
                "amount_inr": str(d.amount_inr),
                "percentage_of_gross": str(d.percentage_of_gross),
                "reason": d.reason or "",
                "supporting_doc_ref": d.supporting_doc_ref,
            }
            for d in tx.deductions
        ],
        "valuation": {
            "pure_gold_weight_g": str(v.pure_gold_weight_g),
            "gross_reference_value_inr": str(v.gross_reference_value_inr),
            "total_deductions_inr": str(v.total_deductions_inr),
            "calculated_net_value_inr": str(v.calculated_net_value_inr),
            "jeweller_offered_value_inr": str(v.jeweller_offered_value_inr),
            "offer_difference_inr": str(v.offer_difference_inr),
            "offer_difference_explanation": v.offer_difference_explanation,
            "assumptions": v.assumptions_json,
            "calculation_steps": v.calculation_steps_json,
            "computed_at": v.computed_at,
        }
        if v
        else None,
        "anomaly_flags": [
            {
                "id": f.id,
                "detection_method": f.detection_method,
                "code": f.code,
                "severity": f.severity,
                "title": f.title,
                "message": f.message,
                "evidence": f.evidence_json,
                "is_resolved": f.is_resolved,
            }
            for f in tx.anomaly_flags
        ],
        "ml_status": {
            "enabled": real_count >= 15,
            "sample_count": real_count,
            "min_samples_required": 15,
            "trained_on_demo_data": False,
        },
        "acknowledgements": [
            {
                "id": a.id,
                "party_role": a.party_role,
                "acknowledged_by_name": a.acknowledged_by_name,
                "acknowledged_at": a.acknowledged_at,
                "method": a.method,
                "note": a.note,
            }
            for a in tx.acknowledgements
        ],
        "digital_passport": {
            "id": dp.id,
            "transaction_code": dp.transaction_code,
            "version_number": dp.version_number,
            "payload_sha256": dp.payload_sha256,
            "previous_passport_hash": dp.previous_passport_hash,
            "signature_algorithm": dp.signature_algorithm,
            "signature_b64": dp.signature_b64,
            "public_key_fingerprint": dp.public_key_fingerprint,
            "verification_url": dp.verification_url,
            "qr_data_uri": generate_qr_data_uri(dp.verification_url),
            "signed_at": dp.signed_at,
            "is_revoked_by_amendment": bool(dp.is_revoked_by_amendment),
        }
        if dp
        else None,
        "audit_logs": [
            {
                "sequence_number": log.sequence_number,
                "action": log.action,
                "actor_role": log.actor_role,
                "details": log.details_json,
                "entry_hash": log.entry_hash,
                "created_at": log.created_at,
            }
            for log in tx_logs
        ],
    }
