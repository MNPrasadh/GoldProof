"""Authentication, RBAC, and strict multi-tenant isolation tests."""

from tests.conftest import auth_headers


def test_demo_accounts_and_login_roles(test_env):
    client, _ = test_env
    demo_resp = client.get("/api/auth/demo-accounts")
    assert demo_resp.status_code == 200
    accounts = demo_resp.json()
    assert len(accounts) == 4

    for acc in accounts:
        login = client.post("/api/auth/login", json={"email": acc["email"], "password": acc["password"]})
        assert login.status_code == 200
        body = login.json()
        assert body["user"]["role"] == acc["role"]
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.status_code == 200
        assert me.json()["email"] == acc["email"]


def test_unauthenticated_blocked(test_env):
    client, _ = test_env
    assert client.get("/api/transactions").status_code == 401
    assert client.get("/api/analytics/jeweller").status_code == 401
    assert client.get("/api/analytics/admin").status_code == 401


def test_jeweller_tenant_isolation_and_customer_scoping(test_env):
    client, _ = test_env
    j1_headers = auth_headers(client, "meena@kaverigold.demo")
    j2_headers = auth_headers(client, "arun@maduraigold.demo")
    cust_headers = auth_headers(client, "lakshmi@customer.demo")

    j1_list = client.get("/api/transactions", headers=j1_headers).json()
    j2_list = client.get("/api/transactions", headers=j2_headers).json()
    cust_list = client.get("/api/transactions", headers=cust_headers).json()

    j1_codes = {t["transaction_code"] for t in j1_list}
    j2_codes = {t["transaction_code"] for t in j2_list}
    cust_codes = {t["transaction_code"] for t in cust_list}

    assert "GP-DEMO-2026-001" in j1_codes
    assert "GP-DEMO-2026-005" not in j1_codes
    assert j2_codes == {"GP-DEMO-2026-005"}
    assert cust_codes == {"GP-DEMO-2026-001", "GP-DEMO-2026-002", "GP-DEMO-2026-003"}

    # Cross-tenant detail access MUST be rejected with 403
    j2_tx_id = j2_list[0]["id"]
    j1_tx_id = next(t["id"] for t in j1_list if t["transaction_code"] == "GP-DEMO-2026-001")
    walkin_tx_id = next(t["id"] for t in j1_list if t["transaction_code"] == "GP-DEMO-2026-004")

    assert client.get(f"/api/transactions/{j2_tx_id}", headers=j1_headers).status_code == 403
    assert client.get(f"/api/transactions/{j1_tx_id}", headers=j2_headers).status_code == 403
    assert client.get(f"/api/transactions/{walkin_tx_id}", headers=cust_headers).status_code == 403
    assert client.get(f"/api/transactions/{j2_tx_id}", headers=cust_headers).status_code == 403

    # Non-admin cannot access admin analytics
    assert client.get("/api/analytics/admin", headers=j1_headers).status_code == 403
    assert client.get("/api/analytics/admin", headers=cust_headers).status_code == 403

    admin_headers = auth_headers(client, "admin@goldproof.demo")
    admin_resp = client.get("/api/analytics/admin", headers=admin_headers)
    assert admin_resp.status_code == 200
    assert admin_resp.json()["audit_chain_integrity"]["valid"] is True
