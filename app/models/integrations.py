from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin
from app.common.enums import IntegrationServiceType, IntegrationStatus

class IntegrationConfig(Base, TimestampMixin):
    __tablename__ = "integration_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    service_type: Mapped[IntegrationServiceType] = mapped_column(SQLEnum(IntegrationServiceType), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    retry_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    settings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    service_type: Mapped[IntegrationServiceType] = mapped_column(SQLEnum(IntegrationServiceType), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[IntegrationStatus] = mapped_column(SQLEnum(IntegrationStatus), default=IntegrationStatus.SUCCESS, nullable=False)
    payload_summary: Mapped[str] = mapped_column(Text, nullable=False)  # Sanitized, no secrets!
    response_summary: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    can_retry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
