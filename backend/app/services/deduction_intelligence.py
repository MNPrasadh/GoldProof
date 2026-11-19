"""AI Deduction Intelligence: deterministic rules + scikit-learn Isolation Forest anomaly detection."""

from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from typing import Any, Optional

import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session, joinedload

from app.models.entities import JewellerProfile, Transaction
from app.services.valuation import DeductionInput, ValuationOutput

MIN_ML_SAMPLES = 15
MIN_REASON_LENGTH = 8


@dataclass
class FlagCandidate:
    detection_method: str  # rule_based | ml_isolation_forest
    code: str
    severity: str  # info | attention | review_required
    title: str
    message: str
    evidence: dict[str, Any]


@dataclass
class IntelligenceEvaluation:
    flags: list[FlagCandidate]
    ml_status: dict[str, Any]
    requires_review: bool


def evaluate_isolation_forest(
    feature_vectors: list[list[float]],
    target_vector: list[float],
    min_samples: int = MIN_ML_SAMPLES,
) -> tuple[bool, Optional[float]]:
    """Run scikit-learn IsolationForest on representative historical feature vectors.

    Returns (is_outlier, decision_score). Never fits on fewer than `min_samples` observations.
    """
    if len(feature_vectors) < min_samples:
        return False, None

    x_train = np.array(feature_vectors, dtype=float)
    x_target = np.array([target_vector], dtype=float)

    model = IsolationForest(
        n_estimators=100,
        contamination=0.1,
        random_state=42,
    )
    model.fit(x_train)
    prediction = int(model.predict(x_target)[0])
    score = float(model.decision_function(x_target)[0])
    return prediction == -1, round(score, 4)


def _extract_feature_vector(
    valuation: ValuationOutput,
    deduction_count: int,
    gross_weight_g: Decimal,
    net_weight_g: Decimal,
) -> list[float]:
    gross_val = float(valuation.gross_reference_value_inr) or 1.0
    ded_pct = float(valuation.total_deductions_inr) / gross_val * 100.0
    offer_diff_pct = abs(float(valuation.offer_difference_inr)) / gross_val * 100.0
    net_ratio = float(net_weight_g) / (float(gross_weight_g) or 1.0)
    return [ded_pct, float(deduction_count), offer_diff_pct, net_ratio]


def evaluate_transaction_intelligence(
    db: Session,
    jeweller: JewellerProfile,
    valuation: ValuationOutput,
    deductions: list[DeductionInput],
    measurement_source: str,
    instrument_name: Optional[str],
    test_report_ref: Optional[str],
    benchmark_reference_rate_per_g: Optional[Decimal] = None,
    offer_difference_explanation: Optional[str] = None,
    exclude_transaction_id: Optional[str] = None,
    is_demo: bool = False,
) -> IntelligenceEvaluation:
    """Inspect valuation evidence with neutral deterministic rules and optional ML anomaly checks."""
    flags: list[FlagCandidate] = []
    gross_val = valuation.gross_reference_value_inr
    total_ded = valuation.total_deductions_inr

    # Rule 1: Deductions missing clear explanation
    unexplained = [
        d
        for d in deductions
        if d.amount_inr > Decimal("0") and (not d.reason or len(d.reason.strip()) < MIN_REASON_LENGTH)
    ]
    if unexplained:
        labels = ", ".join(d.label for d in unexplained)
        flags.append(
            FlagCandidate(
                detection_method="rule_based",
                code="UNEXPLAINED_DEDUCTION",
                severity="review_required",
                title="Deduction requires supporting explanation",
                message=(
                    f"Review required: Deduction item(s) ({labels}) do not include an adequate written "
                    "explanation. Please document the specific reason before finalizing."
                ),
                evidence={
                    "unexplained_items": [
                        {"label": d.label, "amount_inr": str(d.amount_inr), "reason": d.reason or ""}
                        for d in unexplained
                    ]
                },
            )
        )

    # Rule 2: Total deduction percentage exceeding shop policy
    total_ded_pct = (
        (total_ded / gross_val) * Decimal("100") if gross_val > Decimal("0") else Decimal("0")
    )
    max_pct = Decimal(jeweller.policy_max_deduction_pct)
    if total_ded_pct > max_pct:
        flags.append(
            FlagCandidate(
                detection_method="rule_based",
                code="POLICY_DEDUCTION_PCT_EXCEEDED",
                severity="review_required",
                title="Deduction exceeds shop percentage policy",
                message=(
                    f"Review required: The recorded deduction ({total_ded_pct:.2f}% of gross value) "
                    f"exceeds the shop's configured policy limit ({max_pct:.2f}%). "
                    "Please provide supporting documentation."
                ),
                evidence={
                    "recorded_deduction_pct": f"{total_ded_pct:.2f}",
                    "shop_policy_max_pct": f"{max_pct:.2f}",
                    "total_deductions_inr": str(total_ded),
                },
            )
        )

    # Rule 3: Total fixed deduction amount exceeding shop policy
    max_fixed = Decimal(jeweller.policy_max_fixed_deduction_inr)
    if total_ded > max_fixed:
        flags.append(
            FlagCandidate(
                detection_method="rule_based",
                code="POLICY_DEDUCTION_AMOUNT_EXCEEDED",
                severity="review_required",
                title="Deduction exceeds shop fixed limit",
                message=(
                    f"Review required: Total deductions (₹{total_ded:,.2f}) exceed the shop's "
                    f"standard limit (₹{max_fixed:,.2f}). Please attach supporting documentation."
                ),
                evidence={
                    "total_deductions_inr": str(total_ded),
                    "shop_policy_max_inr": str(max_fixed),
                },
            )
        )

    # Rule 4: Measurement evidence provenance & completeness
    if measurement_source == "instrument":
        if not (instrument_name and instrument_name.strip()) or not (test_report_ref and test_report_ref.strip()):
            flags.append(
                FlagCandidate(
                    detection_method="rule_based",
                    code="MISSING_INSTRUMENT_EVIDENCE",
                    severity="review_required",
                    title="Missing instrument or test report reference",
                    message=(
                        "Review required: Measurement is marked as instrument-provided, but the instrument "
                        "identifier or test report reference is incomplete."
                    ),
                    evidence={
                        "measurement_source": measurement_source,
                        "instrument_name": instrument_name or "",
                        "test_report_ref": test_report_ref or "",
                    },
                )
            )
    elif measurement_source == "manual":
        flags.append(
            FlagCandidate(
                detection_method="rule_based",
                code="MISSING_INSTRUMENT_EVIDENCE",
                severity="attention",
                title="Manual measurement without instrument report",
                message=(
                    "Attention: Weight or purity readings were entered manually without an attached assay "
                    "instrument report. Confirm physical verification with the customer."
                ),
                evidence={
                    "measurement_source": measurement_source,
                    "test_report_ref": test_report_ref or "",
                },
            )
        )
    elif measurement_source == "simulated_demo":
        flags.append(
            FlagCandidate(
                detection_method="rule_based",
                code="SIMULATED_MEASUREMENT_NOTICE",
                severity="info",
                title="Simulated demo measurement",
                message=(
                    "Demo notice: Measurement values are labelled as simulated demo readings and must "
                    "not be represented as live physical instrument output."
                ),
                evidence={"measurement_source": measurement_source},
            )
        )

    # Rule 5: Rate inconsistency vs benchmark or shop median
    reference_rate = benchmark_reference_rate_per_g
    rate_basis_label = "provided benchmark rate"
    if reference_rate is None:
        recent_rates_q = (
            db.query(Transaction)
            .options(joinedload(Transaction.rate_record))
            .filter(Transaction.jeweller_id == jeweller.id)
        )
        if exclude_transaction_id:
            recent_rates_q = recent_rates_q.filter(Transaction.id != exclude_transaction_id)
        recent_txs = recent_rates_q.order_by(Transaction.created_at.desc()).limit(20).all()
        recent_rates = [
            float(t.rate_record.rate_24k_per_g)
            for t in recent_txs
            if t.rate_record is not None and t.rate_record.rate_24k_per_g > 0
        ]
        if len(recent_rates) >= 3:
            reference_rate = Decimal(str(round(median(recent_rates), 2)))
            rate_basis_label = "shop recent median rate"

    if reference_rate is not None and reference_rate > Decimal("0"):
        diff_pct = abs(valuation.rate_24k_per_g - reference_rate) / reference_rate * Decimal("100")
        if diff_pct > Decimal("3.00"):
            flags.append(
                FlagCandidate(
                    detection_method="rule_based",
                    code="RATE_INCONSISTENCY",
                    severity="review_required",
                    title="24K reference rate differs from benchmark",
                    message=(
                        f"Review required: Recorded 24K rate (₹{valuation.rate_24k_per_g}/g) differs by "
                        f"{diff_pct:.2f}% from the {rate_basis_label} (₹{reference_rate}/g). "
                        "Please confirm the rate timestamp and source."
                    ),
                    evidence={
                        "recorded_rate_24k": str(valuation.rate_24k_per_g),
                        "reference_rate_24k": str(reference_rate),
                        "deviation_pct": f"{diff_pct:.2f}",
                        "basis": rate_basis_label,
                    },
                )
            )

    # Rule 6: Mismatch between recorded measurements / calculated net vs offered value
    derived_net = valuation.gross_weight_g - valuation.non_gold_weight_g
    weight_mismatch = abs(derived_net - valuation.net_gold_weight_g)
    if weight_mismatch > Decimal("0.01"):
        flags.append(
            FlagCandidate(
                detection_method="rule_based",
                code="MEASUREMENT_VALUATION_MISMATCH",
                severity="review_required",
                title="Weight breakdown mismatch",
                message=(
                    f"Review required: Gross ({valuation.gross_weight_g} g) minus non-gold "
                    f"({valuation.non_gold_weight_g} g) equals {derived_net} g, which differs from "
                    f"recorded net gold weight ({valuation.net_gold_weight_g} g)."
                ),
                evidence={
                    "gross_weight_g": str(valuation.gross_weight_g),
                    "non_gold_weight_g": str(valuation.non_gold_weight_g),
                    "derived_net_g": str(derived_net),
                    "recorded_net_g": str(valuation.net_gold_weight_g),
                },
            )
        )

    if abs(valuation.offer_difference_inr) > Decimal("50.00") and not (
        offer_difference_explanation and len(offer_difference_explanation.strip()) >= MIN_REASON_LENGTH
    ):
        flags.append(
            FlagCandidate(
                detection_method="rule_based",
                code="MEASUREMENT_VALUATION_MISMATCH",
                severity="review_required",
                title="Offered value differs from calculated valuation without explanation",
                message=(
                    f"Review required: Jeweller's offered value (₹{valuation.jeweller_offered_value_inr:,.2f}) "
                    f"differs from the calculated net value (₹{valuation.calculated_net_value_inr:,.2f}) "
                    f"by ₹{abs(valuation.offer_difference_inr):,.2f}. Please document why."
                ),
                evidence={
                    "calculated_net_value_inr": str(valuation.calculated_net_value_inr),
                    "jeweller_offered_value_inr": str(valuation.jeweller_offered_value_inr),
                    "offer_difference_inr": str(valuation.offer_difference_inr),
                },
            )
        )

    # Machine Learning Layer: Isolation Forest ONLY over representative NON-DEMO shop history
    hist_query = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.valuation_result),
            joinedload(Transaction.deductions),
            joinedload(Transaction.measurement_record),
        )
        .filter(
            Transaction.jeweller_id == jeweller.id,
            Transaction.is_demo.is_(False),
            Transaction.status != "cancelled",
        )
    )
    if exclude_transaction_id:
        hist_query = hist_query.filter(Transaction.id != exclude_transaction_id)
    historical_txs = hist_query.all()

    feature_vectors: list[list[float]] = []
    for h_tx in historical_txs:
        if h_tx.valuation_result is None or h_tx.measurement_record is None:
            continue
        h_gross = float(h_tx.valuation_result.gross_reference_value_inr) or 1.0
        h_ded_pct = float(h_tx.valuation_result.total_deductions_inr) / h_gross * 100.0
        h_offer_diff_pct = abs(float(h_tx.valuation_result.offer_difference_inr)) / h_gross * 100.0
        h_net_ratio = float(h_tx.measurement_record.net_gold_weight_g) / (
            float(h_tx.measurement_record.gross_weight_g) or 1.0
        )
        feature_vectors.append([h_ded_pct, float(len(h_tx.deductions)), h_offer_diff_pct, h_net_ratio])

    sample_count = len(feature_vectors)
    if sample_count < MIN_ML_SAMPLES:
        ml_status = {
            "enabled": False,
            "model_name": "IsolationForest (scikit-learn)",
            "sample_count": sample_count,
            "min_samples_required": MIN_ML_SAMPLES,
            "trained_on_demo_data": False,
            "reason": (
                f"Isolation Forest requires at least {MIN_ML_SAMPLES} non-demo historical transactions "
                f"for this shop ({sample_count} recorded so far). Deterministic rules remain active; "
                "GoldProof does not train anomaly models on fabricated demo records."
            ),
        }
    else:
        target_vec = _extract_feature_vector(
            valuation=valuation,
            deduction_count=len(deductions),
            gross_weight_g=valuation.gross_weight_g,
            net_weight_g=valuation.net_gold_weight_g,
        )
        is_outlier, score = evaluate_isolation_forest(feature_vectors, target_vec, MIN_ML_SAMPLES)
        ml_status = {
            "enabled": True,
            "model_name": "IsolationForest (scikit-learn)",
            "sample_count": sample_count,
            "min_samples_required": MIN_ML_SAMPLES,
            "trained_on_demo_data": False,
            "decision_score": score,
            "is_outlier": is_outlier,
            "reason": (
                f"Evaluated against {sample_count} representative non-demo shop transactions."
                + (" (Demo transaction evaluated read-only against real baseline.)" if is_demo else "")
            ),
        }
        if is_outlier:
            flags.append(
                FlagCandidate(
                    detection_method="ml_isolation_forest",
                    code="ML_ANOMALY_PATTERN_DETECTED",
                    severity="attention",
                    title="ML statistical pattern differs from shop baseline",
                    message=(
                        "ML Notice (Isolation Forest): Deduction percentage, offer variance, or net-weight "
                        f"ratio differs statistically from this shop's {sample_count} baseline transactions "
                        f"(score: {score}). Review supporting records for clarity."
                    ),
                    evidence={
                        "model": "IsolationForest",
                        "baseline_sample_count": sample_count,
                        "decision_score": score,
                        "target_features": {
                            "deduction_pct": round(target_vec[0], 2),
                            "deduction_count": int(target_vec[1]),
                            "offer_diff_pct": round(target_vec[2], 2),
                            "net_to_gross_ratio": round(target_vec[3], 4),
                        },
                    },
                )
            )

    requires_review = any(f.severity == "review_required" for f in flags)
    return IntelligenceEvaluation(flags=flags, ml_status=ml_status, requires_review=requires_review)
