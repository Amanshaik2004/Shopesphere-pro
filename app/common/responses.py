from typing import Generic, Optional, TypeVar, Any
from pydantic import BaseModel

T = TypeVar("T")

class ResponseSchema(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation successful"
    data: Optional[T] = None
    error_code: Optional[str] = None

class MessageResponse(BaseModel):
    success: bool = True
    message: str
