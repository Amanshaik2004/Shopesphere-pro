import io
import csv
from typing import List
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from app.db.session import get_db
from app.models.orders import Order
from app.models.system import BackgroundTaskLog
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole
from app.core.exceptions import BadRequestError
from app.tasks.inventory_tasks import check_low_stock_thresholds
from app.tasks.notification_tasks import process_pending_notifications
from app.tasks.report_tasks import generate_daily_sales_summary
from app.modules.exports.schemas import BackgroundTaskLogOut, TriggerTaskRequest

router = APIRouter(prefix="/exports", tags=["Module 49: Report Export & Background Tasks"])

@router.get("/orders/csv")
def export_orders_csv(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order Number", "User ID", "Subtotal", "Discount", "Tax", "Shipping", "Total", "Status", "Date"])

    for o in orders:
        writer.writerow([
            o.order_number, o.user_id, o.subtotal_amount, o.discount_amount,
            o.tax_amount, o.shipping_amount, o.total_amount, o.status.value, o.created_at.isoformat()
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders_export.csv"}
    )

@router.get("/orders/excel")
def export_orders_excel(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append(["Order Number", "User ID", "Subtotal", "Discount", "Tax", "Shipping", "Total", "Status", "Date"])

    for o in orders:
        ws.append([
            o.order_number, o.user_id, float(o.subtotal_amount), float(o.discount_amount),
            float(o.tax_amount), float(o.shipping_amount), float(o.total_amount), o.status.value, str(o.created_at)
        ])

    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=orders_export.xlsx"}
    )

@router.get("/orders/pdf")
def export_orders_pdf(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).order_by(Order.created_at.desc()).limit(50).all()
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, "ShopSphere Pro - Orders Summary Report")
    p.setFont("Helvetica", 10)
    p.drawString(50, 735, f"Exported by {current_user.full_name}")

    y = 700
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, y, "Order Number")
    p.drawString(200, y, "Total ($)")
    p.drawString(280, y, "Status")
    p.drawString(400, y, "Date")
    p.line(50, y - 5, 550, y - 5)

    y -= 20
    p.setFont("Helvetica", 8)
    for o in orders:
        if y < 50:
            p.showPage()
            y = 750
        p.drawString(50, y, o.order_number)
        p.drawString(200, y, f"${o.total_amount:.2f}")
        p.drawString(280, y, o.status.value)
        p.drawString(400, y, o.created_at.strftime("%Y-%m-%d %H:%M"))
        y -= 15

    p.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=orders_summary.pdf"}
    )

@router.post("/trigger-task", response_model=ResponseSchema[dict])
def trigger_background_task(
    req: TriggerTaskRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    if req.task_name == "low_stock_scan":
        result = check_low_stock_thresholds(db)
    elif req.task_name == "process_notifications":
        result = process_pending_notifications(db)
    elif req.task_name == "sales_summary":
        result = generate_daily_sales_summary(db)
    else:
        raise BadRequestError(f"Unknown task name: {req.task_name}")

    return ResponseSchema(message=f"Task '{req.task_name}' executed successfully", data=result)

@router.get("/task-logs", response_model=ResponseSchema[List[BackgroundTaskLogOut]])
def get_task_logs(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    logs = db.query(BackgroundTaskLog).order_by(BackgroundTaskLog.created_at.desc()).limit(50).all()
    return ResponseSchema(data=[BackgroundTaskLogOut.model_validate(l) for l in logs])
