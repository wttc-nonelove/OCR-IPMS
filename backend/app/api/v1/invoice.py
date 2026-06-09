from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_pagination, require_roles
from app.db.session import get_db
from app.models.entities import Invoice, User
from app.models.enums import ADMIN, FINANCE
from app.schemas.common import ok, paginated
from app.services.audit import log_action
from app.services.approval import create_approval_instance
from app.services.files import save_upload
from app.services.finance import calculate_receivable, validate_invoice_amount
from app.services.ocr import recognize_file

router = APIRouter(prefix="/invoice", tags=["invoice"])


def _normalize_invoice_amounts(
    amount: Decimal | None,
    amount_without_tax: Decimal | None,
    tax_rate: Decimal | None,
    tax_amount: Decimal | None,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    amount = amount.quantize(Decimal("0.01")) if amount is not None else None
    amount_without_tax = amount_without_tax.quantize(Decimal("0.01")) if amount_without_tax is not None else None
    tax_rate = tax_rate.quantize(Decimal("0.01")) if tax_rate is not None else None
    tax_amount = tax_amount.quantize(Decimal("0.01")) if tax_amount is not None else None

    if amount_without_tax is not None and amount_without_tax > 0:
        if tax_amount is None:
            if tax_rate is not None and tax_rate > 0:
                tax_amount = (amount_without_tax * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
                amount = (amount_without_tax + tax_amount).quantize(Decimal("0.01"))
            else:
                tax_amount = ((amount or amount_without_tax) - amount_without_tax).quantize(Decimal("0.01"))
    elif tax_amount is not None and tax_amount > 0:
        if amount is None:
            raise HTTPException(status_code=400, detail="请填写价税合计或不含税金额")
        amount_without_tax = (amount - tax_amount).quantize(Decimal("0.01"))
    else:
        if amount is None:
            raise HTTPException(status_code=400, detail="请填写发票金额")
        amount_without_tax = amount
        tax_amount = Decimal("0.00")

    if tax_amount is None:
        tax_amount = Decimal("0.00")
    if tax_rate is None and amount_without_tax > 0:
        tax_rate = (tax_amount / amount_without_tax * Decimal("100")).quantize(Decimal("0.01"))
    if tax_rate is None:
        tax_rate = Decimal("0.00")
    if (amount is None or amount <= 0) and amount_without_tax > 0:
        amount = (amount_without_tax + tax_amount).quantize(Decimal("0.01"))
    return amount, amount_without_tax, tax_rate, tax_amount


@router.get("/list")
def list_invoices(
    project_id: int | None = None,
    pg: Pagination = Depends(get_pagination),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(FINANCE, ADMIN)),
):
    query = db.query(Invoice)
    if project_id:
        query = query.filter(Invoice.project_id == project_id)
    total = query.count()
    items = [
        {
            "id": i.id,
            "project_id": i.project_id,
            "project_no": i.project.project_no if i.project else None,
            "project_name": i.project.name if i.project else None,
            "invoice_no": i.invoice_no,
            "amount": float(i.amount or 0),
            "amount_without_tax": float(i.amount_without_tax or 0),
            "tax_rate": float(i.tax_rate or 0),
            "tax_amount": float(i.tax_amount or 0),
            "invoice_date": i.invoice_date.isoformat(),
            "invoice_type": i.invoice_type,
            "buyer": i.buyer,
            "seller": i.seller,
            "file_path": i.file_path,
            "create_time": i.create_time.isoformat() if i.create_time else None,
        }
        for i in query.order_by(Invoice.create_time.desc()).offset(pg.offset).limit(pg.limit).all()
    ]
    return paginated(items, total, pg.page, pg.page_size)


@router.post("/create")
async def create_invoice(
    project_id: int = Form(...),
    invoice_no: str = Form(...),
    amount: Decimal | None = Form(None),
    amount_without_tax: Decimal | None = Form(None),
    tax_rate: Decimal | None = Form(None),
    tax_amount: Decimal | None = Form(None),
    invoice_date: date = Form(...),
    invoice_type: str = Form("special"),
    buyer: str | None = Form(None),
    seller: str | None = Form(None),
    invoice_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(FINANCE)),
):
    amount, amount_without_tax, tax_rate, tax_amount = _normalize_invoice_amounts(amount, amount_without_tax, tax_rate, tax_amount)
    project = validate_invoice_amount(db, project_id, amount_without_tax)
    path = await save_upload(invoice_file, "invoices")
    if path:
        recognize_file(db, path, "invoice")
    invoice = Invoice(
        project_id=project_id,
        invoice_no=invoice_no,
        amount=amount,
        amount_without_tax=amount_without_tax,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        invoice_date=invoice_date,
        invoice_type=invoice_type,
        buyer=buyer,
        seller=seller,
        file_path=path,
        create_by=user.id,
    )
    db.add(invoice)
    try:
        if project.amount > 0 and amount_without_tax >= project.amount * Decimal("0.8"):
            create_approval_instance(db, "invoice", project_id, user.id)
        log_action(db, user, "invoice_create", f"{invoice_no} project:{project_id} amount:{amount} without_tax:{amount_without_tax}")
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
