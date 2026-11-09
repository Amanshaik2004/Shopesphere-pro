from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.engagement import (
    Notification, NotificationDeliveryLog, CustomerNotificationPreference
)
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, NotificationChannel, NotificationStatus
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.modules.notifications.schemas import (
    NotificationCreate, NotificationOut, NotificationPreferenceOut,
    NotificationPreferencesUpdate, NotificationDispatchResponse
)
from app.modules.messaging.schemas import DeliveryLogOut

router = APIRouter(prefix="/notifications", tags=["Module 41: Notification Management"])

@router.post("", response_model=ResponseSchema[NotificationOut])
def send_notification(
    data: NotificationCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    notif = Notification(**data.model_dump())
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return ResponseSchema(message="Notification dispatched", data=NotificationOut.model_validate(notif))

@router.get("", response_model=ResponseSchema[List[NotificationOut]])
def get_my_notifications(
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    notifications = query.order_by(Notification.created_at.desc()).limit(100).all()
    return ResponseSchema(data=[NotificationOut.model_validate(n) for n in notifications])

@router.put("/{notification_id}/read", response_model=ResponseSchema[NotificationOut])
def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise NotFoundError("Notification not found")
    if notif.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return ResponseSchema(message="Marked as read", data=NotificationOut.model_validate(notif))

@router.put("/read-all", response_model=ResponseSchema[MessageResponse])
def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return ResponseSchema(message="All notifications marked as read", data=MessageResponse(message="Updated"))


# =========================================================================
# Phase 2: Notification Preferences & Deduplicated Dispatch
# =========================================================================

@router.get("/preferences", response_model=ResponseSchema[List[NotificationPreferenceOut]])
def get_my_notification_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    prefs = db.query(CustomerNotificationPreference).filter(CustomerNotificationPreference.user_id == current_user.id).all()
    return ResponseSchema(data=[NotificationPreferenceOut.model_validate(p) for p in prefs])

@router.put("/preferences", response_model=ResponseSchema[List[NotificationPreferenceOut]])
def update_my_notification_preferences(
    data: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    saved_prefs = []
    for item in data.preferences:
        pref = db.query(CustomerNotificationPreference).filter(
            CustomerNotificationPreference.user_id == current_user.id,
            CustomerNotificationPreference.channel == item.channel,
            CustomerNotificationPreference.event_type == item.event_type
        ).first()
        if not pref:
            pref = CustomerNotificationPreference(
                user_id=current_user.id,
                channel=item.channel,
                event_type=item.event_type,
                is_enabled=item.is_enabled
            )
            db.add(pref)
        else:
            pref.is_enabled = item.is_enabled
        saved_prefs.append(pref)

    db.commit()
    for p in saved_prefs:
        db.refresh(p)
    return ResponseSchema(message="Preferences updated", data=[NotificationPreferenceOut.model_validate(p) for p in saved_prefs])

@router.post("/dispatch", response_model=ResponseSchema[NotificationDispatchResponse])
def dispatch_notification_with_controls(
    data: NotificationCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    # 1. Deduplication Check
    if data.deduplication_key:
        existing = db.query(Notification).filter(Notification.deduplication_key == data.deduplication_key).first()
        if existing:
            return ResponseSchema(
                message="Notification skipped: Duplicate key already processed",
                data=NotificationDispatchResponse(
                    notification_id=existing.id,
                    channel=existing.channel.value,
                    is_duplicate=True,
                    delivery_status="SKIPPED_DUPLICATE",
                    message="Duplicate notification prevented"
                )
            )

    # 2. Check Customer Channel Preference
    pref = db.query(CustomerNotificationPreference).filter(
        CustomerNotificationPreference.user_id == data.user_id,
        CustomerNotificationPreference.channel == data.channel,
        CustomerNotificationPreference.event_type == data.notification_type
    ).first()
    if pref and not pref.is_enabled:
        return ResponseSchema(
            message="Notification skipped: Customer opted out of this channel/event",
            data=NotificationDispatchResponse(
                channel=data.channel.value,
                is_duplicate=False,
                delivery_status="SKIPPED_OPT_OUT",
                message="Customer preferences suppress this notification"
            )
        )

    # 3. Create Notification Record
    notif = Notification(
        user_id=data.user_id,
        title=data.title,
        message=data.message,
        channel=data.channel,
        notification_type=data.notification_type,
        data=data.data,
        deduplication_key=data.deduplication_key
    )
    db.add(notif)
    db.flush()

    # 4. Create Delivery Log Record
    recipient_user = db.query(User).filter(User.id == data.user_id).first()
    recipient_contact = recipient_user.email if data.channel == NotificationChannel.EMAIL else (recipient_user.phone_number or recipient_user.email)

    log = NotificationDeliveryLog(
        notification_id=notif.id,
        channel=data.channel,
        recipient=recipient_contact or f"User #{data.user_id}",
        status=NotificationStatus.DELIVERED if data.channel == NotificationChannel.IN_APP else NotificationStatus.SENT,
        retry_count=0,
        sent_at=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()
    db.refresh(notif)

    return ResponseSchema(
        message="Notification dispatched and delivery logged",
        data=NotificationDispatchResponse(
            notification_id=notif.id,
            channel=data.channel.value,
            is_duplicate=False,
            delivery_status="DELIVERED",
            message="Notification successfully sent"
        )
    )

@router.get("/history", response_model=ResponseSchema[List[DeliveryLogOut]])
def get_notification_history(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    logs = db.query(NotificationDeliveryLog).order_by(NotificationDeliveryLog.created_at.desc()).limit(100).all()
    return ResponseSchema(data=[DeliveryLogOut.model_validate(l) for l in logs])
