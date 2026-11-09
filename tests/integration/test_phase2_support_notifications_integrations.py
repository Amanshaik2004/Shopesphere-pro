import pytest
from app.models.orders import Order
from app.common.enums import SupportCaseCategory, SupportCaseStatus, TicketPriority, NotificationChannel

def test_support_case_lifecycle_and_sla_metrics(client, customer_headers, superadmin_headers, db):
    # 1. Customer creates a chargeback dispute case
    create_res = client.post(
        "/api/v1/support-cases",
        json={
            "category": SupportCaseCategory.DISPUTE.value,
            "priority": TicketPriority.HIGH.value,
            "subject": "Unauthorized recurring transaction dispute",
            "description": "Card was billed twice for a single order.",
            "is_dispute": True,
            "chargeback_amount": 150.0
        },
        headers=customer_headers
    )
    assert create_res.status_code == 200
    case_data = create_res.json()["data"]
    case_id = case_data["id"]
    assert case_data["is_dispute"] is True
    assert case_data["chargeback_amount"] == 150.0

    # 2. Staff replies to the case (triggers first response timestamp)
    reply_res = client.post(
        f"/api/v1/support-cases/{case_id}/messages",
        json={"message": "We are investigating the duplicate billing records with the merchant acquiring bank."},
        headers=superadmin_headers
    )
    assert reply_res.status_code == 200

    # Verify first_response_at is now set
    c_check = client.get(f"/api/v1/support-cases/{case_id}", headers=superadmin_headers)
    assert c_check.json()["data"]["first_response_at"] is not None

    # 3. Escalate case
    esc_res = client.put(
        f"/api/v1/support-cases/{case_id}/escalate",
        json={"reason": "Requires review by financial operations manager"},
        headers=superadmin_headers
    )
    assert esc_res.status_code == 200
    assert esc_res.json()["data"]["status"] == "escalated"
    assert esc_res.json()["data"]["escalation_level"] == 1

    # 4. Resolve case
    resolve_res = client.put(
        f"/api/v1/support-cases/{case_id}/resolve",
        json={"resolution_notes": "Duplicate billing reversed through refund transaction.", "dispute_status": "WON"},
        headers=superadmin_headers
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["data"]["status"] == "resolved"
    assert resolve_res.json()["data"]["resolved_at"] is not None

    # 5. Check SLA metrics
    metrics_res = client.get("/api/v1/support-cases/metrics", headers=superadmin_headers)
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()["data"]
    assert metrics["total_cases"] >= 1
    assert metrics["disputes_count"] >= 1


def test_notification_preferences_and_deduplication(client, customer_headers, superadmin_headers, db):
    prof = client.get("/api/v1/profile", headers=customer_headers).json()["data"]
    cust_id = prof["user_id"]

    # 1. Update preferences: enable EMAIL for ORDER_STATUS, opt-out of SMS for ORDER_STATUS
    pref_res = client.put(
        "/api/v1/notifications/preferences",
        json={
            "preferences": [
                {"channel": "email", "event_type": "ORDER_STATUS", "is_enabled": True},
                {"channel": "sms", "event_type": "ORDER_STATUS", "is_enabled": False}
            ]
        },
        headers=customer_headers
    )
    assert pref_res.status_code == 200
    prefs = pref_res.json()["data"]
    assert len(prefs) == 2

    # 2. Dispatch SMS notification for ORDER_STATUS -> should be suppressed due to opt-out
    sms_disp = client.post(
        "/api/v1/notifications/dispatch",
        json={
            "user_id": cust_id,
            "title": "Your order has shipped",
            "message": "Tracking info enclosed",
            "channel": "sms",
            "notification_type": "ORDER_STATUS",
            "deduplication_key": "sms_ord_001"
        },
        headers=superadmin_headers
    )
    assert sms_disp.status_code == 200
    assert sms_disp.json()["data"]["delivery_status"] == "SKIPPED_OPT_OUT"

    # 3. Dispatch in-app notification with deduplication key
    notif1 = client.post(
        "/api/v1/notifications/dispatch",
        json={
            "user_id": cust_id,
            "title": "Refund processed",
            "message": "Your refund of $50 has been sent",
            "channel": "in_app",
            "notification_type": "REFUND",
            "deduplication_key": "dedup_refund_key_789"
        },
        headers=superadmin_headers
    )
    assert notif1.status_code == 200
    assert notif1.json()["data"]["is_duplicate"] is False
    assert notif1.json()["data"]["delivery_status"] == "DELIVERED"

    # 4. Re-dispatch same key -> duplicate prevented
    notif1_dup = client.post(
        "/api/v1/notifications/dispatch",
        json={
            "user_id": cust_id,
            "title": "Refund processed",
            "message": "Your refund of $50 has been sent",
            "channel": "in_app",
            "notification_type": "REFUND",
            "deduplication_key": "dedup_refund_key_789"
        },
        headers=superadmin_headers
    )
    assert notif1_dup.status_code == 200
    assert notif1_dup.json()["data"]["is_duplicate"] is True
    assert notif1_dup.json()["data"]["delivery_status"] == "SKIPPED_DUPLICATE"


def test_external_integrations_management(client, superadmin_headers, db):
    # 1. Configure Stripe integration
    cfg_res = client.post(
        "/api/v1/integrations/configs",
        json={
            "service_type": "payment",
            "provider_name": "STRIPE",
            "api_endpoint": "https://api.stripe.com/v1",
            "webhook_secret": "whsec_supersecretkey12345678",
            "timeout_seconds": 30,
            "retry_limit": 3
        },
        headers=superadmin_headers
    )
    assert cfg_res.status_code == 200
    data = cfg_res.json()["data"]
    # Secret must be masked!
    assert "whsec_supersecretkey12345678" not in data["webhook_secret_masked"]
    assert "whs...678" in data["webhook_secret_masked"]

    # 2. Check Integration Health
    health_res = client.get("/api/v1/integrations/health", headers=superadmin_headers)
    assert health_res.status_code == 200
    assert health_res.json()["data"]["system_status"] == "ALL_INTEGRATIONS_OPERATIONAL"

    # 3. Process integration callback
    cb_res = client.post(
        "/api/v1/integrations/callback",
        json={
            "provider_name": "STRIPE",
            "service_type": "payment",
            "event_type": "charge.captured",
            "signature": "sig_valid_test_signature",
            "payload": {"charge_id": "ch_12345", "amount": 9000, "currency": "usd"}
        }
    )
    assert cb_res.status_code == 200
    log_id = cb_res.json()["data"]["log_id"]

    # 4. View Integration Logs (credentials never exposed)
    logs_res = client.get("/api/v1/integrations/logs", headers=superadmin_headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()["data"]
    assert any(l["id"] == log_id for l in logs)


def test_advanced_reporting_and_csv_export(client, superadmin_headers, sample_catalog, db):
    prod = sample_catalog["product"]

    # 1. Advanced Sales Report
    sales_res = client.get("/api/v1/reports/sales-advanced", headers=superadmin_headers)
    assert sales_res.status_code == 200

    # 2. Financial Summary
    fin_res = client.get("/api/v1/reports/financial-summary", headers=superadmin_headers)
    assert fin_res.status_code == 200

    # 3. Inventory Aging
    aging_res = client.get("/api/v1/reports/inventory-aging", headers=superadmin_headers)
    assert aging_res.status_code == 200

    # 4. Customer Retention
    ret_res = client.get("/api/v1/reports/customer-retention", headers=superadmin_headers)
    assert ret_res.status_code == 200

    # 5. CSV Export
    csv_res = client.get("/api/v1/reports/export-csv?report_type=sales", headers=superadmin_headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert "Order Number,Date,Status" in csv_res.text
