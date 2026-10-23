from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.orders import Order
from app.models.catalog import Product
from app.models.inventory import InventoryItem
from app.models.payments import Payment
from app.models.logistics import ReturnRequest
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, OrderStatus, PaymentStatus, ReturnStatus
from app.modules.dashboard.schemas import DashboardSummaryOut

router = APIRouter(prefix="/dashboard", tags=["Module 47: Dashboard & Summary APIs"])

@router.get("/summary", response_model=ResponseSchema[DashboardSummaryOut])
def get_dashboard_summary(
    current_user: User = Depends(require_roles(
        UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER, UserRole.INVENTORY_MANAGER, UserRole.FINANCE_MANAGER
    )),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    
    # Total revenue from successful payments
    total_rev = db.query(func.sum(Payment.amount)).filter(Payment.status == PaymentStatus.SUCCESSFUL).scalar() or 0.0

    # Orders by status
    orders_group = db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    orders_by_status = {s.value: 0 for s in OrderStatus}
    for st, count in orders_group:
        orders_by_status[st.value] = count

    # Payments by status
    payments_group = db.query(Payment.status, func.count(Payment.id)).group_by(Payment.status).all()
    payments_by_status = {s.value: 0 for s in PaymentStatus}
    for st, count in payments_group:
        payments_by_status[st.value] = count

    # Low stock items
    low_stock = db.query(func.count(InventoryItem.id)).filter(
        (InventoryItem.quantity - InventoryItem.reserved_quantity) <= InventoryItem.low_stock_threshold
    ).scalar() or 0

    # Pending returns
    pending_returns = db.query(func.count(ReturnRequest.id)).filter(
        ReturnRequest.status == ReturnStatus.REQUESTED
    ).scalar() or 0

    return ResponseSchema(data=DashboardSummaryOut(
        total_users=total_users,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=float(total_rev),
        orders_by_status=orders_by_status,
        payments_by_status=payments_by_status,
        low_stock_items_count=low_stock,
        pending_returns_count=pending_returns
    ))
