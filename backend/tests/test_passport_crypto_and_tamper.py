"""Ed25519 digital passport signing, QR generation, tamper detection, and amendment tests."""

from decimal import Decimal

from app.models.entities import AuditLog, Deduction, Transaction
from app.services.audit_service import verify_audit_chain
from tests.conftest import auth_headers


def test_passport_verification_and_qr_png(test_env):
    client, _ = test_env
    verify = client.get("/api/passports/verify/GP-DEMO-2026-001")
    assert verify.status_code == 200
    body = verify.json()
    assert body["signature_valid"] is True
    assert body["hash_matches_stored_payload"] is True
    assert body["matches_current_db_record"] is True
    assert body["integrity_status"] == "verified"
    assert body["valuation"]["calculated_net_value_inr"] == "136232.00"
    assert body["customer_display"]["masked_mobile"].endswith("2334")

    qr = client.get("/api/passports/GP-DEMO-2026-001/qr.png")
    assert qr.status_code == 200
    assert qr.headers["content-type"] == "image/png"
    assert qr.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_signed_transaction_immutable_and_amendment_chain(test_env):
    client, _ = test_env
    j1_headers = auth_headers(client, "meena@kaverigold.demo")
    txs = client.get("/api/transactions", headers=j1_headers).json()
    signed_tx = next(t for t in txs if t["transaction_code"] == "GP-DEMO-2026-001")

    base_payload = {
        "customer_name": "Lakshmi Narayanan",
        "customer_mobile": "+919840122334",
        "customer_preferred_language": "ta",
        "consent_granted": True,
        "item_description": "22K Traditional Gold Haram Necklace [DEMO]",
        "category": "necklace",
        "gross_weight_g": "20.0",
        "non_gold_weight_g": "0.0",
        "purity_pct": "91.6",
        "purity_karat_label": "22K (916)",
        "measurement_source": "simulated_demo",
        "instrument_name": "Simulated XRF Benchtop Demo",
        "test_report_ref": "DEMO-XRF-001",
        "rate_24k_per_g": "7600.00",
        "rate_source": "Illustrative 24K Bullion Reference [DEMO]",
        "deductions": [
            {
                "deduction_type": "melting_refining",
                "label": "Melting & Refining Charge",
                "amount_inr": "2000.00",
                "reason": "Corrected melting charge after customer review.",
            }
        ],
        "is_demo": True,
    }

    # Direct edit MUST fail with 409 Conflict
    edit_resp = client.put(f"/api/transactions/{signed_tx['id']}", headers=j1_headers, json=base_payload)
    assert edit_resp.status_code == 409

    # Amendment creates linked V2 while preserving V1 passport
    amend_resp = client.post(
        f"/api/transactions/{signed_tx['id']}/amend",
        headers=j1_headers,
        json={
            "amendment_reason": "Updated melting fee after ultrasonic cleaning discount.",
            "updated_payload": base_payload,
        },
    )
    assert amend_resp.status_code == 201
    v2 = amend_resp.json()
    assert v2["version_number"] == 2
    assert v2["parent_transaction_code"] == "GP-DEMO-2026-001"
    assert v2["valuation"]["calculated_net_value_inr"] == "137232.00"

    # Original V1 still verifies cryptographically as superseded_by_amendment
    v1_verify = client.get("/api/passports/verify/GP-DEMO-2026-001").json()
    assert v1_verify["signature_valid"] is True
    assert v1_verify["integrity_status"] == "superseded_by_amendment"
    assert v1_verify["amended_by_transaction_code"] == v2["transaction_code"]


def test_tamper_detection_on_db_modification(test_env):
    client, SessionLocal = test_env
    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(Transaction.transaction_code == "GP-DEMO-2026-001").first()
        assert tx is not None
        ded = db.query(Deduction).filter(Deduction.transaction_id == tx.id).first()
        assert ded is not None
        # Simulate unauthorized direct SQL alteration of deduction amount
        ded.amount_inr = Decimal("9999.00")
        db.commit()
    finally:
        db.close()

    verify = client.get("/api/passports/verify/GP-DEMO-2026-001").json()
    assert verify["integrity_status"] == "tampered"
    assert verify["matches_current_db_record"] is False

    # Also test audit log chain tamper detection
    db = SessionLocal()
    try:
        valid_before, _, _ = verify_audit_chain(db)
        assert valid_before is True
        first_log = db.query(AuditLog).order_by(AuditLog.sequence_number.asc()).first()
        assert first_log is not None
        first_log.action = "TAMPERED_ACTION"
        db.commit()
        valid_after, _, broken_seq = verify_audit_chain(db)
        assert valid_after is False
        assert broken_seq == 1
    finally:
        db.close()
