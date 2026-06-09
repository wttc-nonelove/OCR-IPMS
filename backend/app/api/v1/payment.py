from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.entities import Payment, User
from app.models.enums import ADMIN, FINANCE
from app.schemas.common import ok
from app.services.audit import log_action
from app.services.files import save_upload
from app.services.finance import calculate_receivable, validate_payment_amount

router = APIRouter(prefix="/payment", tags=["payment"])


@router.get("/list")
def list_payments(project_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(FINANCE, ADMIN))):
    query = db.query(Payment)
    if project_id:
        query = query.filter(Payment.project_id == project_id)
    return ok([
        {
            "id": p.id,
            "project_id": p.project_id,
            "invoice_id": p.invoice_id,
            "invoice_no": p.invoice.invoice_no if p.invoice else None,
            "amount": float(p.amount),
            "payment_date": p.payment_date.isoformat(),
            "payment_method": p.payment_method,
            "remark": p.remark,
            "voucher_file": p.voucher_file,
            "create_time": p.create_time.isoformat() if p.create_time else None,
        }
        for p in query.order_by(Payment.create_time.desc()).all()
    ])


@router.post("/create")
async def create_payment(
    project_id: int = Form(...),
    invoice_id: int = Form(...),
    amount: Decimal = Form(...),
    payment_date: date = Form(...),
    payment_method: str = Form("bank"),
    remark: str | None = Form(None),
    voucher_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(FINANCE)),
):
    validate_payment_amount(db, project_id, invoice_id, amount)
    path = await save_upload(voucher_file, "payments")
    payment = Payment(project_id=project_id, invoice_id=invoice_id, amount=amount, payment_date=payment_date, payment_method=payment_method, voucher_file=path, remark=remark, create_by=user.id)
    db.add(payment)
    db.flush()
    data = calculate_receivable(db, project_id)
    log_action(db, user, "payment_create", f"project:{project_id} invoice:{invoice_id} amount:{amount}")
    db.commit()
    return ok({"id": payment.id, "receivable": data}, "回款登记成功")
