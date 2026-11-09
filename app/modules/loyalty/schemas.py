from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import LoyaltyTier, LoyaltyTransactionType

class LoyaltyAccountOut(BaseModel):
    id: int
    user_id: int
    points_balance: int
    lifetime_earned: int
    lifetime_redeemed: int
    tier: LoyaltyTier
    approximate_dollar_value: float = 0.0

    class Config:
        from_attributes = True

class LoyaltyTransactionOut(BaseModel):
    id: int
    account_id: int
    order_id: Optional[int] = None
    transaction_type: LoyaltyTransactionType
    points: int
    dollar_value: float
    reason: str
    created_at: datetime

    class Config:
        from_attributes = True

class LoyaltyRedeemRequest(BaseModel):
    points: int = Field(..., gt=0)

class LoyaltyRedeemResponse(BaseModel):
    points_redeemed: int
    discount_amount: float
    remaining_points: int

class LoyaltyRuleCreate(BaseModel):
    name: str
    points_per_dollar: float = Field(default=1.0, gt=0)
    redemption_rate: float = Field(default=100.0, gt=0)
    min_points_to_redeem: int = Field(default=50, ge=1)
    points_expiry_days: int = Field(default=365, ge=1)
    is_active: bool = True

class LoyaltyRuleOut(BaseModel):
    id: int
    name: str
    points_per_dollar: float
    redemption_rate: float
    min_points_to_redeem: int
    points_expiry_days: int
    is_active: bool

    class Config:
        from_attributes = True

class LoyaltyAdjustmentRequest(BaseModel):
    user_id: int
    points: int  # can be positive or negative
    reason: str

class LoyaltyReverseRequest(BaseModel):
    order_id: int
    reason: str
