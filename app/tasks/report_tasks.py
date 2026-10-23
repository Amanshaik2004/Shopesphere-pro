import time
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.system import BackgroundTaskLog
from app.models.orders import Order
from app.core.logging import logger

def generate_daily_sales_summary(db: Session):
    start = time.time()
    try:
        total_orders = db.query(func.count(Order.id)).scalar() or 0
        total_revenue = db.query(func.sum(Order.total_amount)).scalar() or 0.0
        duration = int((time.time() - start) * 1000)
        task_log = BackgroundTaskLog(task_name="generate_daily_sales_summary", status="SUCCESS", execution_time_ms=duration)
        db.add(task_log)
        db.commit()
        return {"total_orders": total_orders, "total_revenue": float(total_revenue), "duration_ms": duration}
    except Exception as e:
        db.rollback()
        task_log = BackgroundTaskLog(task_name="generate_daily_sales_summary", status="FAILED", error_details=str(e))
        db.add(task_log)
        db.commit()
        raise e
