from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import Order
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.pagination import PaginationParams, PaginatedResponse, PaginatedData, paginate_query
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, OrderStatus
from app.core.exceptions import NotFoundError, ForbiddenError
from app.modules.orders.schemas import OrderOut

router = APIRouter(prefix="/orders", tags=["Module 25: Order Management"])

@router.get("", response_model=PaginatedResponse[OrderOut])
def get_orders(
    status: Optional[OrderStatus] = Query(None),
    order_number: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    # If not staff, isolate customer data strictly
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Order.user_id == current_user.id)
    
    if status:
        query = query.filter(Order.status == status)
    if order_number:
        query = query.filter(Order.order_number.ilike(f"%{order_number}%"))

    query = query.order_by(Order.created_at.desc())
    paginated = paginate_query(query, pagination)

    return PaginatedResponse(
        message="Orders retrieved successfully",
        data=PaginatedData(
            items=[OrderOut.model_validate(o) for o in paginated.items],
            total=paginated.total,
            page=paginated.page,
            page_size=paginated.page_size,
            total_pages=paginated.total_pages
        )
    )

@router.get("/{order_id}", response_model=ResponseSchema[OrderOut])
def get_order_by_id(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("You do not have permission to view this order")

    return ResponseSchema(data=OrderOut.model_validate(order))
