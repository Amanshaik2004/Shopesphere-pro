import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.lifespan import lifespan
import app.db.models

# Import all module routers
from app.modules.authentication import router as auth_router
from app.modules.users import router as users_router
from app.modules.customers import router as customers_router
from app.modules.profiles import router as profiles_router
from app.modules.addresses import router as addresses_router
from app.modules.categories import router as categories_router
from app.modules.brands import router as brands_router
from app.modules.products import router as products_router
from app.modules.variants import router as variants_router
from app.modules.product_media import router as media_router
from app.modules.attributes import router as attributes_router
from app.modules.pricing import router as pricing_router
from app.modules.inventory import router as inventory_router
from app.modules.warehouses import router as warehouses_router
from app.modules.inventory_transfers import router as transfers_router
from app.modules.stock_alerts import router as stock_alerts_router
from app.modules.carts import router as carts_router
from app.modules.wishlists import router as wishlists_router
from app.modules.coupons import router as coupons_router
from app.modules.promotions import router as promotions_router
from app.modules.taxes import router as taxes_router
from app.modules.shipping_config import router as shipping_router
from app.modules.checkout import router as checkout_router
from app.modules.orders import router as orders_router
from app.modules.order_items import router as order_items_router
from app.modules.order_status import router as order_status_router
from app.modules.cancellations import router as cancellations_router
from app.modules.payments import router as payments_router
from app.modules.transactions import router as transactions_router
from app.modules.refunds import router as refunds_router
from app.modules.cod import router as cod_router
from app.modules.shipments import router as shipments_router
from app.modules.tracking import router as tracking_router
from app.modules.deliveries import router as deliveries_router
from app.modules.returns import router as returns_router
from app.modules.exchanges import router as exchanges_router
from app.modules.reviews import router as reviews_router
from app.modules.questions_answers import router as qa_router
from app.modules.support_tickets import router as support_tickets_router
from app.modules.notifications import router as notifications_router
from app.modules.messaging import router as messaging_router
from app.modules.suppliers import router as suppliers_router
from app.modules.purchase_orders import router as purchase_orders_router
from app.modules.supplier_invoices import router as supplier_invoices_router
from app.modules.audit_logs import router as audit_logs_router
from app.modules.dashboard import router as dashboard_router
from app.modules.reports import router as reports_router
from app.modules.exports import router as exports_router
from app.modules.health import router as health_router

# Phase 2 Advanced Modules
from app.modules.loyalty import router as loyalty_router
from app.modules.customer_segments import router as customer_segments_router
from app.modules.warranty import router as warranty_router
from app.modules.sellers import router as sellers_router
from app.modules.support_cases import router as support_cases_router
from app.modules.integrations import router as integrations_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="ShopSphere Pro - Complete Enterprise E-Commerce Platform Backend (Phase 1 + Phase 2 Advanced Modules). Built with FastAPI, MySQL, SQLAlchemy ORM, and JWT RBAC.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Exception Handlers
register_exception_handlers(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploaded files
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include all module routers under API_V1_STR
api_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_prefix)
app.include_router(users_router, prefix=api_prefix)
app.include_router(customers_router, prefix=api_prefix)
app.include_router(profiles_router, prefix=api_prefix)
app.include_router(addresses_router, prefix=api_prefix)
app.include_router(categories_router, prefix=api_prefix)
app.include_router(brands_router, prefix=api_prefix)
app.include_router(products_router, prefix=api_prefix)
app.include_router(variants_router, prefix=api_prefix)
app.include_router(media_router, prefix=api_prefix)
app.include_router(attributes_router, prefix=api_prefix)
app.include_router(pricing_router, prefix=api_prefix)
app.include_router(inventory_router, prefix=api_prefix)
app.include_router(warehouses_router, prefix=api_prefix)
app.include_router(transfers_router, prefix=api_prefix)
app.include_router(stock_alerts_router, prefix=api_prefix)
app.include_router(carts_router, prefix=api_prefix)
app.include_router(wishlists_router, prefix=api_prefix)
app.include_router(coupons_router, prefix=api_prefix)
app.include_router(promotions_router, prefix=api_prefix)
app.include_router(taxes_router, prefix=api_prefix)
app.include_router(shipping_router, prefix=api_prefix)
app.include_router(checkout_router, prefix=api_prefix)
app.include_router(orders_router, prefix=api_prefix)
app.include_router(order_items_router, prefix=api_prefix)
app.include_router(order_status_router, prefix=api_prefix)
app.include_router(cancellations_router, prefix=api_prefix)
app.include_router(payments_router, prefix=api_prefix)
app.include_router(transactions_router, prefix=api_prefix)
app.include_router(refunds_router, prefix=api_prefix)
app.include_router(cod_router, prefix=api_prefix)
app.include_router(shipments_router, prefix=api_prefix)
app.include_router(tracking_router, prefix=api_prefix)
app.include_router(deliveries_router, prefix=api_prefix)
app.include_router(returns_router, prefix=api_prefix)
app.include_router(exchanges_router, prefix=api_prefix)
app.include_router(reviews_router, prefix=api_prefix)
app.include_router(qa_router, prefix=api_prefix)
app.include_router(support_tickets_router, prefix=api_prefix)
app.include_router(notifications_router, prefix=api_prefix)
app.include_router(messaging_router, prefix=api_prefix)
app.include_router(suppliers_router, prefix=api_prefix)
app.include_router(purchase_orders_router, prefix=api_prefix)
app.include_router(supplier_invoices_router, prefix=api_prefix)
app.include_router(audit_logs_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(exports_router, prefix=api_prefix)
app.include_router(health_router, prefix=api_prefix)

# Phase 2 Routers
app.include_router(loyalty_router, prefix=api_prefix)
app.include_router(customer_segments_router, prefix=api_prefix)
app.include_router(warranty_router, prefix=api_prefix)
app.include_router(sellers_router, prefix=api_prefix)
app.include_router(support_cases_router, prefix=api_prefix)
app.include_router(integrations_router, prefix=api_prefix)

@app.api_route("/docs", methods=["GET", "HEAD"], include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url=f"{settings.API_V1_STR}/docs")

@app.api_route("/redoc", methods=["GET", "HEAD"], include_in_schema=False)
def redirect_to_redoc():
    return RedirectResponse(url=f"{settings.API_V1_STR}/redoc")

@app.get("/")
def root():
    return {
        "success": True,
        "message": "Welcome to ShopSphere Pro API",
        "documentation": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
