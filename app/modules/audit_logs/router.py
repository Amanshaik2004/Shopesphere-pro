from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.system import AuditLog
from app.models.users import User
from app.common.pagination import PaginationParams, PaginatedResponse, PaginatedData, paginate_query
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.modules.audit_logs.schemas import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["Module 46: Audit Log Management"])

@router.get("", response_model=PaginatedResponse[AuditLogOut])
def get_audit_logs(
    entity_type: Optional[str] = Query(None),
    action: Optional[AuditAction] = Query(None),
    user_id: Optional[int] = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    query = query.order_by(AuditLog.created_at.desc())
    paginated = paginate_query(query, pagination)

    return PaginatedResponse(
        message="Audit logs retrieved",
        data=PaginatedData(
            items=[AuditLogOut.model_validate(a) for a in paginated.items],
            total=paginated.total,
            page=paginated.page,
            page_size=paginated.page_size,
            total_pages=paginated.total_pages
        )
    )
