from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Numeric, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin
from app.common.enums import InventoryTransferStatus, ReservationStatus

class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="United States", nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    items: Mapped[List["InventoryItem"]] = relationship("InventoryItem", back_populates="warehouse", cascade="all, delete-orphan")


class InventoryItem(Base, TimestampMixin):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="items")
    movements: Mapped[List["InventoryMovement"]] = relationship("InventoryMovement", back_populates="inventory_item", cascade="all, delete-orphan")
    alerts: Mapped[List["StockAlert"]] = relationship("StockAlert", back_populates="inventory_item", cascade="all, delete-orphan")

    @property
    def available_quantity(self) -> int:
        return max(0, self.quantity - self.reserved_quantity)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ADD, REDUCE, RESERVE, RELEASE, TRANSFER_OUT, TRANSFER_IN
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ORDER, TRANSFER, ADJUSTMENT, RETURN
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    performed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    inventory_item: Mapped["InventoryItem"] = relationship("InventoryItem", back_populates="movements")


class InventoryTransfer(Base, TimestampMixin):
    __tablename__ = "inventory_transfers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transfer_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    source_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    target_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[InventoryTransferStatus] = mapped_column(SQLEnum(InventoryTransferStatus), default=InventoryTransferStatus.REQUESTED, nullable=False)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    items: Mapped[List["InventoryTransferItem"]] = relationship("InventoryTransferItem", back_populates="transfer", cascade="all, delete-orphan")


class InventoryTransferItem(Base):
    __tablename__ = "inventory_transfer_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("inventory_transfers.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    dispatched_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    transfer: Mapped["InventoryTransfer"] = relationship("InventoryTransfer", back_populates="items")


class StockAlert(Base):
    __tablename__ = "stock_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    inventory_item: Mapped["InventoryItem"] = relationship("InventoryItem", back_populates="alerts")


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(SQLEnum(ReservationStatus), default=ReservationStatus.ACTIVE, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class InventoryBatch(Base):
    __tablename__ = "inventory_batches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_number: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_per_unit: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    received_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class StockDiscrepancy(Base):
    __tablename__ = "stock_discrepancies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    system_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    physical_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    discrepancy: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reconciled_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
