import pytest
from datetime import datetime, timezone, timedelta
from app.models.inventory import InventoryItem, InventoryReservation

def test_inventory_reservations_and_release(client, superadmin_headers, sample_catalog, db):
    prod = sample_catalog["product"]
    wh = sample_catalog["warehouse"]
    inv = sample_catalog["inventory"]
    init_avail = inv.available_quantity

    # 1. Reserve 5 units for 15 minutes
    res_resp = client.post(
        "/api/v1/inventory/reserve",
        json={
            "product_id": prod.id,
            "warehouse_id": wh.id,
            "quantity": 5,
            "duration_minutes": 15
        },
        headers=superadmin_headers
    )
    assert res_resp.status_code == 200
    res_data = res_resp.json()["data"]
    res_id = res_data["id"]
    assert res_data["quantity"] == 5

    db.refresh(inv)
    assert inv.available_quantity == init_avail - 5

    # 2. Simulate expiry
    db_res = db.query(InventoryReservation).filter(InventoryReservation.id == res_id).first()
    db_res.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.commit()

    # 3. Call release-expired
    rel_resp = client.post("/api/v1/inventory/reservations/release-expired", headers=superadmin_headers)
    assert rel_resp.status_code == 200
    assert rel_resp.json()["data"]["expired_count"] >= 1

    db.refresh(inv)
    assert inv.available_quantity == init_avail


def test_batch_tracking_and_discrepancies(client, superadmin_headers, sample_catalog, db):
    inv = sample_catalog["inventory"]
    now = datetime.now(timezone.utc)

    # 1. Record Batch Receipt
    batch_resp = client.post(
        "/api/v1/inventory/batches",
        json={
            "inventory_item_id": inv.id,
            "batch_number": "BATCH-2026-X1",
            "quantity": 25,
            "cost_per_unit": 450.0,
            "expiry_date": (now + timedelta(days=90)).isoformat()
        },
        headers=superadmin_headers
    )
    assert batch_resp.status_code == 200
    assert batch_resp.json()["data"]["batch_number"] == "BATCH-2026-X1"

    # 2. Check Warehouse Availability
    avail_resp = client.get(f"/api/v1/inventory/warehouse-availability?product_id={inv.product_id}", headers=superadmin_headers)
    assert avail_resp.status_code == 200
    records = avail_resp.json()["data"]
    assert len(records) >= 1
    assert records[0]["total_quantity"] >= 25

    # 3. Record physical discrepancy: system has X, physical is 50
    disc_resp = client.post(
        "/api/v1/inventory/discrepancies/record",
        json={
            "inventory_item_id": inv.id,
            "physical_quantity": 50,
            "reason": "Quarterly physical warehouse cycle count"
        },
        headers=superadmin_headers
    )
    assert disc_resp.status_code == 200
    disc_id = disc_resp.json()["data"]["id"]

    # 4. Reconcile discrepancy
    rec_resp = client.post(
        f"/api/v1/inventory/discrepancies/{disc_id}/reconcile",
        json={"notes": "Adjusted inventory count per audit verification"},
        headers=superadmin_headers
    )
    assert rec_resp.status_code == 200
    assert rec_resp.json()["data"]["is_reconciled"] is True

    db.refresh(inv)
    assert inv.quantity == 50
