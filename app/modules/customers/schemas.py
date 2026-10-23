from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class CustomerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    phone_number: Optional[str] = None

class CustomerRegisterResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone_number: Optional[str] = None
    email_verified: bool
    status: str

    class Config:
        from_attributes = True

class VerifyEmailRequest(BaseModel):
    token_or_email: str
