import json
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.system import AuditLog
from app.common.enums import AuditAction

def log_audit(
    db: Session,
    action: AuditAction,
    entity_type: str,
    entity_id: Optional[str] = None,
    user_id: Optional[int] = None,
    old_values: Optional[Any] = None,
    new_values: Optional[Any] = None,
    ip_address: Optional[str] = None,
):
    try:
        old_str = json.dumps(old_values, default=str) if old_values is not None else None
        new_str = json.dumps(new_values, default=str) if new_values is not None else None
        audit = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_values=old_str,
            new_values=new_str,
            ip_address=ip_address
        )
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()
