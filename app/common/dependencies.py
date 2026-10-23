from typing import Optional, List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.users import User, RevokedToken
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.common.enums import UserRole, UserStatus
from app.common.pagination import PaginationParams

security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise UnauthorizedError("Authentication credentials were not provided")
    
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired authentication token")
    
    # Check if token is revoked
    revoked = db.query(RevokedToken).filter(RevokedToken.token == token).first()
    if revoked:
        raise UnauthorizedError("Token has been revoked. Please log in again.")
    
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token subject")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise UnauthorizedError("User does not exist")
    
    if user.status == UserStatus.SUSPENDED:
        raise ForbiddenError("User account has been suspended")
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.status != UserStatus.ACTIVE:
        raise ForbiddenError("Inactive user account")
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    try:
        token = credentials.credentials
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        revoked = db.query(RevokedToken).filter(RevokedToken.token == token).first()
        if revoked:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user if user and user.status == UserStatus.ACTIVE else None
    except Exception:
        return None


def require_roles(*allowed_roles: UserRole) -> Callable:
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user
        if current_user.role not in allowed_roles:
            raise ForbiddenError(f"Access denied. Required roles: {[r.value for r in allowed_roles]}")
        return current_user
    return role_checker
