from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Invoice, Payment, Project, User
from app.schemas.common import ok
from app.services.finance import calculate_receivable

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/summary")
def finance_summary(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return ok(None, "项目不存在")
    receivable = calculate_receivable(db, project_id)
    contract_amount = float(project.amount or 0)
    invoiced = receivable["invoiced_amount"]
    paid = receivable["paid_amount"]
    remaining_invoice = max(contract_amount - invoiced, 0) if contract_amount > 0 else 0
    invoice_progress = round(invoiced / contract_amount * 100, 2) if contract_amount > 0 else 0
    payment_progress = round(paid / invoiced * 100, 2) if invoiced > 0 else 0
    invoices = db.query(Invoice).filter(Invoice.project_id == project_id).order_by(Invoice.create_time.desc()).all()
    payments = db.query(Payment).filter(Payment.project_id == project_id).order_by(Payment.create_time.desc()).all()
    return ok(
        {
            "project_id": project.id,
            "project_no": project.project_no,
            "project_name": project.name,
            "contract_amount": contract_amount,
            "invoiced_amount": invoiced,
            "paid_amount": paid,
            "receivable": receivable["receivable"],
            "remaining_invoice_amount": remaining_invoice,
            "invoice_progress": invoice_progress,
            "payment_progress": payment_progress,
            "balance_status": receivable["balance_status"],
            "invoices": [
                {"id": i.id, "invoice_no": i.invoice_no, "amount": float(i.amount), "invoice_date": i.invoice_date.isoformat(), "invoice_type": i.invoice_type}
                for i in invoices
            ],
            "payments": [
                {"id": p.id, "invoice_id": p.invoice_id, "amount": float(p.amount), "payment_date": p.payment_date.isoformat(), "payment_method": p.payment_method}
                for p in payments
            ],
        }
    )
