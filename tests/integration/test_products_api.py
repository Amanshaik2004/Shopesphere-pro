def test_get_products_list(client, sample_catalog):
    resp = client.get("/api/v1/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) >= 1

def test_get_product_detail_and_view_count(client, sample_catalog):
    prod_id = sample_catalog["product"].id
    resp = client.get(f"/api/v1/products/{prod_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["id"] == prod_id
    assert data["data"]["views_count"] >= 1
