from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Numeric, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin
from app.common.enums import SupportCaseCategory, SupportCaseStatus, TicketPriority

class SupportCase(Base, TimestampMixin):
    __tablename__ = "support_cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    return_id: Mapped[Optional[int]] = mapped_column(ForeignKey("return_requests.id", ondelete="SET NULL"), nullable=True)
    category: Mapped[SupportCaseCategory] = mapped_column(SQLEnum(SupportCaseCategory), default=SupportCaseCategory.GENERAL, nullable=False)
    priority: Mapped[TicketPriority] = mapped_column(SQLEnum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    status: Mapped[SupportCaseStatus] = mapped_column(SQLEnum(SupportCaseStatus), default=SupportCaseStatus.OPEN, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Dispute & Escalation Tracking
    is_dispute: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chargeback_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    dispute_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. UNDER_REVIEW, WON, LOST
    escalation_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    escalated_to_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # SLA Metrics
    first_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    messages: Mapped[List["CaseMessage"]] = relationship("CaseMessage", back_populates="case", cascade="all, delete-orphan")


class CaseMessage(Base):
    __tablename__ = "case_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("support_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    case: Mapped["SupportCase"] = relationship("SupportCase", back_populates="messages")
