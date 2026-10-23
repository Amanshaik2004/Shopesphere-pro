import time
from sqlalchemy.orm import Session
from app.models.system import BackgroundTaskLog
from app.models.engagement import Notification, NotificationDeliveryLog
from app.common.enums import NotificationStatus
from app.core.logging import logger

def process_pending_notifications(db: Session):
    start = time.time()
    try:
        pending = db.query(NotificationDeliveryLog).filter(NotificationDeliveryLog.status == NotificationStatus.PENDING).all()
        count = len(pending)
        for log in pending:
            log.status = NotificationStatus.SENT
        db.commit()
        duration = int((time.time() - start) * 1000)
        task_log = BackgroundTaskLog(task_name="process_pending_notifications", status="SUCCESS", execution_time_ms=duration)
        db.add(task_log)
        db.commit()
        return {"processed": count, "duration_ms": duration}
    except Exception as e:
        db.rollback()
        task_log = BackgroundTaskLog(task_name="process_pending_notifications", status="FAILED", error_details=str(e))
        db.add(task_log)
        db.commit()
        raise e
