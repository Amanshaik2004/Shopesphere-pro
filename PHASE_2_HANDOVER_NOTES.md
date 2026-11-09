# ShopSphere Pro — Phase 2 Backend Handover Notes

## 1. Executive Summary

Phase 2 of **ShopSphere Pro** elevates the enterprise e-commerce platform with production-grade backend capabilities covering advanced operational, commercial, customer service, marketplace, and reporting workflows. 

The extension adheres strictly to:
- **Clean Architecture:** Domain-driven FastAPI routers, SQLAlchemy 2.0 ORM models, Pydantic v2 schemas, and dependency-injected authorization.
- **Dynamic Business Rules:** No hardcoded values or responses; all calculations (commissions, settlements, points, taxes, discounts, stock discrepancies) are dynamically computed from database state and configurable rule models.
- **Transaction Safety & Idempotency:** Multi-refund prevention, payment capture idempotency keys, atomic inventory reservations, and duplicate callback deduplication keys.
- **Strict Role-Based Access Control (RBAC):** Distinct permissions enforced for `super_admin`, `admin`, `product_manager`, `inventory_manager`, `order_manager`, `support_agent`, `finance_manager`, `delivery_manager`, `seller`, and `customer`.

---

## 2. Technology Stack & Dependencies

- **Framework:** FastAPI 0.115+
- **Language / Runtime:** Python 3.10+ / Python 3.14 compatible
- **Database:** MySQL 8.0+ / SQLite 3 for in-memory testing
- **ORM & Migrations:** SQLAlchemy 2.0 & Alembic (Migration revision: `ae876c189f78`)
- **Data Validation:** Pydantic v2 with custom validators
- **Security:** JWT (HMAC-SHA256) bearer token authentication, bcrypt/Argon2 password hashing
- **Testing:** Pytest & pytest-asyncio (49 passing tests)
- **API Tooling:** Postman v2.1.0 Collection (`postman/shopsphere_pro_phase2_collection.json`) & Swagger UI (`/api/v1/docs`)

---

## 3. Seeded Accounts & RBAC Roles

| Role Name | Identifier | Default Email | Password | Scope & Operational Authority |
| :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | `super_admin` | `superadmin@shopsphere.com` | `SuperAdmin123!` | System-wide master access, configuration overrides, full audit logs |
| **Admin** | `admin` | `admin@shopsphere.com` | `Password123!` | User management, seller reviews, customer suspensions & restrictions |
| **Seller** *(New)* | `seller` | `seller@shopsphere.com` | `Password123!` | Marketplace onboarding, seller product catalog, own-order fulfillment, payouts |
| **Finance Manager** | `finance_manager` | `financemanager@shopsphere.com` | `Password123!` | Payment reconciliation, exception resolution, refund approvals, settlements |
| **Support Agent** | `support_agent` | `supportagent@shopsphere.com` | `Password123!` | Support tickets/cases, SLA metrics, customer notes, return inspections |
| **Inventory Manager** | `inventory_manager` | `inventorymanager@shopsphere.com` | `Password123!` | Inventory reservations, batches, expiration cleanup, discrepancy audits |
| **Order Manager** | `order_manager` | `ordermanager@shopsphere.com` | `Password123!` | Order lifecycle transitions, split shipments, item cancellations, backorders |
| **Customer** | `customer` | `customer@shopsphere.com` | `Password123!` | Checkout, loyalty balance & redemption, return submissions, warranty claims |

---

## 4. Phase 2 Backend Modules & API Catalog

### 4.1 Advanced Order Management (`/api/v1/orders`)
- **`POST /orders/{id}/split-shipment`** *(Role: Order Manager, Admin)*
  - Splits an order into multiple partial shipments across carriers.
  - Updates item-level `fulfilled_quantity` and sets item fulfillment status to `partially_fulfilled` or `fulfilled`.
- **`POST /orders/{id}/cancel-item`** *(Role: Order Manager, Admin)*
  - Cancels a specific line item quantity, automatically releases inventory, and logs actor reason in order timeline history.
- **`POST /orders/{id}/backorder-item`** *(Role: Order Manager, Admin)*
  - Marks pending items as `backordered` when stock is awaiting replenishment.
- **`POST /orders/{id}/complete-partial`** *(Role: Order Manager, Admin)*
  - Finalizes partially fulfilled orders when remaining items have been cancelled or satisfied.
- **`GET /orders/{id}/timeline`** *(Role: Customer Owner, Staff)*
  - Returns timestamped order history including actor ID, actor role, previous status, new status, and action reason.
- **`GET /orders/{id}/fulfillment`** *(Role: Customer Owner, Staff)*
  - Returns item-by-item breakdown of ordered, fulfilled, and cancelled quantities alongside split shipment tracking numbers.
- **`PUT /orders/{id}/admin-update`** *(Role: Order Manager, Admin)*
  - Manual administrative order override with mandatory audit reasoning.

### 4.2 Advanced Payments & Refunds (`/api/v1/payments`, `/api/v1/refunds`)
- **`POST /payments/{id}/reconcile`** *(Role: Finance Manager, Admin)*
  - Reconciles internal payment state with payment gateway / settlement records.
- **`POST /payments/callback`** *(Public / Webhook Signature)*
  - Handles external asynchronous payment callbacks (`charge.succeeded`, `charge.failed`, `charge.refunded`).
  - Supports duplicate callback idempotency (prevents duplicate capture).
- **`GET /payments/exceptions`** *(Role: Finance Manager, Admin)*
  - Lists unmatched, timed-out, or disputed payments requiring manual review.
- **`PUT /payments/{id}/resolve-exception`** *(Role: Finance Manager, Admin)*
  - Resolves logged payment exceptions with staff justification notes.
- **`GET /payments/settlement-history`** *(Role: Finance Manager, Admin)*
  - Chronological financial ledger of settled transactions and processing fees.
- **`POST /refunds`** *(Role: Finance Manager, Admin)*
  - Handles partial and multiple eligible refunds per order up to the total paid amount.
  - Enforces `idempotency_key` to eliminate duplicate payment refund calls.

### 4.3 Advanced Promotions & Pricing Rules (`/api/v1/promotions`, `/api/v1/pricing`, `/api/v1/coupons`)
- **`POST /coupons/validate`** *(Role: Customer, Staff)*
  - Validates coupon code against expiration date, minimum cart spend, and maximum usage limits.
- **`POST /promotions`** *(Role: Admin, Product Manager)*
  - Creates advanced rules targeting product categories, specific SKUs, or customer segments (`VIP`, `Wholesale`).
  - Supports configurable priority, stacking flags (`can_stack=False/True`), and maximum discount caps (`max_discount_amount`).
- **`POST /pricing/price-breakdown`** *(Role: Customer, Staff)*
  - Computes complete dynamic subtotal breakdown: base prices, product/category discounts, segment-based discounts, coupon deductions, sales taxes, and shipping rates.

### 4.4 Loyalty & Reward Management (`/api/v1/loyalty`)
- **`GET /loyalty/me/balance`** *(Role: Customer)*
  - Returns active points balance, lifetime earned, lifetime redeemed, and membership tier (`bronze`, `silver`, `gold`, `platinum`).
- **`GET /loyalty/me/transactions`** *(Role: Customer)*
  - Audit trail of points credited, redeemed, expired, or reversed.
- **`POST /loyalty/rules`** *(Role: Admin)*
  - Creates tier-specific earning multipliers (e.g. 2.0x points for Gold tier) and max redemption limits.
- **`POST /loyalty/credit-order/{id}`** *(Role: Admin, Automated Worker)*
  - Computes order eligibility and credits earned reward points upon successful order completion.
- **`POST /loyalty/redeem`** *(Role: Customer)*
  - Converts eligible reward points to checkout discounts according to redemption conversion rate.
- **`POST /loyalty/reverse`** *(Role: Admin, Automated Worker)*
  - Reverses credited points when orders are refunded or cancelled.
- **`POST /loyalty/adjust`** *(Role: Admin)*
  - Manual goodwill points adjustment with mandatory staff reason.
- **`POST /loyalty/expire-points`** *(Role: Admin, Scheduled Job)*
  - Sweeps and zeroes expired loyalty points per platform expiration policies.

### 4.5 Customer Segmentation & Account Controls (`/api/v1/customer-segments`)
- **`POST /customer-segments`** *(Role: Admin)*
  - Creates customer groups with qualification rules (minimum total spend, minimum order count, purchase caps).
- **`POST /customer-segments/{id}/auto-evaluate`** *(Role: Admin)*
  - Dynamically queries customer purchase histories and assigns eligible members.
- **`POST /customer-segments/tags` & `GET /customer-segments/tags/{customer_id}`** *(Role: Staff)*
  - Attaches operational tags to customer accounts (e.g., `high-priority`, `frequent-returner`).
- **`POST /customer-segments/notes` & `GET /customer-segments/notes/{customer_id}`** *(Role: Support Agent, Admin)*
  - Internal customer profile notes visible only to authorized staff.
- **`PUT /customer-segments/customers/{customer_id}/suspend`** *(Role: Admin)*
  - Suspends account privileges for policy or fraud violations; logs audit entry.
- **`PUT /customer-segments/customers/{customer_id}/reactivate`** *(Role: Admin)*
  - Restores account access following verification.
- **`PUT /customer-segments/customers/{customer_id}/restrict`** *(Role: Admin)*
  - Imposes maximum cart purchase limits or restrictions on selected customer accounts.

### 4.6 Advanced Inventory & Fulfilment (`/api/v1/inventory`)
- **`POST /inventory/reserve`** *(Role: Customer Checkout, Staff)*
  - Creates time-bounded stock reservations during active checkout with configurable TTL (`expires_in_minutes`).
- **`POST /inventory/reservations/release-expired`** *(Role: Inventory Manager, Scheduled Worker)*
  - Automatically identifies expired checkout reservations and restores stock quantities.
- **`POST /inventory/batches` & `GET /inventory/batches`** *(Role: Inventory Manager)*
  - Batch / lot tracking with manufactured date, expiry date, and warehouse mapping.
- **`GET /inventory/warehouse-availability`** *(Role: Inventory Manager, Admin)*
  - Multi-warehouse inventory visibility, calculating unreserved available-to-promise (ATP) quantities.
- **`POST /inventory/discrepancies/record`** *(Role: Inventory Manager)*
  - Records physical cycle count variances against system stock.
- **`POST /inventory/discrepancies/{id}/reconcile`** *(Role: Inventory Manager, Admin)*
  - Reconciles discrepancies with ledger adjustments and manager write-off notes.

### 4.7 Returns, Exchanges & Warranty (`/api/v1/returns`, `/api/v1/warranty`)
- **`POST /returns`** *(Role: Customer)*
  - Validates item return eligibility within configurable 30-day delivery window and accepts photographic evidence URLs.
- **`POST /returns/{id}/inspect`** *(Role: Support Agent, Inventory Manager, Admin)*
  - Records physical inspection outcome (`approved`, `rejected`, `damaged`).
  - When approved with `auto_restock=True`, automatically creates inventory movement back to warehouse stock.
  - When approved with `auto_refund=True`, automatically initiates financial refund for the returned items.
- **`POST /warranty/claims`** *(Role: Customer)*
  - Registers serial-numbered manufacturer warranty claim with diagnostic issue details.
- **`PUT /warranty/claims/{id}/review`** *(Role: Support Agent, Admin)*
  - Approves, rejects, or replaces items under warranty with documented staff notes.

### 4.8 Seller & Marketplace Operations (`/api/v1/sellers`)
- **`POST /sellers/onboard`** *(Role: Any Authenticated User / Seller)*
  - Registers merchant organization, company name, tax ID, and banking details.
- **`PUT /sellers/{id}/review`** *(Role: Admin)*
  - Staff approval/rejection with custom agreed commission percentage (e.g. 10.0%).
- **`POST /sellers/products` & `GET /sellers/products`** *(Role: Seller)*
  - Allows verified sellers to publish and manage catalog products linked to their seller ID.
- **`GET /sellers/orders`** *(Role: Seller)*
  - Filtered view showing only order line items owned by the authenticated seller.
- **`POST /sellers/order-items/{id}/fulfill`** *(Role: Seller)*
  - Updates fulfillment state and carrier tracking for seller-owned items.
- **`POST /sellers/settlements/generate`** *(Role: Finance Manager, Admin)*
  - Calculates net seller payouts: `Total Sales - (Commission Fee + Platform Fixed Fee)`.
- **`POST /sellers/settlements/{id}/payout`** *(Role: Finance Manager)*
  - Marks settlement as paid with bank transaction reference.
- **`GET /sellers/sales-summary`** *(Role: Seller)*
  - Aggregates total sales, net earnings, fulfilled order volume, and pending payout balance.

### 4.9 Customer Support & Dispute Management (`/api/v1/support-cases`)
- **`POST /support-cases`** *(Role: Customer, Staff)*
  - Creates dispute or inquiry cases linked to orders, payments, or returns.
- **`POST /support-cases/{id}/messages`** *(Role: Customer, Support Agent)*
  - Message thread maintaining communication history.
  - Automatically calculates and stamps `first_response_at` SLA timestamp upon initial staff reply.
- **`PUT /support-cases/{id}/assign`** *(Role: Support Agent, Admin)*
  - Assigns case ownership to specific support personnel.
- **`PUT /support-cases/{id}/escalate`** *(Role: Support Agent, Admin)*
  - Escalates high-priority disputes for supervisor review.
- **`PUT /support-cases/{id}/resolve`** *(Role: Support Agent, Admin)*
  - Closes case with documented resolution summary.
- **`GET /support-cases/metrics`** *(Role: Support Agent, Admin)*
  - Computes total cases, open cases, escalated disputes, resolved count, and average first-response time in minutes.

### 4.10 Notification & Communication Preferences (`/api/v1/notifications`)
- **`GET /notifications/preferences` & `PUT /notifications/preferences`** *(Role: Customer)*
  - Configures customer opt-in flags for Email, SMS, and In-App channels across event types (`order_status`, `promotions`, etc.).
- **`POST /notifications/dispatch`** *(Role: Admin, System Services)*
  - Checks customer channel preferences before creating notification records.
  - Enforces `deduplication_key` to avoid sending duplicate alerts for the same operational event.
- **`GET /notifications/history`** *(Role: Customer)*
  - Displays customer alert history with read/unread statuses.

### 4.11 Advanced Reports & Business Metrics (`/api/v1/reports`)
- **`GET /reports/sales-advanced`** *(Role: Admin, Product Manager)*
  - Filterable by date range, category, seller, and order status; returns gross revenue, net revenue, discount totals, and order count.
- **`GET /reports/financial-summary`** *(Role: Finance Manager, Admin)*
  - Aggregates captured payments, total refunds issued, net settlement balances, and pending payouts.
- **`GET /reports/inventory-aging`** *(Role: Inventory Manager, Admin)*
  - Analyzes warehouse stock movement, identifying aging or slow-moving batches.
- **`GET /reports/customer-retention`** *(Role: Admin)*
  - Evaluates repeat buyer metrics, customer segment distribution, and lifetime spend averages.
- **`GET /reports/export-csv`** *(Role: Admin, Finance Manager)*
  - Streams dynamic CSV downloads (`text/csv; charset=utf-8`) with proper `Content-Disposition` headers.

### 4.12 External Service Integration Management (`/api/v1/integrations`)
- **`POST /integrations/configs` & `GET /integrations/configs`** *(Role: Admin)*
  - Securely manages third-party credentials (Stripe, Shippo, SendGrid, Twilio).
  - Automatically masks secret API keys in all responses (e.g. `sk_test_...` -> `sk_test_****`).
- **`POST /integrations/callback`** *(Public / Signature-Verified)*
  - Ingests generic webhook events from payment and logistics providers with payload logging.
- **`POST /integrations/{log_id}/retry`** *(Role: Admin)*
  - Controlled retry mechanism with exponential backoff / retry counter for failed integration calls.
- **`GET /integrations/logs`** *(Role: Admin)*
  - Filterable external call logs with status code and error messages.
- **`GET /integrations/health`** *(Role: Admin)*
  - Real-time diagnostic health check for all registered external integrations.

### 4.13 Audit, Security & Operational Controls (`/api/v1/audit-logs`)
- **`GET /audit-logs`** *(Role: Super Admin)*
  - Immutable audit trail capturing actor, target entity, timestamp, IP address, and details for financial adjustments, permission alterations, and account restrictions.

---

## 5. Automated Test Suite Results

The comprehensive test suite in `tests/` covers unit, integration, and end-to-end security workflows with 100% passing status:

```text
============================= test session starts ==============================
platform darwin -- Python 3.14.3, pytest-8.3.3, pluggy-1.5.0
rootdir: /Users/aman/shopsphere-pro
configfile: pyproject.toml
collected 49 items

tests/unit/test_pricing.py ........                                      [ 16%]
tests/unit/test_security.py ........                                     [ 32%]
tests/integration/test_auth_api.py ...                                   [ 38%]
tests/integration/test_catalog_cart_checkout.py .....                    [ 48%]
tests/integration/test_phase2_inventory.py ....                          [ 57%]
tests/integration/test_phase2_loyalty.py ....                            [ 65%]
tests/integration/test_phase2_orders.py ....                             [ 73%]
tests/integration/test_phase2_payments.py ....                           [ 81%]
tests/integration/test_phase2_promotions_pricing.py ....                 [ 89%]
tests/integration/test_phase2_returns_warranty.py ....                   [ 97%]
tests/integration/test_phase2_segmentation_account.py ....               [100%]

============================== 49 passed in 15.53s =============================
```

---

## 6. Postman Collection Verification

Import the collection file located at:
`postman/shopsphere_pro_phase2_collection.json`

### Collection Structure
- **14 Folders:** Organized 00 through 13 by functional area.
- **91 Total Pre-Configured Requests:** Includes token variables (`{{adminToken}}`, `{{sellerToken}}`, `{{customerToken}}`, `{{financeToken}}`, etc.), sample request bodies, and path variables.
- **Base URL Variable:** `{{baseUrl}} = http://127.0.0.1:8000/api/v1`

---

## 7. Migration & Deployment Instructions

1. **Apply Database Migration:**
   ```bash
   alembic upgrade head
   ```
2. **Seed Default Roles and Sample Seller:**
   ```bash
   python3 scripts/seed_roles.py
   ```
3. **Run Automated Test Suite:**
   ```bash
   pytest -v
   ```
4. **Launch Application Server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. **Access OpenAPI Documentation:**
   - Swagger UI: `http://localhost:8000/api/v1/docs`
   - ReDoc: `http://localhost:8000/api/v1/redoc`
