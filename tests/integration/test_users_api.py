def test_superadmin_login(client, superadmin_user):
    resp = client.post("/api/v1/auth/login", json={
        "email": "superadmin_test@shopsphere.com",
        "password": "SuperAdmin123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["role"] == "super_admin"

def test_get_users_list_as_superadmin(client, superadmin_headers):
    resp = client.get("/api/v1/users", headers=superadmin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) >= 1

def test_customer_cannot_list_users(client, customer_headers):
    resp = client.get("/api/v1/users", headers=customer_headers)
    assert resp.status_code == 403
