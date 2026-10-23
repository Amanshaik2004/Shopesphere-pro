from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.orders import Cart, CartItem, Coupon, Promotion, TaxRate, ShippingMethod
from app.models.catalog import Product, ProductVariant
from app.models.inventory import InventoryItem
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_active_user
from app.common.enums import DiscountType
from app.core.exceptions import NotFoundError, BadRequestError, InsufficientStockError
from app.modules.carts.schemas import (
    AddToCartRequest, UpdateCartItemRequest, CartSummaryOut, CartItemDetail, CartPriceCalculationRequest
)

router = APIRouter(prefix="/cart", tags=["Module 17 & 18: Shopping Cart & Price Calculation"])

def _get_or_create_cart(user_id: int, db: Session) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart

def _get_item_price_and_availability(item: CartItem, db: Session):
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if not product or not product.is_active:
        return 0.0, "Inactive", "N/A", False
    
    price = float(product.sale_price if product.sale_price else product.base_price)
    sku = product.sku
    name = product.name

    if item.variant_id:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if variant and variant.is_active:
            price += float(variant.additional_price)
            sku = variant.sku
            name = f"{product.name} ({variant.name})"

    # Check total inventory across warehouses
    available_stock = db.query(func.sum(InventoryItem.quantity - InventoryItem.reserved_quantity)).filter(
        InventoryItem.product_id == item.product_id,
        InventoryItem.variant_id == item.variant_id
    ).scalar() or 0

    is_available = available_stock >= item.quantity
    return price, name, sku, is_available

@router.get("", response_model=ResponseSchema[CartSummaryOut])
def get_cart(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    cart = _get_or_create_cart(current_user.id, db)
    items_detail = []
    subtotal = 0.0

    for item in cart.items:
        price, name, sku, is_avail = _get_item_price_and_availability(item, db)
        line_total = round(price * item.quantity, 2)
        subtotal += line_total
        items_detail.append(CartItemDetail(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=name,
            sku=sku,
            unit_price=price,
            quantity=item.quantity,
            line_total=line_total,
            is_available=is_avail
        ))

    subtotal = round(subtotal, 2)
    return ResponseSchema(data=CartSummaryOut(
        cart_id=cart.id,
        items=items_detail,
        subtotal=subtotal,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=subtotal
    ))

@router.post("/items", response_model=ResponseSchema[CartSummaryOut])
def add_to_cart(
    data: AddToCartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == data.product_id, Product.is_active == True).first()
    if not product:
        raise NotFoundError("Product not found or inactive")

    cart = _get_or_create_cart(current_user.id, db)
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == data.product_id,
        CartItem.variant_id == data.variant_id
    ).first()

    if existing_item:
        existing_item.quantity += data.quantity
    else:
        new_item = CartItem(
            cart_id=cart.id,
            product_id=data.product_id,
            variant_id=data.variant_id,
            quantity=data.quantity
        )
        db.add(new_item)

    db.commit()
    return get_cart(current_user=current_user, db=db)

@router.put("/items/{item_id}", response_model=ResponseSchema[CartSummaryOut])
def update_cart_item(
    item_id: int,
    data: UpdateCartItemRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cart = _get_or_create_cart(current_user.id, db)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise NotFoundError("Cart item not found")

    item.quantity = data.quantity
    db.commit()
    return get_cart(current_user=current_user, db=db)

@router.delete("/items/{item_id}", response_model=ResponseSchema[CartSummaryOut])
def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cart = _get_or_create_cart(current_user.id, db)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise NotFoundError("Cart item not found")

    db.delete(item)
    db.commit()
    return get_cart(current_user=current_user, db=db)

@router.delete("/clear", response_model=ResponseSchema[MessageResponse])
def clear_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cart = _get_or_create_cart(current_user.id, db)
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    return ResponseSchema(message="Cart cleared successfully", data=MessageResponse(message="All items removed"))

# Module 18: Cart Price Calculation
@router.post("/calculate", response_model=ResponseSchema[CartSummaryOut])
def calculate_cart_price(
    calc_data: CartPriceCalculationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cart = _get_or_create_cart(current_user.id, db)
    items_detail = []
    subtotal = 0.0

    for item in cart.items:
        price, name, sku, is_avail = _get_item_price_and_availability(item, db)
        line_total = round(price * item.quantity, 2)
        subtotal += line_total
        items_detail.append(CartItemDetail(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=name,
            sku=sku,
            unit_price=price,
            quantity=item.quantity,
            line_total=line_total,
            is_available=is_avail
        ))

    subtotal = round(subtotal, 2)
    discount = 0.0

    # Apply Coupon if provided
    now = datetime.now(timezone.utc)
    if calc_data.coupon_code:
        coupon = db.query(Coupon).filter(
            Coupon.code == calc_data.coupon_code.upper(),
            Coupon.is_active == True,
            Coupon.valid_from <= now,
            Coupon.valid_to >= now
        ).first()

        if coupon and subtotal >= float(coupon.min_purchase_amount):
            if coupon.discount_type == DiscountType.PERCENTAGE:
                disc_val = subtotal * (float(coupon.discount_value) / 100.0)
            else:
                disc_val = float(coupon.discount_value)

            if coupon.max_discount_amount:
                disc_val = min(disc_val, float(coupon.max_discount_amount))
            discount += disc_val

    discount = min(round(discount, 2), subtotal)

    # Shipping Calculation
    shipping_amount = 0.0
    if calc_data.shipping_method_id:
        shipping_method = db.query(ShippingMethod).filter(
            ShippingMethod.id == calc_data.shipping_method_id,
            ShippingMethod.is_active == True
        ).first()
        if shipping_method:
            if shipping_method.free_shipping_threshold and subtotal >= float(shipping_method.free_shipping_threshold):
                shipping_amount = 0.0
            else:
                shipping_amount = float(shipping_method.base_cost)

    # Tax Calculation
    tax_rate = 0.0
    tax_rule = db.query(TaxRate).filter(
        TaxRate.is_active == True,
        TaxRate.country == calc_data.country
    ).first()
    if tax_rule:
        tax_rate = float(tax_rule.rate_percentage) / 100.0

    tax_amount = round((subtotal - discount) * tax_rate, 2)
    total_amount = round(subtotal - discount + tax_amount + shipping_amount, 2)

    return ResponseSchema(data=CartSummaryOut(
        cart_id=cart.id,
        items=items_detail,
        subtotal=subtotal,
        discount_amount=discount,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        total_amount=total_amount,
        coupon_code=calc_data.coupon_code
    ))
