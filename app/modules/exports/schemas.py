from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class BackgroundTaskLogOut(BaseModel):
    id: int
    task_name: str
    status: str
    execution_time_ms: Optional[int] = None
    error_details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TriggerTaskRequest(BaseModel):
    task_name: str  # "low_stock_scan", "process_notifications", "sales_summary"
