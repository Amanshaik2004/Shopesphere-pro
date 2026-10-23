import time
from sqlalchemy.orm import Session
from app.models.system import BackgroundTaskLog
from app.models.inventory import InventoryItem, StockAlert
from app.core.logging import logger

def check_low_stock_thresholds(db: Session):
    start = time.time()
    try:
        items = db.query(InventoryItem).all()
        created_alerts = 0
        for item in items:
            if item.available_quantity <= item.low_stock_threshold:
                # check existing unresolved alert
                existing = db.query(StockAlert).filter(
                    StockAlert.inventory_item_id == item.id,
                    StockAlert.is_resolved == False
                ).first()
                if not existing:
                    alert = StockAlert(
                        inventory_item_id=item.id,
                        product_id=item.product_id,
                        warehouse_id=item.warehouse_id,
                        threshold=item.low_stock_threshold,
                        current_stock=item.available_quantity,
                        is_resolved=False
                    )
                    db.add(alert)
                    created_alerts += 1
        db.commit()
        duration = int((time.time() - start) * 1000)
        task_log = BackgroundTaskLog(task_name="check_low_stock_thresholds", status="SUCCESS", execution_time_ms=duration)
        db.add(task_log)
        db.commit()
        return {"created_alerts": created_alerts, "duration_ms": duration}
    except Exception as e:
        db.rollback()
        task_log = BackgroundTaskLog(task_name="check_low_stock_thresholds", status="FAILED", error_details=str(e))
        db.add(task_log)
        db.commit()
        raise e
