from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.entities import ApprovalInstance, ApprovalTask, Contract, ContractDiff, Invoice, Payment, Project, ProjectClose, User
from app.models.enums import ADMIN, APPROVAL_PENDING, BUSINESS, PM, PROJECT_ACTIVE, PROJECT_APPROVED, PROJECT_CLOSED, PROJECT_DRAFT, PROJECT_PENDING
from app.schemas.business import ContractDiffConfirmIn, ProjectApproveIn, ProjectOut, ProjectStartIn
from app.schemas.common import ok
from app.services.audit import log_action
from app.services.approval import create_approval_instance
from app.services.approval import process_task
from app.services.files import save_upload
from app.services.finance import calculate_receivable
from app.services.ocr import recognize_file

router = APIRouter(prefix="/project", tags=["project"])


def generate_project_no(db: Session) -> str:
    year = datetime.now().year
    prefix = f"PRJ-{year}-"
    max_no = db.query(func.max(Project.project_no)).filter(Project.project_no.like(f"{prefix}%")).scalar()
    seq = int(max_no.split("-")[2]) + 1 if max_no else 1
    return f"{prefix}{seq:04d}"


@router.get("/next-no")
def next_project_no(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ok({"project_no": generate_project_no(db)})


@router.get("/options")
def project_options(
    usage: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Project)
    if usage == "invoice":
        query = query.filter(Project.status.in_([PROJECT_APPROVED, PROJECT_ACTIVE]))
    elif usage == "close":
        query = query.filter(Project.status.in_([PROJECT_APPROVED, PROJECT_ACTIVE]))
    elif usage == "active":
        query = query.filter(Project.status == PROJECT_ACTIVE)
    projects = query.order_by(Project.create_time.desc()).all()
    return ok([
        {"id": p.id, "project_no": p.project_no, "name": p.name, "customer": p.customer, "amount": float(p.amount), "status": p.status}
        for p in projects
    ])


@router.get("/detail")
def project_detail(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    contracts = db.query(Contract).filter(Contract.project_id == project_id).order_by(Contract.version.desc()).all()
    diffs = db.query(ContractDiff).filter(ContractDiff.project_id == project_id).order_by(ContractDiff.create_time.desc()).all()
    invoices = db.query(Invoice).filter(Invoice.project_id == project_id).order_by(Invoice.create_time.desc()).all()
    payments = db.query(Payment).filter(Payment.project_id == project_id).order_by(Payment.create_time.desc()).all()
    closes = db.query(ProjectClose).filter(ProjectClose.project_id == project_id).order_by(ProjectClose.create_time.desc()).all()
    approvals = db.query(ApprovalInstance).filter(ApprovalInstance.business_id.in_([project_id] + [c.id for c in closes])).order_by(ApprovalInstance.start_time.desc()).all()
    return ok(
        {
            "project": ProjectOut.model_validate(project).model_dump(),
            "contracts": [
                {"id": c.id, "version": c.version, "file_type": c.file_type, "file_name": c.file_name, "upload_time": c.upload_time.isoformat()}
                for c in contracts
            ],
            "diffs": [_diff_out(d) for d in diffs],
            "invoices": [
                {"id": i.id, "invoice_no": i.invoice_no, "amount": float(i.amount), "invoice_date": i.invoice_date.isoformat(), "invoice_type": i.invoice_type}
                for i in invoices
            ],
            "payments": [
                {"id": p.id, "invoice_id": p.invoice_id, "amount": float(p.amount), "payment_date": p.payment_date.isoformat(), "payment_method": p.payment_method}
                for p in payments
            ],
            "closes": [{"id": c.id, "close_time": c.close_time.isoformat(), "status": c.status, "balance_status": c.balance_status} for c in closes],
            "receivable": calculate_receivable(db, project_id),
            "approvals": [
                {"id": a.id, "business_type": a.business_type, "business_id": a.business_id, "status": a.status, "start_time": a.start_time.isoformat()}
                for a in approvals
            ],
        }
    )


@router.get("/list")
def list_projects(
    keyword: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Project)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((Project.name.like(like)) | (Project.project_no.like(like)) | (Project.customer.like(like)))
    if status:
        query = query.filter(Project.status == status)
    projects = query.order_by(Project.create_time.desc()).all()
    return ok([ProjectOut.model_validate(project).model_dump() for project in projects])


@router.post("/create")
async def create_project(
    name: str = Form(...),
    customer: str = Form(...),
    amount: Decimal = Form(...),
    contract_no: str = Form(""),
    sign_date: date | None = Form(None),
    project_type: str = Form("software"),
    pm_id: int | None = Form(None),
    start_date: date | None = Form(None),
    end_date: date | None = Form(None),
    description: str | None = Form(None),
    extra_cost: Decimal = Form(Decimal("0")),
    cost_desc: str | None = Form(None),
    word_contract: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(BUSINESS, ADMIN)),
):
    project = Project(
        project_no=generate_project_no(db),
        name=name,
        customer=customer,
        amount=amount,
        contract_no=contract_no,
        sign_date=sign_date,
        project_type=project_type,
        pm_id=pm_id,
        start_date=start_date,
        end_date=end_date,
        description=description,
        extra_cost=extra_cost,
        cost_desc=cost_desc,
        status=PROJECT_DRAFT,
        create_by=user.id,
    )
    db.add(project)
    db.flush()
    path = await save_upload(word_contract, "contracts")
    if path:
        db.add(Contract(project_id=project.id, version=1, file_type="word", file_path=path, file_name=word_contract.filename, file_size=word_contract.size, upload_by=user.id))
        recognize_file(db, path, "contract")
    log_action(db, user, "project_create", f"{project.project_no} {project.name}")
    db.commit()
    db.refresh(project)
    return ok(ProjectOut.model_validate(project).model_dump(), "创建成功")


@router.post("/update")
async def update_project(
    project_id: int = Form(...),
    name: str | None = Form(None),
    customer: str | None = Form(None),
    amount: Decimal | None = Form(None),
    pdf_contract: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(BUSINESS, ADMIN)),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status not in {PROJECT_DRAFT, PROJECT_PENDING} and user.role != ADMIN:
        raise HTTPException(status_code=400, detail="当前状态不可编辑")
    if name:
        project.name = name
    if customer:
        project.customer = customer
    if amount is not None:
        project.amount = amount
    path = await save_upload(pdf_contract, "contracts")
    if path:
        version = db.query(func.count(Contract.id)).filter(Contract.project_id == project_id).scalar() + 1
        contract = Contract(project_id=project.id, version=version, file_type="pdf", file_path=path, file_name=pdf_contract.filename, file_size=pdf_contract.size, upload_by=user.id)
        db.add(contract)
        db.flush()
        result = recognize_file(db, path, "contract")
        extracted = result["extracted_info"]
        comparisons = [
            ("name", "项目名称", project.name, extracted.get("project_name")),
            ("amount", "合同金额", str(project.amount), extracted.get("contract_amount")),
            ("contract_no", "合同编号", project.contract_no, extracted.get("contract_no")),
        ]
        for field_name, label, registered, recognized in comparisons:
            status = "confirmed" if str(registered or "") == str(recognized or "") else "pending"
            db.add(ContractDiff(project_id=project.id, contract_id=contract.id, field_name=field_name, field_label=label, registered_value=registered, recognized_value=recognized, diff_status=status))
    log_action(db, user, "project_update", f"{project.project_no} {project.name}")
    db.commit()
    return ok(message="更新成功")


@router.post("/submit")
def submit_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(BUSINESS, ADMIN))):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status != PROJECT_DRAFT:
        raise HTTPException(status_code=400, detail="只有草稿可提交")
    project.status = PROJECT_PENDING
    create_approval_instance(db, "project", project.id, user.id)
    log_action(db, user, "project_submit", f"{project.project_no} {project.name}")
    db.commit()
    return ok(message="已提交审核")


@router.post("/approve")
def approve_project(payload: ProjectApproveIn, db: Session = Depends(get_db), user: User = Depends(require_roles(ADMIN))):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project or project.status != PROJECT_PENDING:
        raise HTTPException(status_code=400, detail="项目不可审核")
    instance = (
        db.query(ApprovalInstance)
        .filter(ApprovalInstance.business_type == "project", ApprovalInstance.business_id == project.id, ApprovalInstance.status == APPROVAL_PENDING)
        .order_by(ApprovalInstance.start_time.desc())
        .first()
    )
    task = db.query(ApprovalTask).filter(ApprovalTask.instance_id == instance.id, ApprovalTask.approver_id == user.id, ApprovalTask.status == APPROVAL_PENDING).first() if instance else None
    if task:
        process_task(db, task.id, payload.result, user, payload.opinion, payload.reason)
    else:
        project.status = PROJECT_APPROVED if payload.result == "approved" else PROJECT_DRAFT
    log_action(db, user, "project_approve", f"{project.project_no} {payload.result}")
    db.commit()
    return ok(message="审核完成")


@router.post("/start")
def start_project(payload: ProjectStartIn, db: Session = Depends(get_db), user: User = Depends(require_roles(ADMIN))):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project or project.status != PROJECT_APPROVED:
        raise HTTPException(status_code=400, detail="仅已立项项目可开始")
    project.status = PROJECT_ACTIVE
    log_action(db, user, "project_start", f"{project.project_no} {project.name}")
    db.commit()
    return ok(message="项目已进入进行中")


@router.post("/contract-diff/confirm")
def confirm_diff(payload: ContractDiffConfirmIn, db: Session = Depends(get_db), user: User = Depends(require_roles(BUSINESS, ADMIN))):
    diff = db.query(ContractDiff).filter(ContractDiff.id == payload.diff_id).first()
    if not diff:
        raise HTTPException(status_code=404, detail="差异记录不存在")
    diff.adopted_value = payload.adopted_value
    diff.diff_status = payload.diff_status
    diff.remark = payload.remark
    diff.confirm_by = user.id
    diff.confirm_time = datetime.now()
    log_action(db, user, "contract_diff_confirm", f"diff:{diff.id} {payload.diff_status}")
    db.commit()
    return ok(message="确认成功")


@router.get("/diff/list")
def list_diffs(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    diffs = db.query(ContractDiff).filter(ContractDiff.project_id == project_id).all()
    return ok([
        _diff_out(d) for d in diffs
    ])


def _diff_out(d: ContractDiff) -> dict:
    return {
        "id": d.id,
        "field_name": d.field_name,
        "field_label": d.field_label,
        "registered_value": d.registered_value,
        "recognized_value": d.recognized_value,
        "adopted_value": d.adopted_value,
        "diff_status": d.diff_status,
        "confirm_by": d.confirm_by,
        "confirm_time": d.confirm_time.isoformat() if d.confirm_time else None,
        "remark": d.remark,
        "create_time": d.create_time.isoformat() if d.create_time else None,
    }
