"""Valuation calculation accuracy, deterministic rules, and IsolationForest ML tests."""

from decimal import Decimal

from app.models.entities import JewellerProfile
from app.services.transaction_service import create_transaction_record
from app.schemas.transaction import DeductionPayload, TransactionCreateRequest
from tests.conftest import auth_headers


def test_section_15_valuation_calculation(test_env):
    client, _ = test_env
    j1_headers = auth_headers(client, "meena@kaverigold.demo")

    preview = client.post(
        "/api/transactions/preview-valuation",
        headers=j1_headers,
        json={
            "gross_weight_g": "20",
            "non_gold_weight_g": "0",
            "purity_pct": "91.6",
            "measurement_source": "simulated_demo",
            "rate_24k_per_g": "7600",
            "rate_source": "Demo Reference Rate",
            "deductions": [
                {
                    "deduction_type": "melting_refining",
                    "label": "Melting & Refining Charge",
                    "amount_inr": "3000",
                    "reason": "Standard crucible melting and assay charges per shop policy.",
                }
            ],
            "is_demo": True,
        },
    )
    assert preview.status_code == 200
    data = preview.json()
    assert data["net_gold_weight_g"] == "20.0000"
    assert data["pure_gold_weight_g"] == "18.3200"
    assert data["gross_reference_value_inr"] == "139232.00"
    assert data["total_deductions_inr"] == "3000.00"
    assert data["calculated_net_value_inr"] == "136232.00"
    assert data["requires_review"] is False
    assert data["ml_status"]["enabled"] is False
    assert data["ml_status"]["trained_on_demo_data"] is False


def test_deterministic_rules_and_neutral_language(test_env):
    client, _ = test_env
    j1_headers = auth_headers(client, "meena@kaverigold.demo")

    preview = client.post(
        "/api/transactions/preview-valuation",
        headers=j1_headers,
        json={
            "gross_weight_g": "15.5",
            "non_gold_weight_g": "0.5",
            "net_gold_weight_g": "15.0",
            "purity_pct": "91.6",
            "measurement_source": "manual",
            "rate_24k_per_g": "8200",
            "benchmark_reference_rate_per_g": "7600",
            "rate_source": "Manual Counter Quote",
            "deductions": [
                {
                    "deduction_type": "wastage",
                    "label": "Special Deduction",
                    "amount_inr": "7500",
                    "reason": "",
                }
            ],
            "jeweller_offered_value_inr": "100000",
            "offer_difference_explanation": "",
            "is_demo": False,
        },
    )
    assert preview.status_code == 200
    data = preview.json()
    codes = {f["code"] for f in data["flags"]}

    assert "UNEXPLAINED_DEDUCTION" in codes
    assert "POLICY_DEDUCTION_PCT_EXCEEDED" in codes
    assert "POLICY_DEDUCTION_AMOUNT_EXCEEDED" in codes
    assert "MISSING_INSTRUMENT_EVIDENCE" in codes
    assert "RATE_INCONSISTENCY" in codes
    assert "MEASUREMENT_VALUATION_MISMATCH" in codes
    assert data["requires_review"] is True

    # Ensure strictly neutral wording (never accuse of fraud)
    combined_text = " ".join(f["title"] + " " + f["message"] for f in data["flags"]).lower()
    for forbidden in ("fraud", "scam", "cheat", "criminal"):
        assert forbidden not in combined_text


def test_isolation_forest_activates_only_with_representative_non_demo_data(test_env):
    client, SessionLocal = test_env
    j1_headers = auth_headers(client, "meena@kaverigold.demo")

    # Populate 16 realistic non-demo transactions for Kaveri shop
    db = SessionLocal()
    try:
        jeweller = db.query(JewellerProfile).filter(JewellerProfile.shop_code == "GP-SHOP-KOVAI-01").first()
        assert jeweller is not None
        actor = jeweller.user

        for idx in range(16):
            gross_w = Decimal("9.50") + Decimal(str(idx)) * Decimal("1.15")
            non_gold_w = Decimal(str((idx % 4) * 0.25))
            net_w = gross_w - non_gold_w
            ded_amt = Decimal("900.00") + Decimal(idx * 95)
            deds = [
                DeductionPayload(
                    deduction_type="melting_refining",
                    label="Standard Refining",
                    amount_inr=ded_amt,
                    reason="Standard refining and assay charge per documented tariff.",
                )
            ]
            if idx % 2 == 0:
                deds.append(
                    DeductionPayload(
                        deduction_type="assay_testing",
                        label="XRF Assay",
                        amount_inr=Decimal("300.00") + Decimal(idx * 10),
                        reason="Standard XRF purity verification fee.",
                    )
                )
            payload = TransactionCreateRequest(
                customer_name=f"Baseline Customer {idx}",
                customer_mobile=f"+9198400001{idx:02d}",
                customer_preferred_language="en",
                consent_granted=True,
                item_description=f"22K Chain #{idx}",
                gross_weight_g=gross_w,
                non_gold_weight_g=non_gold_w,
                net_gold_weight_g=net_w,
                purity_pct=Decimal("91.60"),
                measurement_source="instrument",
                instrument_name="SpectroXRF",
                test_report_ref=f"XRF-BASE-{idx}",
                rate_24k_per_g=Decimal("7600.00"),
                rate_source="IBJA Reference",
                deductions=deds,
                is_demo=False,
            )
            create_transaction_record(db, jeweller, actor, payload)
    finally:
        db.close()

    # Now evaluate an extreme statistical outlier (25% deduction + huge offer gap)
    outlier_resp = client.post(
        "/api/transactions/preview-valuation",
        headers=j1_headers,
        json={
            "gross_weight_g": "20.0",
            "non_gold_weight_g": "5.0",
            "purity_pct": "91.6",
            "measurement_source": "instrument",
            "instrument_name": "SpectroXRF",
            "test_report_ref": "XRF-OUTLIER-1",
            "rate_24k_per_g": "7600",
            "rate_source": "IBJA Reference",
            "deductions": [
                {
                    "deduction_type": "melting_refining",
                    "label": "Heavy Refining",
                    "amount_inr": "12000",
                    "reason": "Heavy solder removal across intricate antique links.",
                },
                {
                    "deduction_type": "assay_testing",
                    "label": "Extra Assay",
                    "amount_inr": "6000",
                    "reason": "Additional fire assay verification across multiple segments.",
                },
                {
                    "deduction_type": "wastage",
                    "label": "Wastage",
                    "amount_inr": "4000",
                    "reason": "Additional documented melting wastage allowance.",
                },
            ],
            "jeweller_offered_value_inr": "60000",
            "offer_difference_explanation": "Custom manual negotiation documented.",
            "is_demo": False,
        },
    )
    assert outlier_resp.status_code == 200
    body = outlier_resp.json()
    assert body["ml_status"]["enabled"] is True
    assert body["ml_status"]["sample_count"] >= 15
    ml_flags = [f for f in body["flags"] if f["detection_method"] == "ml_isolation_forest"]
    assert len(ml_flags) == 1
    assert ml_flags[0]["code"] == "ML_ANOMALY_PATTERN_DETECTED"
