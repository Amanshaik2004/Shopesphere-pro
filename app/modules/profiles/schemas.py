from typing import Optional, Dict, Any
from pydantic import BaseModel

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class ProfileOut(BaseModel):
    id: int
    user_id: int
    email: str
    full_name: str
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    deactivation_requested: bool

    class Config:
        from_attributes = True
