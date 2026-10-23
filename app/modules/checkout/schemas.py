from typing import Optional
from pydantic import BaseModel
from app.common.enums import PaymentMethod

class CheckoutRequest(BaseModel):
    shipping_address_id: int
    billing_address_id: Optional[int] = None
    shipping_method_id: int
    coupon_code: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.STRIPE
    notes: Optional[str] = None

class CheckoutResponse(BaseModel):
    order_id: int
    order_number: str
    subtotal_amount: float
    discount_amount: float
    tax_amount: float
    shipping_amount: float
    total_amount: float
    status: str
    payment_status: str
    client_secret: Optional[str] = None
