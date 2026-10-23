from typing import Optional, List
from pydantic import BaseModel, Field

class AddToCartRequest(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(gt=0, default=1)

class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(gt=0)

class CartItemDetail(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    sku: str
    unit_price: float
    quantity: int
    line_total: float
    is_available: bool

class CartSummaryOut(BaseModel):
    cart_id: int
    items: List[CartItemDetail]
    subtotal: float
    discount_amount: float = 0.0
    tax_amount: float = 0.0
    shipping_amount: float = 0.0
    total_amount: float
    coupon_code: Optional[str] = None

class CartPriceCalculationRequest(BaseModel):
    coupon_code: Optional[str] = None
    shipping_method_id: Optional[int] = None
    state: Optional[str] = None
    country: Optional[str] = "United States"
