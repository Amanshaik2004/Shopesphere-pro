from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Numeric, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin
from app.common.enums import SellerStatus, SettlementStatus

class SellerProfile(Base, TimestampMixin):
    __tablename__ = "seller_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    store_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    business_name: Mapped[str] = mapped_column(String(150), nullable=False)
    business_registration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[SellerStatus] = mapped_column(SQLEnum(SellerStatus), default=SellerStatus.PENDING, nullable=False, index=True)
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=10.0, nullable=False)
    platform_fee_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=2.0, nullable=False)
    bank_account_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class CommissionRule(Base, TimestampMixin):
    __tablename__ = "commission_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    seller_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=10.0, nullable=False)
    fixed_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SellerSettlement(Base):
    __tablename__ = "seller_settlements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    settlement_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    gross_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    commission_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    platform_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    net_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[SettlementStatus] = mapped_column(SQLEnum(SettlementStatus), default=SettlementStatus.PENDING, nullable=False, index=True)
    settlement_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
