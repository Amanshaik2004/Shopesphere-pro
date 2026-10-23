def test_customer_forbidden_from_admin_audit_logs(client, customer_headers):
    resp = client.get("/api/v1/audit-logs", headers=customer_headers)
    assert resp.status_code == 403

def test_customer_forbidden_from_creating_category(client, customer_headers):
    resp = client.post("/api/v1/categories", json={
        "name": "Unauthorized Cat",
        "slug": "unauth-cat"
    }, headers=customer_headers)
    assert resp.status_code == 403

def test_superadmin_allowed_on_audit_logs(client, superadmin_headers):
    resp = client.get("/api/v1/audit-logs", headers=superadmin_headers)
    assert resp.status_code == 200
