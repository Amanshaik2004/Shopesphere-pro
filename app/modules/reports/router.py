from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.orders import Order, OrderItem
from app.models.inventory import InventoryItem
from app.models.catalog import Product
from app.models.payments import Payment, Refund
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, OrderStatus, PaymentStatus
from app.modules.reports.schemas import (
    SalesReportItem, InventoryValuationReport, ProductPerformanceReport
)

router = APIRouter(prefix="/reports", tags=["Module 48: Reports & Analytics APIs"])

@router.get("/sales", response_model=ResponseSchema[List[SalesReportItem]])
def get_sales_report(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    since_date = datetime.now(timezone.utc) - timedelta(days=days)
    orders = db.query(Order).filter(
        Order.created_at >= since_date,
        Order.status != OrderStatus.CANCELLED
    ).all()

    daily_data = {}
    for ord in orders:
        dt = ord.created_at.strftime("%Y-%m-%d")
        if dt not in daily_data:
            daily_data[dt] = {"orders": 0, "gross": 0.0, "discounts": 0.0, "net": 0.0}
        daily_data[dt]["orders"] += 1
        daily_data[dt]["gross"] += float(ord.subtotal_amount)
        daily_data[dt]["discounts"] += float(ord.discount_amount)
        daily_data[dt]["net"] += float(ord.total_amount)

    result = [
        SalesReportItem(
            date=d,
            orders_count=vals["orders"],
            gross_sales=round(vals["gross"], 2),
            discounts=round(vals["discounts"], 2),
            net_sales=round(vals["net"], 2)
        )
        for d, vals in sorted(daily_data.items())
    ]
    return ResponseSchema(data=result)

@router.get("/inventory-valuation", response_model=ResponseSchema[InventoryValuationReport])
def get_inventory_valuation(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    items = db.query(InventoryItem, Product.base_price).join(Product, InventoryItem.product_id == Product.id).all()
    total_qty = 0
    total_val = 0.0
    for inv, price in items:
        total_qty += inv.quantity
        total_val += (inv.quantity * float(price))

    return ResponseSchema(data=InventoryValuationReport(
        total_items=len(items),
        total_quantity=total_qty,
        total_inventory_value=round(total_val, 2)
    ))

@router.get("/product-performance", response_model=ResponseSchema[List[ProductPerformanceReport]])
def get_product_performance(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    perf = db.query(
        OrderItem.product_id,
        OrderItem.product_name,
        OrderItem.sku,
        func.sum(OrderItem.quantity).label("units"),
        func.sum(OrderItem.total_price).label("revenue")
    ).group_by(OrderItem.product_id, OrderItem.product_name, OrderItem.sku).order_by(func.sum(OrderItem.total_price).desc()).limit(limit).all()

    reports = [
        ProductPerformanceReport(
            product_id=p[0],
            product_name=p[1],
            sku=p[2],
            units_sold=int(p[3] or 0),
            revenue_generated=round(float(p[4] or 0.0), 2)
        )
        for p in perf
    ]
    return ResponseSchema(data=reports)
