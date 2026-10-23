from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.engagement import NotificationDeliveryLog
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, NotificationChannel, NotificationStatus
from app.integrations.email.provider import email_provider
from app.integrations.sms.provider import sms_provider
from app.tasks.retry_tasks import retry_failed_notifications
from app.modules.messaging.schemas import SendMessageRequest, DeliveryLogOut

router = APIRouter(prefix="/messaging", tags=["Module 42: Email & SMS Notifications"])

@router.post("/send", response_model=ResponseSchema[DeliveryLogOut])
def send_external_message(
    data: SendMessageRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    success = False
    error_msg = None
    if data.channel == NotificationChannel.EMAIL:
        success = email_provider.send_email(data.recipient, data.subject or "ShopSphere Notification", data.content)
    elif data.channel == NotificationChannel.SMS:
        success = sms_provider.send_sms(data.recipient, data.content)

    status = NotificationStatus.SENT if success else NotificationStatus.FAILED
    sent_at = datetime.now(timezone.utc) if success else None

    log = NotificationDeliveryLog(
        channel=data.channel,
        recipient=data.recipient,
        status=status,
        sent_at=sent_at,
        error_message=error_msg
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return ResponseSchema(message=f"Message {status.value}", data=DeliveryLogOut.model_validate(log))

@router.get("/logs", response_model=ResponseSchema[List[DeliveryLogOut]])
def get_messaging_logs(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    logs = db.query(NotificationDeliveryLog).order_by(NotificationDeliveryLog.created_at.desc()).limit(100).all()
    return ResponseSchema(data=[DeliveryLogOut.model_validate(l) for l in logs])

@router.post("/retry-failed", response_model=ResponseSchema[dict])
def retry_failed(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    res = retry_failed_notifications(db)
    return ResponseSchema(message="Retry task executed", data=res)
