# ShopSphere Pro - Enterprise E-Commerce Platform Backend

**ShopSphere Pro** is a secure, scalable, and high-performance backend supporting the complete shopping lifecycle from customer onboarding and catalog discovery to checkout, payment gateways, fulfillment, and return reconciliations.

---

## 🚀 Key Highlights & Architecture

- **Backend Framework:** FastAPI 0.115+
- **Database & ORM:** MySQL 8.0+ with SQLAlchemy 2.0 ORM & PyMySQL driver
- **Migrations:** Alembic
- **Validation & Serialization:** Pydantic v2
- **Authentication & Security:** JWT Access & Refresh tokens, Argon2 / Bcrypt password hashing, Role-Based Access Control (RBAC)
- **Payment Gateway:** Stripe Sandbox & Mock Gateway with Idempotency & Webhooks
- **File & Media Storage:** Local file storage with size & type validation
- **Documentation:** Interactive Swagger UI (`/api/v1/docs`) & ReDoc (`/api/v1/redoc`)
- **API Testing:** Pytest suite with 100% pass rate & Postman collection

---

## 👥 User Roles & Permissions (9 Roles)

| Role | Role Identifier | Scope & Capabilities |
| :--- | :--- | :--- |
| **Super Admin** | `super_admin` | Full system configuration, database seeding, audit access, and overrides. |
| **Admin** | `admin` | User management, platform configuration, catalog oversight, and analytics. |
| **Product Manager** | `product_manager` | Manage categories, brands, products, variants, media, and price rules. |
| **Inventory Manager**| `inventory_manager`| Warehouses, stock levels, adjustments, low-stock alerts, transfers, and POs. |
| **Order Manager** | `order_manager` | Order fulfillment, item statuses, state machine transitions, and cancellations. |
| **Support Agent** | `support_agent` | Customer support tickets, reviews moderation, Q&A responses. |
| **Customer** | `customer` | Browse catalog, shopping cart, checkout, payment, returns, reviews, profile. |
| **Delivery Manager** | `delivery_manager` | Shipments, carriers, dispatching, tracking updates, and delivery attempts. |
| **Finance Manager** | `finance_manager` | Payment transactions, refunds, COD reconciliations, and financial exports. |

---

## 📦 50 Functional Modules Breakdown

| # | Module Name | Primary Endpoints | Description |
|---|:---|:---|:---|
| 01 | **Authentication & Authorization** | `POST /api/v1/auth/*` | Login, token refresh, logout token revocation, password change. |
| 02 | **User Management** | `GET, POST, PUT, DELETE /api/v1/users` | Admin user CRUD, status toggle, audit logs. |
| 03 | **Customer Registration** | `POST /api/v1/customers/*` | Customer signup, validation, duplicate prevention, verification. |
| 04 | **Customer Profile** | `GET, PUT /api/v1/profile` | Self profile management, contact details, deactivation requests. |
| 05 | **Address Management** | `GET, POST, PUT, DELETE /api/v1/addresses` | Shipping/billing address CRUD, default address selection. |
| 06 | **Category Management** | `GET, POST, PUT, DELETE /api/v1/categories` | Hierarchical categories, subcategories, deletion guard. |
| 07 | **Brand Management** | `GET, POST, PUT /api/v1/brands` | Brand CRUD, association, status toggle. |
| 08 | **Product Management** | `GET, POST, PUT, DELETE /api/v1/products` | Product catalog, pricing, SKU, search, filtering, view counts. |
| 09 | **Product Variants** | `GET, POST, PUT, DELETE /api/v1/variants` | Size, color, SKU variations, price adjustments. |
| 10 | **Product Media** | `POST, GET, DELETE /api/v1/product-media` | Image and document uploads, validation, metadata. |
| 11 | **Product Attributes** | `POST, GET, DELETE /api/v1/attributes` | Custom product attributes, category specifications, filtering. |
| 12 | **Product Pricing** | `PUT, GET /api/v1/pricing/*` | Base and sale prices, validation, price change history. |
| 13 | **Inventory Management** | `POST, GET /api/v1/inventory/*` | Stock adjustment, reserved vs available quantities, movement logs. |
| 14 | **Warehouse Management** | `GET, POST, PUT /api/v1/warehouses` | Warehouse facilities, capacities, warehouse-level inventory. |
| 15 | **Inventory Transfers** | `POST, GET /api/v1/inventory-transfers` | Inter-warehouse stock transfers, dispatch, receipt reconciliation. |
| 16 | **Low-Stock Management** | `GET, POST, PUT /api/v1/stock-alerts` | Threshold settings, restock alerts, low-stock reports. |
| 17 | **Shopping Cart** | `GET, POST, PUT, DELETE /api/v1/cart/*` | Customer carts, item additions, updates, removals, clearing. |
| 18 | **Cart Price Calculation**| `POST /api/v1/cart/calculate` | Server-side validation of subtotals, coupons, taxes, shipping. |
| 19 | **Wishlist Management** | `GET, POST, DELETE /api/v1/wishlist` | Customer wishlist, duplicate prevention, stock availability. |
| 20 | **Coupon Management** | `GET, POST, PUT, DELETE /api/v1/coupons` | Percentage and fixed coupons, validity dates, minimum order rules. |
| 21 | **Promotion Management** | `GET, POST, PUT, DELETE /api/v1/promotions` | Category & product promotional discount campaigns. |
| 22 | **Tax Management** | `GET, POST, PUT, DELETE /api/v1/taxes` | Regional and country-level tax rules. |
| 23 | **Shipping Configuration** | `GET, POST, PUT, DELETE /api/v1/shipping-config` | Carriers, base shipping costs, free delivery thresholds. |
| 24 | **Checkout Management** | `POST /api/v1/checkout` | Cart validation, stock reservation, order placement. |
| 25 | **Order Management** | `GET /api/v1/orders` | Customer order history, admin order inspection, search filters. |
| 26 | **Order Item Management** | `GET, PUT /api/v1/order-items/*` | Item line snapshots, fulfillment status per item. |
| 27 | **Order Status Management**| `PUT, GET /api/v1/order-status/*` | Validated state machine transitions, audit history. |
| 28 | **Order Cancellation** | `POST, GET /api/v1/cancellations` | Cancellation checks, automatic stock release, refund trigger. |
| 29 | **Payment Management** | `POST /api/v1/payments/*` | Stripe sandbox intent confirmation, idempotency, webhook. |
| 30 | **Payment Transactions** | `GET /api/v1/transactions/*` | Gateway references, customer payment logs, audit entries. |
| 31 | **Refund Management** | `POST, GET /api/v1/refunds` | Full and partial refunds, refundable balance checks. |
| 32 | **Cash on Delivery (COD)**| `PUT, POST, GET /api/v1/cod/*` | Collection status, delivery reconciliation. |
| 33 | **Shipping Orders** | `POST, GET /api/v1/shipments` | Shipment creation, carrier integration, shipping labels. |
| 34 | **Shipment Tracking** | `POST, GET /api/v1/tracking/*` | Checkpoint tracking event logs, timeline retrieval. |
| 35 | **Delivery Management** | `POST /api/v1/deliveries/*` | Personnel assignment, delivery attempts, proof of delivery. |
| 36 | **Return Management** | `POST, PUT /api/v1/returns/*` | Customer return requests, staff approvals, restock on receipt. |
| 37 | **Exchange Management** | `POST, PUT /api/v1/exchanges/*` | Exchange requests, replacement stock checks, approval. |
| 38 | **Reviews and Ratings** | `POST, GET, PUT /api/v1/reviews/*` | Verified purchaser checks, rating summaries, moderation. |
| 39 | **Product Q&A** | `POST, GET /api/v1/qa/*` | Customer questions, official staff answers. |
| 40 | **Support Tickets** | `POST, GET, PUT /api/v1/support-tickets`| Customer complaints, priority, message threads. |
| 41 | **In-App Notifications** | `POST, GET, PUT /api/v1/notifications` | User alerts, read/unread states, staff broadcast. |
| 42 | **Email & SMS Messaging** | `POST, GET /api/v1/messaging/*` | Email/SMS dispatching, delivery logs, retry mechanism. |
| 43 | **Supplier Management** | `POST, GET, PUT /api/v1/suppliers` | Supplier and seller accounts, contacts, tax details. |
| 44 | **Purchase Orders (PO)** | `POST, GET /api/v1/purchase-orders` | Stock procurement, status tracking, stock intake against PO. |
| 45 | **Supplier Invoices** | `POST, GET, PUT /api/v1/supplier-invoices`| Invoice records, payment status tracking, duplicate protection. |
| 46 | **Audit Log Management** | `GET /api/v1/audit-logs` | Immutable audit trail for all sensitive admin operations. |
| 47 | **Dashboard & Summary** | `GET /api/v1/dashboard/summary` | Real-time counts, revenue, inventory and order analytics. |
| 48 | **Reports & Analytics** | `GET /api/v1/reports/*` | Sales by date, inventory valuation, top product performance. |
| 49 | **Report Exports & Tasks**| `GET, POST /api/v1/exports/*` | Dynamic CSV, Excel (`.xlsx`), and PDF downloads; background jobs. |
| 50 | **Health & Integration** | `GET /api/v1/health` | Uptime check, database connection status, module integrity. |

---

## 🛠️ Installation and Setup

### 1. Prerequisites
- Python 3.10+
- MySQL 8.0+

### 2. Clone and Navigate
```bash
cd shopsphere-pro
```

### 3. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure your MySQL database credentials in `.env` are accurate:
```env
DATABASE_URL="mysql+pymysql://root:password@localhost:3306/shopsphere_pro_db"
```

### 5. Apply Database Migrations & Seed Default Data
```bash
# 1. Run Alembic migrations
alembic upgrade head

# 2. Seed Super Admin
python3 scripts/create_admin.py

# 3. Seed All Staff Roles (Admin, Inventory, Product, Finance, Support, Delivery, Customer)
python3 scripts/seed_roles.py

# 4. Seed Sample Product Catalog, Warehouses & Settings
python3 scripts/seed_sample_data.py
```

### 6. Start the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Once started, access:
- **Interactive OpenAPI Documentation (Swagger UI):** `http://localhost:8000/api/v1/docs`
- **Alternative Documentation (ReDoc):** `http://localhost:8000/api/v1/redoc`
- **System Health Endpoint:** `http://localhost:8000/api/v1/health`

---

## 🧪 Running Automated Tests

Run the test suite using pytest:
```bash
pytest
```
Test results verify:
- **Unit Tests:** Password hashing, JWT token life-cycle, pricing & coupon discount logic, inventory math, order totals, and refund thresholds.
- **Integration Tests:** Authentication, User management, Products catalog, Cart & Checkout, Orders API, and Payments gateway.
- **Security Tests:** RBAC role restriction checks and Customer Data Isolation (ownership checks).
- **Workflow Tests:** Complete end-to-end shopping workflow and complete return/refund lifecycle.

---

## 📬 Postman Collection

Import `postman/shopsphere_pro_collection.json` into Postman to test requests across modules with preconfigured payloads and authentication tokens.

---

## 🔑 Default Seeded Accounts

| Role | Email | Password |
| :--- | :--- | :--- |
| **Super Admin** | `superadmin@shopsphere.com` | `SuperAdmin123!` |
| **Admin** | `admin@shopsphere.com` | `Password123!` |
| **Product Manager** | `productmanager@shopsphere.com` | `Password123!` |
| **Inventory Manager** | `inventorymanager@shopsphere.com` | `Password123!` |
| **Order Manager** | `ordermanager@shopsphere.com` | `Password123!` |
| **Support Agent** | `supportagent@shopsphere.com` | `Password123!` |
| **Delivery Manager** | `deliverymanager@shopsphere.com` | `Password123!` |
| **Finance Manager** | `financemanager@shopsphere.com` | `Password123!` |
| **Customer** | `customer@shopsphere.com` | `Password123!` |
