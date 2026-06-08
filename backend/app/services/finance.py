from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import Invoice, Payment, Project
from app.models.enums import BALANCE_PARTIAL, BALANCE_SETTLED, BALANCE_WAITING, PROJECT_APPROVED, PROJECT_ACTIVE, PROJECT_CLOSED


def calculate_receivable(db: Session, project_id: int) -> dict:
    project = db.query(Project).filter(Project.id == project_id).first()
    invoiced = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.project_id == project_id).scalar() or Decimal("0")
    paid = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.project_id == project_id).scalar() or Decimal("0")
    receivable = invoiced - paid
    if paid >= project.amount and project.amount > 0:
        balance = BALANCE_SETTLED
    elif paid > 0:
        balance = BALANCE_PARTIAL
    else:
        balance = BALANCE_WAITING
    project.balance_status = balance
    return {"invoiced_amount": float(invoiced), "paid_amount": float(paid), "receivable": float(receivable), "balance_status": balance}


def validate_invoice_amount(db: Session, project_id: int, amount: Decimal) -> Project:
    project = db.query(Project).filter(Project.id == project_id).with_for_update().first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status == PROJECT_CLOSED:
        raise HTTPException(status_code=400, detail="已结项项目不可开票")
    if project.status not in {PROJECT_APPROVED, PROJECT_ACTIVE}:
        raise HTTPException(status_code=400, detail="仅已立项或进行中项目允许开票")
    invoiced = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.project_id == project_id).scalar() or Decimal("0")
    if project.amount > 0 and invoiced + amount > project.amount:
        raise HTTPException(status_code=400, detail="开票金额超过合同金额")
    return project


def validate_payment_amount(db: Session, project_id: int, invoice_id: int, amount: Decimal) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.project_id == project_id).with_for_update().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="关联发票不存在")
    paid = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.invoice_id == invoice_id).scalar() or Decimal("0")
    if paid + amount > invoice.amount:
        raise HTTPException(status_code=400, detail="回款金额超过关联发票金额")
    return invoice
