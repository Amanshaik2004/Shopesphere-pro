from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Numeric, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin
from app.common.enums import LoyaltyTier, LoyaltyTransactionType

class LoyaltyAccount(Base, TimestampMixin):
    __tablename__ = "loyalty_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    points_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_redeemed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tier: Mapped[LoyaltyTier] = mapped_column(SQLEnum(LoyaltyTier), default=LoyaltyTier.BRONZE, nullable=False)

    transactions: Mapped[List["LoyaltyTransaction"]] = relationship("LoyaltyTransaction", back_populates="account", cascade="all, delete-orphan")


class LoyaltyRule(Base, TimestampMixin):
    __tablename__ = "loyalty_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    points_per_dollar: Mapped[float] = mapped_column(Numeric(5, 2), default=1.0, nullable=False)
    redemption_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=100.0, nullable=False)  # e.g., 100 points = $1
    min_points_to_redeem: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    points_expiry_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("loyalty_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_type: Mapped[LoyaltyTransactionType] = mapped_column(SQLEnum(LoyaltyTransactionType), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    dollar_value: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    account: Mapped["LoyaltyAccount"] = relationship("LoyaltyAccount", back_populates="transactions")
