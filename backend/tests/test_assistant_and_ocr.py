"""Tamil/English AI Assistant grounding and OCR human-confirmation tests."""

from tests.conftest import auth_headers


def test_tamil_and_english_assistant_grounding(test_env):
    client, _ = test_env
    cust_headers = auth_headers(client, "lakshmi@customer.demo")
    txs = client.get("/api/transactions", headers=cust_headers).json()
    tx_001 = next(t for t in txs if t["transaction_code"] == "GP-DEMO-2026-001")
    tx_002 = next(t for t in txs if t["transaction_code"] == "GP-DEMO-2026-002")

    # Tamil valuation question
    ta_resp = client.post(
        "/api/assistant/ask",
        headers=cust_headers,
        json={
            "transaction_id": tx_001["id"],
            "question": "எனது தங்கத்தின் மதிப்பு எவ்வளவு?",
            "language": "ta",
        },
    )
    assert ta_resp.status_code == 200
    ta_body = ta_resp.json()
    assert ta_body["language"] == "ta"
    assert "18.3200" in ta_body["answer"]
    assert "1,39,232.00" in ta_body["answer"]
    assert "1,36,232.00" in ta_body["answer"]
    assert ta_body["is_external_llm"] is False

    # English deduction breakdown question
    en_resp = client.post(
        "/api/assistant/ask",
        headers=cust_headers,
        json={
            "transaction_id": tx_001["id"],
            "question": "Why was ₹3,000 deducted?",
            "language": "en",
        },
    )
    assert en_resp.status_code == 200
    en_body = en_resp.json()
    assert "Melting & Refining Charge" in en_body["answer"]
    assert "XRF Purity Assay Fee" in en_body["answer"]

    # Missing evidence check on GP-DEMO-2026-002
    miss_resp = client.post(
        "/api/assistant/ask",
        headers=cust_headers,
        json={
            "transaction_id": tx_002["id"],
            "question": "Why was ₹6,500 deducted and what is missing?",
            "language": "en",
        },
    )
    assert miss_resp.status_code == 200
    miss_body = miss_resp.json()
    assert "MISSING EXPLANATION" in miss_body["answer"]
    assert len(miss_body["missing_information"]) >= 2


def test_ocr_requires_human_confirmation_and_does_not_mutate_db(test_env):
    client, _ = test_env
    j1_headers = auth_headers(client, "meena@kaverigold.demo")
    before_count = len(client.get("/api/transactions", headers=j1_headers).json())

    ocr_resp = client.post(
        "/api/ocr/extract",
        headers=j1_headers,
        data={"document_type": "assay_report"},
        files={"file": ("sample_slip.txt", b"Gross Weight: 12.50 g\nPurity: 91.6%\n24K Rate: 7600", "text/plain")},
    )
    assert ocr_resp.status_code == 200
    body = ocr_resp.json()
    assert body["requires_human_confirmation"] is True
    assert body["is_simulated"] is True
    assert body["extracted_fields"]["gross_weight_g"] == "12.50"
    assert body["extracted_fields"]["purity_pct"] == "91.6"

    after_count = len(client.get("/api/transactions", headers=j1_headers).json())
    assert after_count == before_count
