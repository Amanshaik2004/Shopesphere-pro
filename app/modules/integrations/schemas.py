from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import IntegrationServiceType, IntegrationStatus

class IntegrationConfigCreate(BaseModel):
    service_type: IntegrationServiceType
    provider_name: str
    is_active: bool = True
    api_endpoint: Optional[str] = None
    webhook_secret: Optional[str] = None
    timeout_seconds: int = Field(default=30, ge=1, le=120)
    retry_limit: int = Field(default=3, ge=0, le=10)
    settings_json: Optional[str] = None

class IntegrationConfigOut(BaseModel):
    id: int
    service_type: IntegrationServiceType
    provider_name: str
    is_active: bool
    api_endpoint: Optional[str] = None
    webhook_secret_masked: Optional[str] = None
    timeout_seconds: int
    retry_limit: int
    created_at: datetime

    class Config:
        from_attributes = True

class IntegrationCallbackPayload(BaseModel):
    provider_name: str
    service_type: IntegrationServiceType
    event_type: str
    signature: Optional[str] = None
    payload: Dict[str, Any]

class IntegrationLogOut(BaseModel):
    id: int
    service_type: IntegrationServiceType
    provider_name: str
    event_type: str
    status: IntegrationStatus
    payload_summary: str
    response_summary: str
    error_message: Optional[str] = None
    retry_count: int
    can_retry: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ServiceHealthStatus(BaseModel):
    service_type: str
    provider_name: str
    status: str  # UP, DEGRADED, DOWN
    latency_ms: int
    is_active: bool

class IntegrationHealthResponse(BaseModel):
    system_status: str
    services: List[ServiceHealthStatus]
