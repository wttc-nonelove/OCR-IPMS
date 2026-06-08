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
            "invoice_no": i.invoice_no,
            "amount": float(i.amount),
            "amount_without_tax": float(i.amount_without_tax),
            "tax_rate": float(i.tax_rate),
            "tax_amount": float(i.tax_amount),
            "invoice_date": i.invoice_date.isoformat(),
            "invoice_type": i.invoice_type,
            "buyer": i.buyer,
            "seller": i.seller,
            "create_time": i.create_time.isoformat() if i.create_time else None,
        }
        for i in query.order_by(Invoice.create_time.desc()).offset(pg.offset).limit(pg.limit).all()
    ]
    return paginated(items, total, pg.page, pg.page_size)


@router.post("/create")
async def create_invoice(
    project_id: int = Form(...),
    invoice_no: str = Form(...),
    amount: Decimal = Form(...),
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
    # 自动计算不含税金额和税额
    if amount_without_tax is not None and amount_without_tax > 0:
        # 用户提供了不含税金额
        if tax_amount is None:
            tax_amount = amount - amount_without_tax
    elif tax_amount is not None and tax_amount > 0:
        # 用户提供了税额，反算不含税金额
        amount_without_tax = amount - tax_amount
    else:
        # 都没提供，默认不含税金额 = 价税合计（兼容旧逻辑）
        amount_without_tax = amount
        tax_amount = Decimal("0")

    if tax_rate is None and amount_without_tax > 0:
        tax_rate = (tax_amount / amount_without_tax * 100).quantize(Decimal("0.01"))

    # 用不含税金额校验
    project = validate_invoice_amount(db, project_id, amount_without_tax)
    path = await save_upload(invoice_file, "invoices")
    if path:
        recognize_file(db, path, "invoice")
    invoice = Invoice(
        project_id=project_id, invoice_no=invoice_no,
        amount=amount, amount_without_tax=amount_without_tax,
        tax_rate=tax_rate or Decimal("0"), tax_amount=tax_amount,
        invoice_date=invoice_date, invoice_type=invoice_type,
        buyer=buyer, seller=seller, file_path=path, create_by=user.id,
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
