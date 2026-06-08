from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.entities import Invoice, User
from app.models.enums import ADMIN, FINANCE
from app.schemas.common import ok
from app.services.audit import log_action
from app.services.approval import create_approval_instance
from app.services.files import save_upload
from app.services.finance import calculate_receivable, validate_invoice_amount
from app.services.ocr import recognize_file

router = APIRouter(prefix="/invoice", tags=["invoice"])


@router.get("/list")
def list_invoices(project_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(FINANCE, ADMIN))):
    query = db.query(Invoice)
    if project_id:
        query = query.filter(Invoice.project_id == project_id)
    return ok([
        {
            "id": i.id,
            "project_id": i.project_id,
            "invoice_no": i.invoice_no,
            "amount": float(i.amount),
            "invoice_date": i.invoice_date.isoformat(),
            "invoice_type": i.invoice_type,
            "buyer": i.buyer,
            "seller": i.seller,
            "create_time": i.create_time.isoformat() if i.create_time else None,
        }
        for i in query.order_by(Invoice.create_time.desc()).all()
    ])


@router.post("/create")
async def create_invoice(
    project_id: int = Form(...),
    invoice_no: str = Form(...),
    amount: Decimal = Form(...),
    invoice_date: date = Form(...),
    invoice_type: str = Form("special"),
    buyer: str | None = Form(None),
    seller: str | None = Form(None),
    invoice_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(FINANCE)),
):
    project = validate_invoice_amount(db, project_id, amount)
    path = await save_upload(invoice_file, "invoices")
    if path:
        recognize_file(db, path, "invoice")
    invoice = Invoice(project_id=project_id, invoice_no=invoice_no, amount=amount, invoice_date=invoice_date, invoice_type=invoice_type, buyer=buyer, seller=seller, file_path=path, create_by=user.id)
    db.add(invoice)
    try:
        if project.amount > 0 and amount >= project.amount * Decimal("0.8"):
            create_approval_instance(db, "invoice", project_id, user.id)
        log_action(db, user, "invoice_create", f"{invoice_no} project:{project_id} amount:{amount}")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="发票号码已存在") from exc
    return ok({"id": invoice.id}, "开票登记成功")


@router.get("/receivable")
def receivable(project_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(FINANCE, ADMIN))):
    data = calculate_receivable(db, project_id)
    db.commit()
    return ok(data)
