"""Offline draft synchronization, idempotency, and signed-record conflict protection tests."""

from datetime import datetime, timedelta, timezone

from tests.conftest import auth_headers


def _make_draft_payload(amount_deduction: str = "1200.00"):
    return {
        "customer_name": "Kavitha Rajan",
        "customer_mobile": "+919840556677",
        "customer_preferred_language": "ta",
        "consent_granted": True,
        "item_description": "22K Offline Draft Chain",
        "category": "chain",
        "gross_weight_g": "12.0",
        "non_gold_weight_g": "0.0",
        "purity_pct": "91.6",
        "purity_karat_label": "22K (916)",
        "measurement_source": "manual",
        "rate_24k_per_g": "7600.00",
        "rate_source": "Shop Board Offline Cache",
        "deductions": [
            {
                "deduction_type": "melting_refining",
                "label": "Melting Fee",
                "amount_inr": amount_deduction,
                "reason": "Standard melting allowance recorded during offline entry.",
            }
        ],
        "is_demo": False,
    }


def test_offline_sync_lifecycle_and_signed_conflict_protection(test_env):
    client, _ = test_env
    j1_headers = auth_headers(client, "meena@kaverigold.demo")
    t1 = datetime.now(timezone.utc).replace(microsecond=0)
    draft_id = "draft-android-001"

    # 1. Create from offline queue
    r1 = client.post(
        "/api/sync/drafts",
        headers=j1_headers,
        json={"drafts": [{"client_draft_id": draft_id, "client_updated_at": t1.isoformat(), "payload": _make_draft_payload("1200.00")}]},
    )
    assert r1.status_code == 200
    res1 = r1.json()["results"][0]
    assert res1["status"] == "created"
    tx_id = res1["transaction_id"]

    # 2. Idempotent replay with same timestamp
    r2 = client.post(
        "/api/sync/drafts",
        headers=j1_headers,
        json={"drafts": [{"client_draft_id": draft_id, "client_updated_at": t1.isoformat(), "payload": _make_draft_payload("1200.00")}]},
    )
    assert r2.json()["results"][0]["status"] == "already_synced"

    # 3. Update pending draft with newer timestamp
    t2 = t1 + timedelta(minutes=5)
    r3 = client.post(
        "/api/sync/drafts",
        headers=j1_headers,
        json={"drafts": [{"client_draft_id": draft_id, "client_updated_at": t2.isoformat(), "payload": _make_draft_payload("1000.00")}]},
    )
    assert r3.json()["results"][0]["status"] == "updated"

    # 4. Jeweller acknowledges and issues Digital Gold Passport (making tx signed & immutable)
    ack = client.post(f"/api/transactions/{tx_id}/acknowledge", headers=j1_headers, json={"method": "in_app_confirmation"})
    assert ack.status_code == 200
    issue = client.post(f"/api/passports/{tx_id}/issue", headers=j1_headers)
    assert issue.status_code == 200

    # 5. Stale/delayed offline sync MUST NOT overwrite the signed transaction
    t3 = t2 + timedelta(minutes=5)
    r4 = client.post(
        "/api/sync/drafts",
        headers=j1_headers,
        json={"drafts": [{"client_draft_id": draft_id, "client_updated_at": t3.isoformat(), "payload": _make_draft_payload("500.00")}]},
    )
    assert r4.status_code == 200
    assert r4.json()["results"][0]["status"] == "conflict_signed_immutable"

    # Verify original signed value was untouched
    detail = client.get(f"/api/transactions/{tx_id}", headers=j1_headers).json()
    assert detail["valuation"]["total_deductions_inr"] == "1000.00"
