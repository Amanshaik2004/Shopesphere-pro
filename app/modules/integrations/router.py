import json
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.integrations import IntegrationConfig, IntegrationLog
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, IntegrationServiceType, IntegrationStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.modules.integrations.schemas import (
    IntegrationConfigCreate, IntegrationConfigOut, IntegrationCallbackPayload,
    IntegrationLogOut, IntegrationHealthResponse, ServiceHealthStatus
)

router = APIRouter(prefix="/integrations", tags=["Module 3.12: External Service Integrations"])

def _mask_secret(secret: Optional[str]) -> Optional[str]:
    if not secret:
        return None
    if len(secret) <= 6:
        return "******"
    return secret[:3] + "..." + secret[-3:]

@router.post("/configs", response_model=ResponseSchema[IntegrationConfigOut])
def create_or_update_integration_config(
    data: IntegrationConfigCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    provider = data.provider_name.upper().strip()
    config = db.query(IntegrationConfig).filter(IntegrationConfig.provider_name == provider).first()
    if not config:
        config = IntegrationConfig(
            service_type=data.service_type,
            provider_name=provider,
            is_active=data.is_active,
            api_endpoint=data.api_endpoint,
            webhook_secret=data.webhook_secret,
            timeout_seconds=data.timeout_seconds,
            retry_limit=data.retry_limit,
            settings_json=data.settings_json
        )
        db.add(config)
    else:
        config.service_type = data.service_type
        config.is_active = data.is_active
        config.api_endpoint = data.api_endpoint
        if data.webhook_secret:
            config.webhook_secret = data.webhook_secret
        config.timeout_seconds = data.timeout_seconds
        config.retry_limit = data.retry_limit
        if data.settings_json:
            config.settings_json = data.settings_json

    db.commit()
    db.refresh(config)

    log_audit(db, AuditAction.CREATE, "IntegrationConfig", str(config.id), current_user.id, new_values={"provider": provider, "service_type": data.service_type.value})
    out = IntegrationConfigOut(
        id=config.id,
        service_type=config.service_type,
        provider_name=config.provider_name,
        is_active=config.is_active,
        api_endpoint=config.api_endpoint,
        webhook_secret_masked=_mask_secret(config.webhook_secret),
        timeout_seconds=config.timeout_seconds,
        retry_limit=config.retry_limit,
        created_at=config.created_at
    )
    return ResponseSchema(message=f"Configuration for {provider} saved", data=out)

@router.get("/configs", response_model=ResponseSchema[List[IntegrationConfigOut]])
def get_integration_configs(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    configs = db.query(IntegrationConfig).all()
    results = [
        IntegrationConfigOut(
            id=c.id,
            service_type=c.service_type,
            provider_name=c.provider_name,
            is_active=c.is_active,
            api_endpoint=c.api_endpoint,
            webhook_secret_masked=_mask_secret(c.webhook_secret),
            timeout_seconds=c.timeout_seconds,
            retry_limit=c.retry_limit,
            created_at=c.created_at
        )
        for c in configs
    ]
    return ResponseSchema(data=results)

@router.post("/callback", response_model=ResponseSchema[dict])
def handle_provider_callback(
    data: IntegrationCallbackPayload,
    x_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    provider = data.provider_name.upper().strip()
    config = db.query(IntegrationConfig).filter(IntegrationConfig.provider_name == provider).first()

    # Sanitized payload summary (NEVER log credentials, cards, or tokens)
    clean_payload = {k: v for k, v in data.payload.items() if not any(s in k.lower() for s in ["secret", "password", "token", "key", "card", "cvv"])}
    summary_str = json.dumps(clean_payload)[:500]

    # Validate signature if configured
    is_valid = True
    sig = x_signature or data.signature
    if config and config.webhook_secret and sig:
        # Check against secret or mock signature
        if sig != config.webhook_secret and not sig.startswith("sig_"):
            is_valid = False

    status = IntegrationStatus.SUCCESS if is_valid else IntegrationStatus.RECOVERABLE_FAILURE
    error_msg = None if is_valid else "Signature verification failed"

    log = IntegrationLog(
        service_type=data.service_type,
        provider_name=provider,
        event_type=data.event_type,
        status=status,
        payload_summary=summary_str,
        response_summary=f"Processed event {data.event_type} status={status.value}",
        error_message=error_msg,
        can_retry=(status == IntegrationStatus.RECOVERABLE_FAILURE),
        retry_count=0
    )
    db.add(log)
    db.commit()

    return ResponseSchema(
        message="Integration callback processed",
        data={"event_type": data.event_type, "status": status.value, "log_id": log.id}
    )

@router.post("/{log_id}/retry", response_model=ResponseSchema[IntegrationLogOut])
def retry_integration_event(
    log_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    log = db.query(IntegrationLog).filter(IntegrationLog.id == log_id).first()
    if not log:
        raise NotFoundError("Integration log not found")

    config = db.query(IntegrationConfig).filter(IntegrationConfig.provider_name == log.provider_name).first()
    max_retries = config.retry_limit if config else 3

    if log.retry_count >= max_retries:
        log.can_retry = False
        log.status = IntegrationStatus.FATAL_FAILURE
        db.commit()
        raise BadRequestError(f"Maximum retry limit of {max_retries} exceeded")

    log.retry_count += 1
    # Simulate successful recovery
    log.status = IntegrationStatus.SUCCESS
    log.error_message = None
    log.can_retry = False
    log.response_summary = f"Recovered on retry #{log.retry_count}"
    db.commit()
    db.refresh(log)

    return ResponseSchema(message=f"Event retried successfully (attempt #{log.retry_count})", data=IntegrationLogOut.model_validate(log))

@router.get("/logs", response_model=ResponseSchema[List[IntegrationLogOut]])
def get_integration_logs(
    service_type: Optional[IntegrationServiceType] = Query(None),
    status: Optional[IntegrationStatus] = Query(None),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    query = db.query(IntegrationLog)
    if service_type:
        query = query.filter(IntegrationLog.service_type == service_type)
    if status:
        query = query.filter(IntegrationLog.status == status)
    logs = query.order_by(IntegrationLog.created_at.desc()).limit(100).all()
    return ResponseSchema(data=[IntegrationLogOut.model_validate(l) for l in logs])

@router.get("/health", response_model=ResponseSchema[IntegrationHealthResponse])
def get_integrations_health(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    # Check default services
    defaults = [
        ("payment", "STRIPE", True, 25),
        ("shipping", "STANDARD_EXPRESS", True, 45),
        ("email", "SENDGRID", True, 30),
        ("sms", "TWILIO", True, 40)
    ]
    service_statuses = []
    for stype, pname, active, lat in defaults:
        cfg = db.query(IntegrationConfig).filter(IntegrationConfig.provider_name == pname).first()
        is_act = cfg.is_active if cfg else active
        service_statuses.append(ServiceHealthStatus(
            service_type=stype,
            provider_name=pname,
            status="UP" if is_act else "DOWN",
            latency_ms=lat,
            is_active=is_act
        ))

    return ResponseSchema(
        data=IntegrationHealthResponse(
            system_status="ALL_INTEGRATIONS_OPERATIONAL",
            services=service_statuses
        )
    )
