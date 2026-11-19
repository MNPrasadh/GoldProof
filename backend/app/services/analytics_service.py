"""Tenant-isolated jeweller analytics and system-level administrator analytics."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.entities import AuditLog, JewellerProfile, Transaction
from app.services.audit_service import verify_audit_chain
from app.services.deduction_intelligence import MIN_ML_SAMPLES


def get_jeweller_analytics(
    db: Session,
    jeweller: JewellerProfile,
    days: int = 30,
    status_filter: Optional[str] = None,
) -> dict[str, Any]:
    """Compute strictly tenant-isolated analytics for a single jeweller shop."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.measurement_record),
            joinedload(Transaction.rate_record),
            joinedload(Transaction.deductions),
            joinedload(Transaction.valuation_result),
            joinedload(Transaction.anomaly_flags),
            joinedload(Transaction.digital_passport),
        )
        .filter(Transaction.jeweller_id == jeweller.id, Transaction.created_at >= cutoff)
    )
    if status_filter and status_filter != "all":
        query = query.filter(Transaction.status == status_filter)

    txs = query.order_by(Transaction.created_at.asc()).all()

    total_transactions = len(txs)
    total_gold_weight_g = Decimal("0.0000")
    total_exchange_value_inr = Decimal("0.00")
    total_deductions_sum = Decimal("0.00")
    deduction_pcts: list[Decimal] = []

    missing_reason_count = 0
    policy_mismatch_count = 0
    rate_inconsistency_count = 0
    review_required_count = 0
    signed_count = 0
    complete_evidence_count = 0

    daily_map: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"date": "", "count": 0, "exchange_value_inr": 0.0, "deductions_inr": 0.0}
    )
    monthly_map: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"month": "", "count": 0, "exchange_value_inr": 0.0, "gold_weight_g": 0.0}
    )

    for tx in txs:
        day_key = tx.created_at.strftime("%Y-%m-%d")
        month_key = tx.created_at.strftime("%Y-%m")
        daily_map[day_key]["date"] = day_key
        daily_map[day_key]["count"] += 1
        monthly_map[month_key]["month"] = month_key
        monthly_map[month_key]["count"] += 1

        if tx.measurement_record:
            total_gold_weight_g += tx.measurement_record.net_gold_weight_g
            monthly_map[month_key]["gold_weight_g"] += float(tx.measurement_record.net_gold_weight_g)
            if (
                tx.measurement_record.measurement_source == "instrument"
                and tx.measurement_record.instrument_name
                and tx.measurement_record.test_report_ref
            ):
                complete_evidence_count += 1

        if tx.valuation_result:
            total_exchange_value_inr += tx.valuation_result.jeweller_offered_value_inr
            total_deductions_sum += tx.valuation_result.total_deductions_inr
            daily_map[day_key]["exchange_value_inr"] += float(tx.valuation_result.jeweller_offered_value_inr)
            daily_map[day_key]["deductions_inr"] += float(tx.valuation_result.total_deductions_inr)
            monthly_map[month_key]["exchange_value_inr"] += float(tx.valuation_result.jeweller_offered_value_inr)
            if tx.valuation_result.gross_reference_value_inr > Decimal("0"):
                pct = (
                    tx.valuation_result.total_deductions_inr
                    / tx.valuation_result.gross_reference_value_inr
                    * Decimal("100")
                )
                deduction_pcts.append(pct)

        if tx.status == "signed":
            signed_count += 1

        codes = {f.code for f in tx.anomaly_flags}
        severities = {f.severity for f in tx.anomaly_flags}
        if "UNEXPLAINED_DEDUCTION" in codes:
            missing_reason_count += 1
        if "POLICY_DEDUCTION_PCT_EXCEEDED" in codes or "POLICY_DEDUCTION_AMOUNT_EXCEEDED" in codes:
            policy_mismatch_count += 1
        if "RATE_INCONSISTENCY" in codes:
            rate_inconsistency_count += 1
        if tx.status == "pending_review" or "review_required" in severities:
            review_required_count += 1

    avg_deduction_inr = (
        (total_deductions_sum / Decimal(total_transactions)).quantize(Decimal("0.01"))
        if total_transactions > 0
        else Decimal("0.00")
    )
    avg_deduction_pct = (
        (sum(deduction_pcts) / Decimal(len(deduction_pcts))).quantize(Decimal("0.01"))
        if deduction_pcts
        else Decimal("0.00")
    )
    completeness_pct = (
        round((complete_evidence_count / total_transactions) * 100.0, 1)
        if total_transactions > 0
        else 0.0
    )

    real_sample_count = (
        db.query(Transaction)
        .filter(Transaction.jeweller_id == jeweller.id, Transaction.is_demo.is_(False))
        .count()
    )

    return {
        "jeweller_id": jeweller.id,
        "shop_name": jeweller.shop_name,
        "days_window": days,
        "summary": {
            "total_transactions": total_transactions,
            "total_gold_weight_g": str(total_gold_weight_g.quantize(Decimal("0.0001"))),
            "total_exchange_value_inr": str(total_exchange_value_inr.quantize(Decimal("0.01"))),
            "average_deduction_inr": str(avg_deduction_inr),
            "average_deduction_pct": str(avg_deduction_pct),
            "transactions_requiring_review": review_required_count,
            "signed_passports_count": signed_count,
            "missing_reason_frequency": missing_reason_count,
            "policy_mismatch_frequency": policy_mismatch_count,
            "rate_inconsistency_frequency": rate_inconsistency_count,
            "instrument_evidence_completeness_pct": completeness_pct,
        },
        "ml_readiness": {
            "enabled": real_sample_count >= MIN_ML_SAMPLES,
            "non_demo_sample_count": real_sample_count,
            "min_samples_required": MIN_ML_SAMPLES,
            "note": (
                "Isolation Forest active on non-demo shop history."
                if real_sample_count >= MIN_ML_SAMPLES
                else f"Needs {MIN_ML_SAMPLES - real_sample_count} more non-demo transactions before ML activation."
            ),
        },
        "daily_trends": [daily_map[k] for k in sorted(daily_map.keys())],
        "monthly_trends": [monthly_map[k] for k in sorted(monthly_map.keys())],
    }


def get_admin_analytics(db: Session) -> dict[str, Any]:
    """Compute system-level administrator aggregates and verify audit log chain."""
    all_shops = db.query(JewellerProfile).all()
    all_txs = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.valuation_result),
            joinedload(Transaction.measurement_record),
            joinedload(Transaction.anomaly_flags),
        )
        .all()
    )

    total_tx = len(all_txs)
    signed_tx = sum(1 for t in all_txs if t.status == "signed")
    review_tx = sum(
        1
        for t in all_txs
        if t.status == "pending_review" or any(f.severity == "review_required" for f in t.anomaly_flags)
    )
    total_val = sum(
        (t.valuation_result.jeweller_offered_value_inr for t in all_txs if t.valuation_result),
        Decimal("0.00"),
    )
    total_weight = sum(
        (t.measurement_record.net_gold_weight_g for t in all_txs if t.measurement_record),
        Decimal("0.0000"),
    )

    shop_summaries = []
    for shop in all_shops:
        shop_txs = [t for t in all_txs if t.jeweller_id == shop.id]
        shop_review = sum(
            1
            for t in shop_txs
            if t.status == "pending_review" or any(f.severity == "review_required" for f in t.anomaly_flags)
        )
        shop_signed = sum(1 for t in shop_txs if t.status == "signed")
        shop_value = sum(
            (t.valuation_result.jeweller_offered_value_inr for t in shop_txs if t.valuation_result),
            Decimal("0.00"),
        )
        shop_summaries.append(
            {
                "shop_name": shop.shop_name,
                "shop_code": shop.shop_code,
                "city": shop.city,
                "transaction_count": len(shop_txs),
                "signed_count": shop_signed,
                "review_required_count": shop_review,
                "total_exchange_value_inr": str(shop_value.quantize(Decimal("0.01"))),
            }
        )

    chain_valid, chain_count, broken_seq = verify_audit_chain(db)
    recent_logs = db.query(AuditLog).order_by(AuditLog.sequence_number.desc()).limit(40).all()

    return {
        "system_summary": {
            "total_jeweller_shops": len(all_shops),
            "total_transactions": total_tx,
            "signed_transactions": signed_tx,
            "transactions_requiring_review": review_tx,
            "total_gold_weight_g": str(total_weight.quantize(Decimal("0.0001"))),
            "total_exchange_value_inr": str(total_val.quantize(Decimal("0.01"))),
        },
        "audit_chain_integrity": {
            "valid": chain_valid,
            "total_entries": chain_count,
            "first_broken_sequence": broken_seq,
        },
        "shop_summaries": shop_summaries,
        "recent_audit_logs": [
            {
                "sequence_number": log.sequence_number,
                "action": log.action,
                "actor_role": log.actor_role,
                "transaction_id": log.transaction_id,
                "jeweller_id": log.jeweller_id,
                "details": log.details_json,
                "previous_log_hash": log.previous_log_hash,
                "entry_hash": log.entry_hash,
                "created_at": log.created_at,
            }
            for log in recent_logs
        ],
    }
