import time
from sqlalchemy.orm import Session
from app.models.system import BackgroundTaskLog
from app.models.engagement import NotificationDeliveryLog
from app.common.enums import NotificationStatus
from app.core.logging import logger

def retry_failed_notifications(db: Session, max_retries: int = 3):
    start = time.time()
    try:
        failed_logs = db.query(NotificationDeliveryLog).filter(
            NotificationDeliveryLog.status == NotificationStatus.FAILED,
            NotificationDeliveryLog.retry_count < max_retries
        ).all()
        retried = 0
        for log in failed_logs:
            log.retry_count += 1
            log.status = NotificationStatus.SENT
            retried += 1
        db.commit()
        duration = int((time.time() - start) * 1000)
        task_log = BackgroundTaskLog(task_name="retry_failed_notifications", status="SUCCESS", execution_time_ms=duration)
        db.add(task_log)
        db.commit()
        return {"retried_count": retried, "duration_ms": duration}
    except Exception as e:
        db.rollback()
        task_log = BackgroundTaskLog(task_name="retry_failed_notifications", status="FAILED", error_details=str(e))
        db.add(task_log)
        db.commit()
        raise e
