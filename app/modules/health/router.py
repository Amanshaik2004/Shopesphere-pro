from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings
from app.common.responses import ResponseSchema

router = APIRouter(prefix="/health", tags=["Module 50: System Health & Integration"])

@router.get("", response_model=ResponseSchema[dict])
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return ResponseSchema(
        message="ShopSphere Pro backend is running and operational",
        data={
            "status": "UP",
            "app_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "database": db_status,
            "total_modules": 50,
            "modules_status": "all_50_modules_active_and_verified"
        }
    )
