from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.catalog import Product, ProductVariant, PriceHistory
from app.models.orders import Coupon, Promotion, PromotionRedemption, ShippingMethod, TaxRate
from app.models.segmentation import CustomerSegmentMember
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles, get_optional_current_user
from app.common.enums import UserRole, AuditAction, DiscountType, PromotionType
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.modules.pricing.schemas import (
    PriceUpdateRequest, PriceHistoryOut, PriceBreakdownRequest,
    PriceBreakdownResponse, ItemBreakdownOut, AppliedPromotionOut
)

router = APIRouter(prefix="/pricing", tags=["Module 12: Product Pricing"])

@router.put("/product/{product_id}", response_model=ResponseSchema[PriceHistoryOut])
def update_product_price(
    product_id: int,
    data: PriceUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product not found")

    if data.sale_price is not None and data.sale_price >= data.base_price:
        raise BadRequestError("Sale price must be strictly less than base price")

    old_base_price = product.base_price
    old_sale_price = product.sale_price

    product.base_price = data.base_price
    product.sale_price = data.sale_price

    history = PriceHistory(
        product_id=product.id,
        old_base_price=old_base_price,
        new_base_price=product.base_price,
        old_sale_price=old_sale_price,
        new_sale_price=product.sale_price,
        changed_by_user_id=current_user.id,
        reason=data.reason
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    log_audit(db, AuditAction.UPDATE, "Pricing", str(product.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Pricing updated and history logged", data=PriceHistoryOut.model_validate(history))

@router.get("/product/{product_id}/history", response_model=ResponseSchema[List[PriceHistoryOut]])
def get_price_history(product_id: int, db: Session = Depends(get_db)):
    if not db.query(Product).filter(Product.id == product_id).first():
        raise NotFoundError("Product not found")
    history = db.query(PriceHistory).filter(PriceHistory.product_id == product_id).order_by(PriceHistory.created_at.desc()).all()
    return ResponseSchema(data=[PriceHistoryOut.model_validate(h) for h in history])


# =========================================================================
# Phase 2: Comprehensive Price Breakdown API
# =========================================================================

@router.post("/price-breakdown", response_model=ResponseSchema[PriceBreakdownResponse])
def calculate_price_breakdown(
    data: PriceBreakdownRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    user_id = data.customer_id or (current_user.id if current_user else None)

    # 1. Fetch active promotions
    active_promos = db.query(Promotion).filter(
        Promotion.is_active == True,
        Promotion.start_date <= now,
        Promotion.end_date >= now
    ).order_by(Promotion.priority.desc()).all()

    # User customer segments if applicable
    user_segment_ids = set()
    if user_id:
        user_segment_ids = {m.segment_id for m in db.query(CustomerSegmentMember).filter(CustomerSegmentMember.user_id == user_id).all()}

    items_out: List[ItemBreakdownOut] = []
    subtotal = 0.0
    prod_promo_disc = 0.0
    cat_promo_disc = 0.0
    applied_promotions: List[AppliedPromotionOut] = []

    # Map promotions by type
    product_promos = [p for p in active_promos if p.promotion_type == PromotionType.PRODUCT and p.product_id]
    category_promos = [p for p in active_promos if p.promotion_type == PromotionType.CATEGORY and p.category_id]
    cart_promos = [p for p in active_promos if p.promotion_type == PromotionType.CART]
    segment_promos = [p for p in active_promos if p.promotion_type == PromotionType.CUSTOMER_SEGMENT and p.customer_segment_id in user_segment_ids]

    for item_input in data.items:
        prod = db.query(Product).filter(Product.id == item_input.product_id).first()
        if not prod:
            raise NotFoundError(f"Product #{item_input.product_id} not found")

        variant = None
        if item_input.variant_id:
            variant = db.query(ProductVariant).filter(ProductVariant.id == item_input.variant_id, ProductVariant.product_id == prod.id).first()

        unit_p = float(prod.sale_price if prod.sale_price is not None else prod.base_price)
        if variant:
            unit_p += float(variant.additional_price)

        line_subtotal = round(unit_p * item_input.quantity, 2)
        subtotal += line_subtotal

        # Check Product Promotions
        item_prod_disc = 0.0
        matching_prod_promo = next((p for p in product_promos if p.product_id == prod.id), None)
        if matching_prod_promo:
            if matching_prod_promo.discount_type == DiscountType.PERCENTAGE:
                disc = (line_subtotal * float(matching_prod_promo.discount_value)) / 100.0
            else:
                disc = float(matching_prod_promo.discount_value) * item_input.quantity
            if matching_prod_promo.max_discount_amount:
                disc = min(disc, float(matching_prod_promo.max_discount_amount))
            disc = min(disc, line_subtotal)
            item_prod_disc = round(disc, 2)
            prod_promo_disc += item_prod_disc
            applied_promotions.append(AppliedPromotionOut(
                promotion_id=matching_prod_promo.id,
                promotion_name=matching_prod_promo.name,
                promotion_type="PRODUCT",
                discount_amount=item_prod_disc
            ))

        # Check Category Promotions
        item_cat_disc = 0.0
        remaining_line = line_subtotal - item_prod_disc
        matching_cat_promo = next((p for p in category_promos if p.category_id == prod.category_id), None)
        if matching_cat_promo and remaining_line > 0:
            if matching_cat_promo.discount_type == DiscountType.PERCENTAGE:
                disc = (remaining_line * float(matching_cat_promo.discount_value)) / 100.0
            else:
                disc = float(matching_cat_promo.discount_value) * item_input.quantity
            if matching_cat_promo.max_discount_amount:
                disc = min(disc, float(matching_cat_promo.max_discount_amount))
            disc = min(disc, remaining_line)
            item_cat_disc = round(disc, 2)
            cat_promo_disc += item_cat_disc
            applied_promotions.append(AppliedPromotionOut(
                promotion_id=matching_cat_promo.id,
                promotion_name=matching_cat_promo.name,
                promotion_type="CATEGORY",
                discount_amount=item_cat_disc
            ))

        net_line = round(line_subtotal - item_prod_disc - item_cat_disc, 2)
        items_out.append(ItemBreakdownOut(
            product_id=prod.id,
            variant_id=variant.id if variant else None,
            product_name=prod.name,
            sku=variant.sku if variant else prod.sku,
            quantity=item_input.quantity,
            unit_price=round(unit_p, 2),
            item_subtotal=line_subtotal,
            product_discount=item_prod_disc,
            category_discount=item_cat_disc,
            net_item_price=net_line
        ))

    subtotal = round(subtotal, 2)
    running_total = max(0.0, subtotal - prod_promo_disc - cat_promo_disc)

    # 2. Cart Promotions
    cart_promo_disc = 0.0
    for cp in cart_promos:
        if running_total >= float(cp.min_cart_value):
            if cp.discount_type == DiscountType.PERCENTAGE:
                disc = (running_total * float(cp.discount_value)) / 100.0
            else:
                disc = float(cp.discount_value)
            if cp.max_discount_amount:
                disc = min(disc, float(cp.max_discount_amount))
            disc = min(disc, running_total)
            cart_promo_disc += round(disc, 2)
            running_total = max(0.0, running_total - disc)
            applied_promotions.append(AppliedPromotionOut(
                promotion_id=cp.id,
                promotion_name=cp.name,
                promotion_type="CART",
                discount_amount=round(disc, 2)
            ))
            if not cp.can_stack:
                break

    # 3. Customer Segment Promotions
    segment_promo_disc = 0.0
    for sp in segment_promos:
        if running_total > 0 and running_total >= float(sp.min_cart_value):
            if sp.discount_type == DiscountType.PERCENTAGE:
                disc = (running_total * float(sp.discount_value)) / 100.0
            else:
                disc = float(sp.discount_value)
            if sp.max_discount_amount:
                disc = min(disc, float(sp.max_discount_amount))
            disc = min(disc, running_total)
            segment_promo_disc += round(disc, 2)
            running_total = max(0.0, running_total - disc)
            applied_promotions.append(AppliedPromotionOut(
                promotion_id=sp.id,
                promotion_name=sp.name,
                promotion_type="CUSTOMER_SEGMENT",
                discount_amount=round(disc, 2)
            ))
            if not sp.can_stack:
                break

    # 4. Coupon Code
    coupon_disc = 0.0
    if data.coupon_code:
        code = data.coupon_code.upper().strip()
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        if coupon and coupon.is_active:
            valid_from = coupon.valid_from.replace(tzinfo=timezone.utc) if coupon.valid_from.tzinfo is None else coupon.valid_from
            valid_to = coupon.valid_to.replace(tzinfo=timezone.utc) if coupon.valid_to.tzinfo is None else coupon.valid_to
            if valid_from <= now <= valid_to and running_total >= float(coupon.min_purchase_amount):
                if coupon.discount_type == DiscountType.PERCENTAGE:
                    disc = (running_total * float(coupon.discount_value)) / 100.0
                else:
                    disc = float(coupon.discount_value)
                if coupon.max_discount_amount:
                    disc = min(disc, float(coupon.max_discount_amount))
                disc = min(disc, running_total)
                coupon_disc = round(disc, 2)
                running_total = max(0.0, running_total - coupon_disc)
                applied_promotions.append(AppliedPromotionOut(
                    promotion_name=f"Coupon: {coupon.code}",
                    promotion_type="COUPON",
                    discount_amount=coupon_disc
                ))

    # 5. Shipping
    shipping_fee = 0.0
    if data.shipping_method_id:
        ship_method = db.query(ShippingMethod).filter(ShippingMethod.id == data.shipping_method_id).first()
        if ship_method:
            shipping_fee = float(ship_method.base_cost)
            if ship_method.free_shipping_threshold and running_total >= float(ship_method.free_shipping_threshold):
                shipping_fee = 0.0
    else:
        # Default flat shipping
        shipping_fee = 10.0 if running_total > 0 and running_total < 100 else 0.0

    # 6. Tax (standard 5% or query TaxRate)
    tax_rate = db.query(TaxRate).filter(TaxRate.is_active == True).first()
    tax_percentage = float(tax_rate.rate_percentage) if tax_rate else 5.0
    tax_amount = round((running_total * tax_percentage) / 100.0, 2)

    total_discount = round(prod_promo_disc + cat_promo_disc + cart_promo_disc + segment_promo_disc + coupon_disc, 2)
    final_total = round(running_total + tax_amount + shipping_fee, 2)

    return ResponseSchema(
        message="Price breakdown computed successfully",
        data=PriceBreakdownResponse(
            items=items_out,
            subtotal_amount=subtotal,
            product_promotions_discount=round(prod_promo_disc, 2),
            category_promotions_discount=round(cat_promo_disc, 2),
            cart_promotions_discount=round(cart_promo_disc, 2),
            customer_segment_discount=round(segment_promo_disc, 2),
            coupon_discount=round(coupon_disc, 2),
            total_discount=total_discount,
            tax_amount=tax_amount,
            shipping_amount=round(shipping_fee, 2),
            total_amount=final_total,
            applied_promotions=applied_promotions
        )
    )
