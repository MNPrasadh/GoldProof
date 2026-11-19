"""Transactions, live valuation preview, acknowledgements, and immutable amendments router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.security import (
    assert_transaction_access,
    get_current_jeweller_profile,
    get_current_user,
    require_roles,
)
from app.database import get_db
from app.models.entities import CustomerProfile, JewellerProfile, Transaction, User
from app.schemas.transaction import (
    AcknowledgeRequest,
    AmendTransactionRequest,
    TransactionCreateRequest,
    ValuationPreviewRequest,
    ValuationPreviewResponse,
)
from app.services.deduction_intelligence import evaluate_transaction_intelligence
from app.services.transaction_service import (
    create_transaction_record,
    load_transaction_full,
    record_acknowledgement,
    serialize_transaction_detail,
    serialize_transaction_summary,
    update_mutable_transaction,
)
from app.services.valuation import DeductionInput, calculate_valuation

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.post("/preview-valuation", response_model=ValuationPreviewResponse)
def preview_valuation(
    payload: ValuationPreviewRequest,
    current_user: User = Depends(require_roles("jeweller", "admin")),
    db: Session = Depends(get_db),
):
    """Run Valuation Engine + Deduction Intelligence without persisting to database."""
    jeweller = db.query(JewellerProfile).filter(JewellerProfile.user_id == current_user.id).first()
    if jeweller is None:
        # Admin preview fallback uses a default policy container
        jeweller = JewellerProfile(
            user_id=current_user.id,
            shop_name="GoldProof Reference Policy",
            shop_code="REF",
            valuation_conventions={"valuation_basis": "24K pure gold equivalent"},
        )

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

    val = calculate_valuation(
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
        valuation=val,
        deductions=deduction_inputs,
        measurement_source=payload.measurement_source,
        instrument_name=payload.instrument_name,
        test_report_ref=payload.test_report_ref,
        benchmark_reference_rate_per_g=payload.benchmark_reference_rate_per_g,
        offer_difference_explanation=payload.offer_difference_explanation,
        is_demo=payload.is_demo,
    )

    return ValuationPreviewResponse(
        gross_weight_g=str(val.gross_weight_g),
        non_gold_weight_g=str(val.non_gold_weight_g),
        net_gold_weight_g=str(val.net_gold_weight_g),
        purity_pct=str(val.purity_pct),
        pure_gold_weight_g=str(val.pure_gold_weight_g),
        rate_24k_per_g=str(val.rate_24k_per_g),
        gross_reference_value_inr=str(val.gross_reference_value_inr),
        total_deductions_inr=str(val.total_deductions_inr),
        calculated_net_value_inr=str(val.calculated_net_value_inr),
        jeweller_offered_value_inr=str(val.jeweller_offered_value_inr),
        offer_difference_inr=str(val.offer_difference_inr),
        assumptions=val.assumptions,
        calculation_steps=val.calculation_steps,
        flags=[
            {
                "detection_method": f.detection_method,
                "code": f.code,
                "severity": f.severity,
                "title": f.title,
                "message": f.message,
                "evidence": f.evidence,
            }
            for f in intel.flags
        ],
        ml_status=intel.ml_status,
        requires_review=intel.requires_review,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreateRequest,
    jeweller: JewellerProfile = Depends(get_current_jeweller_profile),
    current_user: User = Depends(require_roles("jeweller")),
    db: Session = Depends(get_db),
):
    """Create a new gold exchange transaction for the authenticated jeweller's shop."""
    if payload.client_draft_id:
        existing = db.query(Transaction).filter(Transaction.client_draft_id == payload.client_draft_id).first()
        if existing is not None:
            assert_transaction_access(db, current_user, existing)
            full = load_transaction_full(db, existing.id)
            return serialize_transaction_detail(db, full)  # type: ignore[arg-type]

    tx = create_transaction_record(
        db=db,
        jeweller=jeweller,
        actor_user=current_user,
        payload=payload,
    )
    return serialize_transaction_detail(db, tx)


@router.get("")
def list_transactions(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List transactions strictly scoped to the caller's role and tenant."""
    query = db.query(Transaction).options(
        joinedload(Transaction.jeweller),
        joinedload(Transaction.customer_profile),
        joinedload(Transaction.jewellery_items),
        joinedload(Transaction.measurement_record),
        joinedload(Transaction.valuation_result),
        joinedload(Transaction.anomaly_flags),
        joinedload(Transaction.acknowledgements),
        joinedload(Transaction.digital_passport),
    )

    if current_user.role == "jeweller":
        profile = db.query(JewellerProfile).filter(JewellerProfile.user_id == current_user.id).first()
        if profile is None:
            return []
        query = query.filter(Transaction.jeweller_id == profile.id)
    elif current_user.role == "customer":
        if current_user.phone:
            matching_profiles = select(CustomerProfile.id).where(
                CustomerProfile.mobile_number == current_user.phone
            )
            query = query.filter(
                or_(
                    Transaction.customer_user_id == current_user.id,
                    Transaction.customer_profile_id.in_(matching_profiles),
                )
            )
        else:
            query = query.filter(Transaction.customer_user_id == current_user.id)
    elif current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    if status_filter and status_filter != "all":
        query = query.filter(Transaction.status == status_filter)

    txs = query.order_by(Transaction.created_at.desc()).all()
    if search and search.strip():
        needle = search.strip().lower()
        txs = [
            t
            for t in txs
            if needle in t.transaction_code.lower()
            or (t.customer_profile and needle in t.customer_profile.full_name.lower())
            or any(needle in i.item_description.lower() for i in t.jewellery_items)
        ]

    return [serialize_transaction_summary(t) for t in txs]


@router.get("/{tx_id}")
def get_transaction(
    tx_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch complete transaction details, valuation steps, intelligence flags, and passport."""
    tx = load_transaction_full(db, tx_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    assert_transaction_access(db, current_user, tx)
    return serialize_transaction_detail(db, tx)


@router.put("/{tx_id}")
def update_transaction(
    tx_id: str,
    payload: TransactionCreateRequest,
    jeweller: JewellerProfile = Depends(get_current_jeweller_profile),
    current_user: User = Depends(require_roles("jeweller")),
    db: Session = Depends(get_db),
):
    """Modify an unsigned transaction. Signed transactions return 409 Conflict."""
    tx = load_transaction_full(db, tx_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    assert_transaction_access(db, current_user, tx)
    updated = update_mutable_transaction(db, tx, jeweller, current_user, payload)
    return serialize_transaction_detail(db, updated)


@router.post("/{tx_id}/acknowledge")
def acknowledge_transaction(
    tx_id: str,
    payload: AcknowledgeRequest,
    current_user: User = Depends(require_roles("jeweller", "customer")),
    db: Session = Depends(get_db),
):
    """Record explicit jeweller or customer acknowledgement prior to signing."""
    tx = load_transaction_full(db, tx_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    assert_transaction_access(db, current_user, tx)
    updated = record_acknowledgement(db, tx, current_user, payload.method, payload.note)
    return serialize_transaction_detail(db, updated)


@router.post("/{tx_id}/amend", status_code=status.HTTP_201_CREATED)
def amend_signed_transaction(
    tx_id: str,
    payload: AmendTransactionRequest,
    jeweller: JewellerProfile = Depends(get_current_jeweller_profile),
    current_user: User = Depends(require_roles("jeweller")),
    db: Session = Depends(get_db),
):
    """Create a new versioned amendment linked to an existing signed transaction without altering the original."""
    parent_tx = load_transaction_full(db, tx_id)
    if parent_tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    assert_transaction_access(db, current_user, parent_tx)

    if parent_tx.status != "signed" or parent_tx.digital_passport is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only signed transactions require versioned amendments; edit unsigned records directly.",
        )

    parent_tx.status = "amended"
    parent_tx.digital_passport.is_revoked_by_amendment = True
    db.flush()

    amended_tx = create_transaction_record(
        db=db,
        jeweller=jeweller,
        actor_user=current_user,
        payload=payload.updated_payload,
        parent_transaction=parent_tx,
        amendment_reason=payload.amendment_reason.strip(),
    )
    return serialize_transaction_detail(db, amended_tx)
