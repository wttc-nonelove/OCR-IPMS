from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_pagination, require_roles
from app.db.session import get_db
from app.models.entities import Invoice, Payment, User
from app.models.enums import ADMIN, FINANCE, PM
from app.schemas.common import ok, paginated
from app.services.audit import log_action
from app.services.files import save_upload
from app.services.finance import calculate_receivable, validate_payment_amount

router = APIRouter(prefix="/payment", tags=["payment"])


@router.get("/list")
def list_payments(
    project_id: int | None = None,
    pg: Pagination = Depends(get_pagination),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(FINANCE, ADMIN, PM)),
):
    query = db.query(Payment)
    if project_id:
        query = query.filter(Payment.project_id == project_id)
    total = query.count()
    items = [
        {
            "id": p.id,
            "project_id": p.project_id,
            "invoice_id": p.invoice_id,
            "invoice_no": p.invoice.invoice_no if p.invoice else None,
            "invoice_label": p.invoice.invoice_no if p.invoice else "未关联发票",
            "amount": float(p.amount),
            "payment_date": p.payment_date.isoformat(),
            "payment_method": p.payment_method,
            "remark": p.remark,
            "voucher_file": p.voucher_file,
            "create_time": p.create_time.isoformat() if p.create_time else None,
        }
        for p in query.order_by(Payment.create_time.desc()).offset(pg.offset).limit(pg.limit).all()
    ]
    return paginated(items, total, pg.page, pg.page_size)


@router.post("/create")
async def create_payment(
    project_id: int = Form(...),
    invoice_id: int | None = Form(None),
    amount: Decimal = Form(...),
    payment_date: date = Form(...),
    payment_method: str = Form("bank"),
    remark: str | None = Form(None),
    voucher_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(FINANCE)),
):
    if invoice_id:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="关联发票不存在")
        if invoice.project_id != project_id:
            raise HTTPException(status_code=400, detail="关联发票不属于当前项目")
    validate_payment_amount(db, project_id, amount)
    path = await save_upload(voucher_file, "payments")
    payment = Payment(project_id=project_id, invoice_id=invoice_id, amount=amount, payment_date=payment_date, payment_method=payment_method, voucher_file=path, remark=remark, create_by=user.id)
    db.add(payment)
    db.flush()
    data = calculate_receivable(db, project_id)
    log_action(db, user, "payment_create", f"project:{project_id} invoice:{invoice_id or 'none'} amount:{amount}")
    db.commit()
    return ok({"id": payment.id, "receivable": data}, "回款登记成功")


@router.delete("/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(FINANCE))):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="回款记录不存在")
    project_id = payment.project_id
    summary = f"project:{payment.project_id} invoice:{payment.invoice_id} amount:{payment.amount}"
    db.delete(payment)
    data = calculate_receivable(db, project_id)
    log_action(db, user, "payment_delete", summary)
    db.commit()
    return ok({"receivable": data}, "回款已删除")
