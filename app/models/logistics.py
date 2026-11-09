from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Numeric, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin
from app.common.enums import ShipmentStatus, ReturnStatus, ExchangeStatus, WarrantyStatus

class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    carrier: Mapped[str] = mapped_column(String(100), default="Standard Express", nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    status: Mapped[ShipmentStatus] = mapped_column(SQLEnum(ShipmentStatus), default=ShipmentStatus.PENDING, nullable=False, index=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    shipping_label_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    tracking_events: Mapped[List["ShipmentTrackingEvent"]] = relationship("ShipmentTrackingEvent", back_populates="shipment", cascade="all, delete-orphan")
    delivery_assignment: Mapped[Optional["DeliveryAssignment"]] = relationship("DeliveryAssignment", back_populates="shipment", uselist=False, cascade="all, delete-orphan")
    items: Mapped[List["ShipmentItem"]] = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentItem(Base):
    __tablename__ = "shipment_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="items")


class ShipmentTrackingEvent(Base):
    __tablename__ = "shipment_tracking_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[ShipmentStatus] = mapped_column(SQLEnum(ShipmentStatus), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="tracking_events")


class DeliveryAssignment(Base, TimestampMixin):
    __tablename__ = "delivery_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), unique=True, nullable=False)
    delivery_person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    confirmation_signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    proof_of_delivery_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="delivery_assignment")


class ReturnRequest(Base, TimestampMixin):
    __tablename__ = "return_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    return_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ReturnStatus] = mapped_column(SQLEnum(ReturnStatus), default=ReturnStatus.REQUESTED, nullable=False, index=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refund_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    inspection_outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    evidence_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    inspection_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    items: Mapped[List["ReturnItem"]] = relationship("ReturnItem", back_populates="return_request", cascade="all, delete-orphan")


class ReturnItem(Base):
    __tablename__ = "return_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    return_request_id: Mapped[int] = mapped_column(ForeignKey("return_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    condition: Mapped[Optional[str]] = mapped_column(String(50), default="UNOPENED", nullable=True)

    return_request: Mapped["ReturnRequest"] = relationship("ReturnRequest", back_populates="items")


class ExchangeRequest(Base, TimestampMixin):
    __tablename__ = "exchange_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    return_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("return_requests.id", ondelete="SET NULL"), nullable=True)
    original_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False)
    replacement_variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=True)
    status: Mapped[ExchangeStatus] = mapped_column(SQLEnum(ExchangeStatus), default=ExchangeStatus.REQUESTED, nullable=False, index=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WarrantyClaim(Base, TimestampMixin):
    __tablename__ = "warranty_claims"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    claim_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    claim_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[WarrantyStatus] = mapped_column(SQLEnum(WarrantyStatus), default=WarrantyStatus.PENDING, nullable=False, index=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
