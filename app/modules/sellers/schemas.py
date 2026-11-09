from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import SellerStatus, SettlementStatus

class SellerOnboardRequest(BaseModel):
    store_name: str
    business_name: str
    business_registration: Optional[str] = None
    bank_account_info: Optional[str] = None

class SellerReviewRequest(BaseModel):
    status: SellerStatus
    commission_rate: Optional[float] = Field(default=None, ge=0, le=100)
    platform_fee_percent: Optional[float] = Field(default=None, ge=0, le=100)
    rejection_reason: Optional[str] = None

class SellerProfileOut(BaseModel):
    id: int
    user_id: int
    store_name: str
    business_name: str
    business_registration: Optional[str] = None
    status: SellerStatus
    commission_rate: float
    platform_fee_percent: float
    bank_account_info: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SellerProductCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    category_id: int
    brand_id: Optional[int] = None
    sku: str
    base_price: float = Field(gt=0)
    sale_price: Optional[float] = None
    is_active: bool = True

class SellerSettlementOut(BaseModel):
    id: int
    settlement_number: str
    seller_id: int
    order_id: int
    gross_amount: float
    commission_amount: float
    platform_fee: float
    net_amount: float
    status: SettlementStatus
    settlement_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SellerSalesSummaryOut(BaseModel):
    seller_id: int
    store_name: str
    total_orders: int
    total_items_sold: int
    gross_sales: float
    total_commission_paid: float
    net_earnings: float
    pending_settlements_amount: float
