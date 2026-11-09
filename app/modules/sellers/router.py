import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.sellers import SellerProfile, CommissionRule, SellerSettlement
from app.models.catalog import Product, Category
from app.models.orders import Order, OrderItem
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, SellerStatus, SettlementStatus, AuditAction, OrderStatus
from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError, ConflictError
from app.core.audit import log_audit
from app.modules.sellers.schemas import (
    SellerOnboardRequest, SellerReviewRequest, SellerProfileOut,
    SellerProductCreate, SellerSettlementOut, SellerSalesSummaryOut
)
from app.modules.products.schemas import ProductOut
from app.modules.orders.schemas import OrderItemOut

router = APIRouter(prefix="/sellers", tags=["Module 3.8: Seller & Marketplace Operations"])

@router.post("/onboard", response_model=ResponseSchema[SellerProfileOut])
def onboard_seller(
    data: SellerOnboardRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    existing = db.query(SellerProfile).filter(SellerProfile.user_id == current_user.id).first()
    if existing:
        raise ConflictError("A seller profile already exists for this account")

    store_check = db.query(SellerProfile).filter(SellerProfile.store_name == data.store_name).first()
    if store_check:
        raise ConflictError("Store name already taken")

    profile = SellerProfile(
        user_id=current_user.id,
        store_name=data.store_name,
        business_name=data.business_name,
        business_registration=data.business_registration,
        bank_account_info=data.bank_account_info,
        status=SellerStatus.PENDING,
        commission_rate=10.0,
        platform_fee_percent=2.0
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    log_audit(db, AuditAction.CREATE, "SellerProfile", str(profile.id), current_user.id)
    return ResponseSchema(message="Seller application submitted for review", data=SellerProfileOut.model_validate(profile))

@router.get("/profile", response_model=ResponseSchema[SellerProfileOut])
def get_my_seller_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    profile = db.query(SellerProfile).filter(SellerProfile.user_id == current_user.id).first()
    if not profile:
        raise NotFoundError("Seller profile not found for this user")
    return ResponseSchema(data=SellerProfileOut.model_validate(profile))

@router.get("", response_model=ResponseSchema[List[SellerProfileOut]])
def list_sellers(
    status: Optional[SellerStatus] = Query(None),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    query = db.query(SellerProfile)
    if status:
        query = query.filter(SellerProfile.status == status)
    sellers = query.order_by(SellerProfile.created_at.desc()).all()
    return ResponseSchema(data=[SellerProfileOut.model_validate(s) for s in sellers])

@router.put("/{seller_id}/review", response_model=ResponseSchema[SellerProfileOut])
def review_seller(
    seller_id: int,
    data: SellerReviewRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    profile = db.query(SellerProfile).filter(SellerProfile.id == seller_id).first()
    if not profile:
        raise NotFoundError("Seller profile not found")

    profile.status = data.status
    if data.commission_rate is not None:
        profile.commission_rate = data.commission_rate
    if data.platform_fee_percent is not None:
        profile.platform_fee_percent = data.platform_fee_percent
    if data.rejection_reason:
        profile.rejection_reason = data.rejection_reason

    # If approved, update user's role to SELLER
    user = db.query(User).filter(User.id == profile.user_id).first()
    if user and data.status == SellerStatus.APPROVED:
        user.role = UserRole.SELLER

    profile.reviewed_by_id = current_user.id
    db.commit()
    db.refresh(profile)

    log_audit(db, AuditAction.STATUS_CHANGE, "SellerProfile", str(profile.id), current_user.id, new_values={"status": profile.status.value})
    return ResponseSchema(message=f"Seller profile updated to {profile.status.value}", data=SellerProfileOut.model_validate(profile))

@router.get("/products", response_model=ResponseSchema[List[ProductOut]])
def get_seller_products(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Sellers only see their own products
    products = db.query(Product).filter(Product.seller_id == current_user.id).all()
    return ResponseSchema(data=[ProductOut.model_validate(p) for p in products])

@router.post("/products", response_model=ResponseSchema[ProductOut])
def create_seller_product(
    data: SellerProductCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check approved seller
    profile = db.query(SellerProfile).filter(SellerProfile.user_id == current_user.id).first()
    if not profile or profile.status != SellerStatus.APPROVED:
        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            raise ForbiddenError("Only approved sellers can create marketplace products")

    if not db.query(Category).filter(Category.id == data.category_id).first():
        raise NotFoundError("Category not found")

    if db.query(Product).filter(Product.sku == data.sku).first():
        raise ConflictError("Product SKU already exists")

    product = Product(
        name=data.name,
        slug=data.slug,
        description=data.description,
        category_id=data.category_id,
        brand_id=data.brand_id,
        sku=data.sku,
        base_price=data.base_price,
        sale_price=data.sale_price,
        is_active=data.is_active,
        seller_id=current_user.id
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    log_audit(db, AuditAction.CREATE, "Product", str(product.id), current_user.id, new_values={"seller_id": current_user.id, "sku": product.sku})
    return ResponseSchema(message="Seller product created successfully", data=ProductOut.model_validate(product))

@router.get("/orders", response_model=ResponseSchema[List[OrderItemOut]])
def get_seller_order_items(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Find all products belonging to this seller
    seller_prod_ids = [p.id for p in db.query(Product.id).filter(Product.seller_id == current_user.id).all()]
    items = db.query(OrderItem).filter(OrderItem.product_id.in_(seller_prod_ids)).order_by(OrderItem.id.desc()).all()
    return ResponseSchema(data=[OrderItemOut.model_validate(i) for i in items])

@router.post("/order-items/{order_item_id}/fulfill", response_model=ResponseSchema[OrderItemOut])
def seller_fulfill_item(
    order_item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    item = db.query(OrderItem).filter(OrderItem.id == order_item_id).first()
    if not item:
        raise NotFoundError("Order item not found")

    # Scope check
    prod = db.query(Product).filter(Product.id == item.product_id).first()
    if not prod or (prod.seller_id != current_user.id and current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER]):
        raise ForbiddenError("You can only fulfill your own products")

    item.fulfilled_quantity = item.quantity
    item.fulfillment_status = "FULFILLED"
    db.commit()
    db.refresh(item)
    return ResponseSchema(message="Item fulfilled by seller", data=OrderItemOut.model_validate(item))

@router.post("/settlements/generate", response_model=ResponseSchema[List[SellerSettlementOut]])
def generate_seller_settlements(
    order_id: Optional[int] = Query(None),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    # Look for confirmed/delivered orders
    query = db.query(Order).filter(Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
    if order_id:
        query = query.filter(Order.id == order_id)
    orders = query.all()

    created_settlements = []
    for ord in orders:
        # Group order items by seller_id
        seller_items = {}
        for it in ord.items:
            prod = db.query(Product).filter(Product.id == it.product_id).first()
            if prod and prod.seller_id:
                if prod.seller_id not in seller_items:
                    seller_items[prod.seller_id] = 0.0
                seller_items[prod.seller_id] += float(it.total_price)

        for s_uid, gross in seller_items.items():
            existing = db.query(SellerSettlement).filter(
                SellerSettlement.seller_id == s_uid,
                SellerSettlement.order_id == ord.id
            ).first()
            if not existing:
                profile = db.query(SellerProfile).filter(SellerProfile.user_id == s_uid).first()
                comm_pct = float(profile.commission_rate) if profile else 10.0
                fee_pct = float(profile.platform_fee_percent) if profile else 2.0

                comm_amt = round((gross * comm_pct) / 100.0, 2)
                plat_fee = round((gross * fee_pct) / 100.0, 2)
                net_amt = round(gross - comm_amt - plat_fee, 2)

                settlement = SellerSettlement(
                    settlement_number=f"SET-{uuid.uuid4().hex[:8].upper()}",
                    seller_id=s_uid,
                    order_id=ord.id,
                    gross_amount=gross,
                    commission_amount=comm_amt,
                    platform_fee=plat_fee,
                    net_amount=net_amt,
                    status=SettlementStatus.PENDING
                )
                db.add(settlement)
                created_settlements.append(settlement)

    db.commit()
    for s in created_settlements:
        db.refresh(s)

    return ResponseSchema(message=f"Generated {len(created_settlements)} settlements", data=[SellerSettlementOut.model_validate(s) for s in created_settlements])

@router.get("/settlements", response_model=ResponseSchema[List[SellerSettlementOut]])
def get_seller_settlements(
    status: Optional[SettlementStatus] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(SellerSettlement)
    if current_user.role == UserRole.SELLER or (current_user.role == UserRole.CUSTOMER and not (current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER])):
        query = query.filter(SellerSettlement.seller_id == current_user.id)
    if status:
        query = query.filter(SellerSettlement.status == status)
    settlements = query.order_by(SellerSettlement.created_at.desc()).all()
    return ResponseSchema(data=[SellerSettlementOut.model_validate(s) for s in settlements])

@router.post("/settlements/{settlement_id}/payout", response_model=ResponseSchema[SellerSettlementOut])
def payout_seller_settlement(
    settlement_id: int,
    notes: Optional[str] = Query("Settlement paid out via bank transfer"),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    settlement = db.query(SellerSettlement).filter(SellerSettlement.id == settlement_id).first()
    if not settlement:
        raise NotFoundError("Settlement record not found")

    settlement.status = SettlementStatus.SETTLED
    settlement.settlement_date = datetime.now(timezone.utc)
    settlement.notes = notes
    db.commit()
    db.refresh(settlement)

    log_audit(db, AuditAction.FINANCIAL_ADJUSTMENT, "SellerSettlement", str(settlement.id), current_user.id, new_values={"status": "SETTLED", "net_amount": float(settlement.net_amount)})
    return ResponseSchema(message="Settlement paid and marked settled", data=SellerSettlementOut.model_validate(settlement))

@router.get("/sales-summary", response_model=ResponseSchema[SellerSalesSummaryOut])
def get_seller_sales_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    profile = db.query(SellerProfile).filter(SellerProfile.user_id == current_user.id).first()
    store_name = profile.store_name if profile else "Direct Marketplace"

    seller_prod_ids = [p.id for p in db.query(Product.id).filter(Product.seller_id == current_user.id).all()]
    items = db.query(OrderItem).filter(OrderItem.product_id.in_(seller_prod_ids)).all()

    total_orders = len({i.order_id for i in items})
    total_items = sum(i.quantity for i in items)
    gross_sales = sum(float(i.total_price) for i in items)

    settlements = db.query(SellerSettlement).filter(SellerSettlement.seller_id == current_user.id).all()
    total_commission = sum(float(s.commission_amount) + float(s.platform_fee) for s in settlements)
    net_earnings = sum(float(s.net_amount) for s in settlements if s.status == SettlementStatus.SETTLED)
    pending_amount = sum(float(s.net_amount) for s in settlements if s.status == SettlementStatus.PENDING)

    return ResponseSchema(
        data=SellerSalesSummaryOut(
            seller_id=current_user.id,
            store_name=store_name,
            total_orders=total_orders,
            total_items_sold=total_items,
            gross_sales=round(gross_sales, 2),
            total_commission_paid=round(total_commission, 2),
            net_earnings=round(net_earnings, 2),
            pending_settlements_amount=round(pending_amount, 2)
        )
    )
