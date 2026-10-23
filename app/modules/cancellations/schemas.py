from pydantic import BaseModel

class CancellationRequest(BaseModel):
    order_id: int
    reason: str

class CancellationOut(BaseModel):
    id: int
    order_id: int
    reason: str
    is_approved: bool
    refund_initiated: bool

    class Config:
        from_attributes = True
