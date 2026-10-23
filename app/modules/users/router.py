from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.session import get_db
from app.models.users import User, UserActivity, UserProfile
from app.core.security import hash_password
from app.core.exceptions import NotFoundError, ConflictError, BadRequestError
from app.common.responses import ResponseSchema, MessageResponse
from app.common.pagination import PaginationParams, PaginatedResponse, PaginatedData, paginate_query
from app.common.dependencies import require_roles
from app.common.enums import UserRole, UserStatus, AuditAction
from app.core.audit import log_audit
from app.modules.users.schemas import UserCreate, UserUpdate, UserOut, UserActivityOut

router = APIRouter(prefix="/users", tags=["Module 02: User Management"])

@router.post("", response_model=ResponseSchema[UserOut])
def create_user(
    data: UserCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise ConflictError("User with this email already exists")
    
    new_user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone_number=data.phone_number,
        role=data.role,
        status=data.status,
        email_verified=True
    )
    db.add(new_user)
    db.flush()
    
    profile = UserProfile(user_id=new_user.id)
    db.add(profile)
    db.commit()
    db.refresh(new_user)
    
    log_audit(db, AuditAction.CREATE, "User", entity_id=str(new_user.id), user_id=current_user.id, new_values={"email": new_user.email, "role": new_user.role.value})
    return ResponseSchema(message="User created successfully", data=UserOut.model_validate(new_user))

@router.get("", response_model=PaginatedResponse[UserOut])
def get_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    status: Optional[UserStatus] = Query(None, description="Filter by status"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if search:
        query = query.filter(or_(User.email.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%")))
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    
    paginated = paginate_query(query, pagination)
    return PaginatedResponse(
        message="Users retrieved successfully",
        data=PaginatedData(
            items=[UserOut.model_validate(u) for u in paginated.items],
            total=paginated.total,
            page=paginated.page,
            page_size=paginated.page_size,
            total_pages=paginated.total_pages
        )
    )

@router.get("/{user_id}", response_model=ResponseSchema[UserOut])
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    return ResponseSchema(data=UserOut.model_validate(user))

@router.put("/{user_id}", response_model=ResponseSchema[UserOut])
def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    old_vals = {"full_name": user.full_name, "role": user.role.value, "status": user.status.value}
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone_number is not None:
        user.phone_number = data.phone_number
    if data.role is not None:
        user.role = data.role
    if data.status is not None:
        user.status = data.status
        
    db.commit()
    db.refresh(user)
    log_audit(db, AuditAction.UPDATE, "User", entity_id=str(user.id), user_id=current_user.id, old_values=old_vals, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="User updated successfully", data=UserOut.model_validate(user))

@router.delete("/{user_id}", response_model=ResponseSchema[MessageResponse])
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    if user_id == current_user.id:
        raise BadRequestError("You cannot deactivate your own account via this endpoint")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    user.status = UserStatus.INACTIVE
    db.commit()
    log_audit(db, AuditAction.STATUS_CHANGE, "User", entity_id=str(user.id), user_id=current_user.id, new_values={"status": UserStatus.INACTIVE.value})
    return ResponseSchema(message="User deactivated successfully", data=MessageResponse(message="User status set to inactive"))

@router.get("/{user_id}/activities", response_model=ResponseSchema[List[UserActivityOut]])
def get_user_activities(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    activities = db.query(UserActivity).filter(UserActivity.user_id == user_id).order_by(UserActivity.created_at.desc()).limit(100).all()
    return ResponseSchema(data=[UserActivityOut.model_validate(a) for a in activities])
