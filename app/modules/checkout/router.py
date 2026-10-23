from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import (
    Cart, CartItem, Order, OrderItem, OrderStatusHistory, Coupon, TaxRate, ShippingMethod
)
from app.models.catalog import Product, ProductVariant
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.payments import Payment, PaymentTransaction, CODRecord
from app.models.users import User, Address
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user
from app.common.utils import generate_order_number
from app.common.enums import OrderStatus, PaymentStatus, PaymentMethod, DiscountType, AuditAction
from app.core.exceptions import BadRequestError, NotFoundError, InsufficientStockError
from app.core.audit import log_audit
from app.integrations.payments.stripe_gateway import stripe_gateway
from app.modules.checkout.schemas import CheckoutRequest, CheckoutResponse

router = APIRouter(prefix="/checkout", tags=["Module 24: Checkout Management"])

@router.post("", response_model=ResponseSchema[CheckoutResponse])
def process_checkout(
    req: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart or not cart.items:
        raise BadRequestError("Cannot checkout with an empty cart")

    shipping_addr = db.query(Address).filter(
        Address.id == req.shipping_address_id,
        Address.user_id == current_user.id
    ).first()
    if not shipping_addr:
        raise NotFoundError("Shipping address not found or does not belong to you")

    billing_addr_id = req.billing_address_id or req.shipping_address_id

    shipping_method = db.query(ShippingMethod).filter(
        ShippingMethod.id == req.shipping_method_id,
        ShippingMethod.is_active == True
    ).first()
    if not shipping_method:
        raise NotFoundError("Shipping method not found or inactive")

    # Validate stock and calculate prices
    items_to_order = []
    subtotal = 0.0

    for c_item in cart.items:
        prod = db.query(Product).filter(Product.id == c_item.product_id, Product.is_active == True).first()
        if not prod:
            raise BadRequestError(f"Product {c_item.product_id} is unavailable")

        unit_price = float(prod.sale_price if prod.sale_price else prod.base_price)
        prod_name = prod.name
        sku = prod.sku

        if c_item.variant_id:
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == c_item.variant_id,
                ProductVariant.is_active == True
            ).first()
            if not variant:
                raise BadRequestError(f"Variant {c_item.variant_id} is unavailable")
            unit_price += float(variant.additional_price)
            sku = variant.sku
            prod_name = f"{prod.name} ({variant.name})"

        # Check stock in warehouse
        inv_item = db.query(InventoryItem).filter(
            InventoryItem.product_id == c_item.product_id,
            InventoryItem.variant_id == c_item.variant_id
        ).first()

        if not inv_item or inv_item.available_quantity < c_item.quantity:
            raise InsufficientStockError(f"Insufficient stock available for {prod_name}")

        line_total = round(unit_price * c_item.quantity, 2)
        subtotal += line_total

        items_to_order.append({
            "product_id": c_item.product_id,
            "variant_id": c_item.variant_id,
            "product_name": prod_name,
            "sku": sku,
            "unit_price": unit_price,
            "quantity": c_item.quantity,
            "total_price": line_total,
            "inventory_item": inv_item
        })

    subtotal = round(subtotal, 2)
    discount = 0.0

    # Apply Coupon
    now = datetime.now(timezone.utc)
    if req.coupon_code:
        coupon = db.query(Coupon).filter(
            Coupon.code == req.coupon_code.upper(),
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
            discount = disc_val
            coupon.usage_count += 1

    discount = min(round(discount, 2), subtotal)

    # Shipping cost
    if shipping_method.free_shipping_threshold and subtotal >= float(shipping_method.free_shipping_threshold):
        shipping_amount = 0.0
    else:
        shipping_amount = float(shipping_method.base_cost)

    # Tax calculation
    tax_rate = 0.0
    tax_record = db.query(TaxRate).filter(
        TaxRate.is_active == True,
        TaxRate.country == shipping_addr.country
    ).first()
    if tax_record:
        tax_rate = float(tax_record.rate_percentage) / 100.0

    tax_amount = round((subtotal - discount) * tax_rate, 2)
    total_amount = round(subtotal - discount + tax_amount + shipping_amount, 2)

    # Reserve inventory
    for item_data in items_to_order:
        inv: InventoryItem = item_data["inventory_item"]
        inv.reserved_quantity += item_data["quantity"]
        movement = InventoryMovement(
            inventory_item_id=inv.id,
            movement_type="RESERVE",
            quantity=item_data["quantity"],
            reference_type="CHECKOUT",
            note="Stock reserved for checkout"
        )
        db.add(movement)

    # Create Order
    order_num = generate_order_number()
    order = Order(
        order_number=order_num,
        user_id=current_user.id,
        shipping_address_id=req.shipping_address_id,
        billing_address_id=billing_addr_id,
        shipping_method_id=req.shipping_method_id,
        subtotal_amount=subtotal,
        discount_amount=discount,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        total_amount=total_amount,
        status=OrderStatus.PENDING,
        coupon_code=req.coupon_code,
        notes=req.notes
    )
    db.add(order)
    db.flush()

    # Create Order Items
    for item_data in items_to_order:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data["product_id"],
            variant_id=item_data["variant_id"],
            product_name=item_data["product_name"],
            sku=item_data["sku"],
            unit_price=item_data["unit_price"],
            quantity=item_data["quantity"],
            total_price=item_data["total_price"],
            fulfillment_status="PENDING"
        )
        db.add(order_item)

    # Status history entry
    history = OrderStatusHistory(
        order_id=order.id,
        from_status=None,
        to_status=OrderStatus.PENDING,
        changed_by_id=current_user.id,
        comment="Checkout completed. Order placed."
    )
    db.add(history)

    # Payment Record initialization
    payment = Payment(
        order_id=order.id,
        payment_method=req.payment_method,
        amount=total_amount,
        currency="USD",
        status=PaymentStatus.PENDING
    )
    db.add(payment)
    db.flush()

    client_secret = None
    if req.payment_method == PaymentMethod.STRIPE:
        stripe_res = stripe_gateway.create_payment_intent(total_amount, metadata={"order_id": order.id, "order_number": order_num})
        payment.transaction_ref = stripe_res["id"]
        client_secret = stripe_res.get("client_secret")
    elif req.payment_method == PaymentMethod.COD:
        cod_rec = CODRecord(order_id=order.id, amount=total_amount, collection_status="PENDING")
        db.add(cod_rec)

    # Clear customer cart
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    db.refresh(order)

    log_audit(db, AuditAction.CREATE, "Order", str(order.id), current_user.id, new_values={"order_number": order.order_number, "total": total_amount})

    return ResponseSchema(
        message="Checkout successful, order placed in pending status",
        data=CheckoutResponse(
            order_id=order.id,
            order_number=order.order_number,
            subtotal_amount=subtotal,
            discount_amount=discount,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            total_amount=total_amount,
            status=order.status.value,
            payment_status=payment.status.value,
            client_secret=client_secret
        )
    )
