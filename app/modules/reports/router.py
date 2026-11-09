import io
import csv
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.orders import Order, OrderItem
from app.models.inventory import InventoryItem, InventoryMovement, Warehouse
from app.models.catalog import Product, Category
from app.models.payments import Payment, Refund
from app.models.logistics import ReturnRequest
from app.models.sellers import SellerSettlement
from app.models.segmentation import CustomerSegment, CustomerSegmentMember
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, OrderStatus, PaymentStatus, SettlementStatus
from app.modules.reports.schemas import (
    SalesReportItem, InventoryValuationReport, ProductPerformanceReport,
    AdvancedSalesReportOut, FinancialSummaryReportOut, InventoryAgingReportOut,
    CustomerRetentionReportOut
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


# =========================================================================
# Phase 2: Advanced Reports & Metrics
# =========================================================================

@router.get("/sales-advanced", response_model=ResponseSchema[AdvancedSalesReportOut])
def get_advanced_sales_report(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    product_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    seller_id: Optional[int] = Query(None),
    order_status: Optional[OrderStatus] = Query(None),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if start_date:
        query = query.filter(Order.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Order.created_at <= datetime.fromisoformat(end_date) + timedelta(days=1))
    if order_status:
        query = query.filter(Order.status == order_status)
    else:
        query = query.filter(Order.status != OrderStatus.CANCELLED)

    orders = query.all()

    total_gross = 0.0
    total_disc = 0.0
    total_net = 0.0
    items_count = 0
    breakdown = []

    for ord in orders:
        # Filter items if product, category, or seller specified
        items = ord.items
        if product_id:
            items = [i for i in items if i.product_id == product_id]
        if category_id:
            cat_prod_ids = {p.id for p in db.query(Product.id).filter(Product.category_id == category_id).all()}
            items = [i for i in items if i.product_id in cat_prod_ids]
        if seller_id:
            seller_prod_ids = {p.id for p in db.query(Product.id).filter(Product.seller_id == seller_id).all()}
            items = [i for i in items if i.product_id in seller_prod_ids]

        if not items and (product_id or category_id or seller_id):
            continue

        ord_gross = sum(float(i.total_price) for i in items) if (product_id or category_id or seller_id) else float(ord.subtotal_amount)
        ord_disc = float(ord.discount_amount) if not (product_id or category_id or seller_id) else 0.0
        ord_net = max(0.0, ord_gross - ord_disc)
        ord_items_cnt = sum(i.quantity for i in items)

        total_gross += ord_gross
        total_disc += ord_disc
        total_net += ord_net
        items_count += ord_items_cnt

        breakdown.append({
            "order_id": ord.id,
            "order_number": ord.order_number,
            "date": ord.created_at.strftime("%Y-%m-%d"),
            "status": ord.status.value,
            "gross_amount": round(ord_gross, 2),
            "discount_amount": round(ord_disc, 2),
            "net_amount": round(ord_net, 2),
            "items_count": ord_items_cnt
        })

    return ResponseSchema(
        data=AdvancedSalesReportOut(
            total_orders=len(breakdown),
            gross_revenue=round(total_gross, 2),
            discounts_total=round(total_disc, 2),
            net_revenue=round(total_net, 2),
            items_count=items_count,
            breakdown=breakdown
        )
    )

@router.get("/financial-summary", response_model=ResponseSchema[FinancialSummaryReportOut])
def get_financial_summary(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    payments = db.query(Payment).filter(Payment.status.in_([PaymentStatus.SUCCESSFUL, PaymentStatus.PARTIALLY_REFUNDED, PaymentStatus.REFUNDED])).all()
    total_pay = sum(float(p.amount) for p in payments)

    refunds = db.query(Refund).filter(Refund.status == PaymentStatus.SUCCESSFUL).all()
    total_ref = sum(float(r.amount) for r in refunds)

    returns_cnt = db.query(ReturnRequest).count()

    settlements = db.query(SellerSettlement).filter(SellerSettlement.status == SettlementStatus.SETTLED).all()
    total_settle = sum(float(s.net_amount) for s in settlements)

    profit = round(total_pay - total_ref - total_settle, 2)

    return ResponseSchema(
        data=FinancialSummaryReportOut(
            total_payments_received=round(total_pay, 2),
            total_refunds_issued=round(total_ref, 2),
            total_returns_count=returns_cnt,
            total_seller_settlements=round(total_settle, 2),
            net_platform_profit=profit
        )
    )

@router.get("/inventory-aging", response_model=ResponseSchema[InventoryAgingReportOut])
def get_inventory_aging(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    items = db.query(InventoryItem).all()
    total_units = sum(i.quantity for i in items)
    low_stock = sum(1 for i in items if i.available_quantity <= i.low_stock_threshold)

    aging_list = []
    now = datetime.now(timezone.utc)
    for it in items:
        prod = db.query(Product).filter(Product.id == it.product_id).first()
        wh = db.query(Warehouse).filter(Warehouse.id == it.warehouse_id).first()
        last_mvmt = db.query(InventoryMovement).filter(InventoryMovement.inventory_item_id == it.id).order_by(InventoryMovement.created_at.desc()).first()
        days_inactive = 0
        if last_mvmt:
            mvmt_time = last_mvmt.created_at.replace(tzinfo=timezone.utc) if last_mvmt.created_at.tzinfo is None else last_mvmt.created_at
            days_inactive = (now - mvmt_time).days

        aging_list.append({
            "inventory_item_id": it.id,
            "product_name": prod.name if prod else "Unknown",
            "sku": prod.sku if prod else "Unknown",
            "warehouse": wh.name if wh else "Unknown",
            "quantity": it.quantity,
            "available_quantity": it.available_quantity,
            "days_since_last_movement": days_inactive,
            "is_slow_moving": (days_inactive > 30 and it.quantity > 0)
        })

    slow_moving = sum(1 for a in aging_list if a["is_slow_moving"])

    return ResponseSchema(
        data=InventoryAgingReportOut(
            total_inventory_units=total_units,
            low_stock_items_count=low_stock,
            slow_moving_items_count=slow_moving,
            aging_items=aging_list
        )
    )

@router.get("/customer-retention", response_model=ResponseSchema[CustomerRetentionReportOut])
def get_customer_retention_metrics(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    customers = db.query(User).filter(User.role == UserRole.CUSTOMER).all()
    total_cust = len(customers)

    repeat_count = 0
    all_order_totals = []
    for c in customers:
        cnt = db.query(Order).filter(Order.user_id == c.id, Order.status != OrderStatus.CANCELLED).count()
        if cnt > 1:
            repeat_count += 1
        orders = db.query(Order.total_amount).filter(Order.user_id == c.id, Order.status != OrderStatus.CANCELLED).all()
        for o in orders:
            all_order_totals.append(float(o[0]))

    rate = round((repeat_count / total_cust * 100), 2) if total_cust > 0 else 0.0
    aov = round(sum(all_order_totals) / len(all_order_totals), 2) if all_order_totals else 0.0

    # Segments breakdown
    segments = db.query(CustomerSegment).all()
    seg_breakdown = []
    for s in segments:
        m_cnt = db.query(CustomerSegmentMember).filter(CustomerSegmentMember.segment_id == s.id).count()
        seg_breakdown.append({
            "segment_id": s.id,
            "name": s.name,
            "code": s.code,
            "member_count": m_cnt
        })

    return ResponseSchema(
        data=CustomerRetentionReportOut(
            total_customers=total_cust,
            repeat_customers_count=repeat_count,
            repeat_purchase_rate=rate,
            average_order_value=aov,
            segment_breakdown=seg_breakdown
        )
    )

@router.get("/export-csv")
def export_report_csv(
    report_type: str = Query("sales", description="sales, inventory, financial, customers"),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "sales":
        orders = db.query(Order).order_by(Order.created_at.desc()).limit(1000).all()
        writer.writerow(["Order Number", "Date", "Status", "Subtotal", "Discount", "Tax", "Shipping", "Total Amount"])
        for o in orders:
            writer.writerow([o.order_number, o.created_at.strftime("%Y-%m-%d"), o.status.value, float(o.subtotal_amount), float(o.discount_amount), float(o.tax_amount), float(o.shipping_amount), float(o.total_amount)])

    elif report_type == "inventory":
        items = db.query(InventoryItem).all()
        writer.writerow(["Item ID", "Product ID", "Warehouse ID", "Quantity", "Reserved", "Available", "Low Stock Threshold"])
        for i in items:
            writer.writerow([i.id, i.product_id, i.warehouse_id, i.quantity, i.reserved_quantity, i.available_quantity, i.low_stock_threshold])

    elif report_type == "financial":
        payments = db.query(Payment).all()
        writer.writerow(["Payment ID", "Order ID", "Amount", "Currency", "Status", "Method", "Reconciled", "Created At"])
        for p in payments:
            writer.writerow([p.id, p.order_id, float(p.amount), p.currency, p.status.value, p.payment_method.value, p.reconciled, p.created_at.strftime("%Y-%m-%d %H:%M:%S")])

    elif report_type == "customers":
        custs = db.query(User).filter(User.role == UserRole.CUSTOMER).all()
        writer.writerow(["User ID", "Full Name", "Email", "Status", "Created At"])
        for c in custs:
            writer.writerow([c.id, c.full_name, c.email, c.status.value, c.created_at.strftime("%Y-%m-%d")])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{report_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"}
    )
