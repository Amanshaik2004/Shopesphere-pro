from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.engagement import Notification
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole
from app.core.exceptions import NotFoundError, ForbiddenError
from app.modules.notifications.schemas import NotificationCreate, NotificationOut

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
