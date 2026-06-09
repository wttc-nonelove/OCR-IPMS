from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
import hashlib
import re
from pathlib import Path

from app.models.entities import ApprovalInstance, ApprovalRecord, ApprovalTask, Contract, ContractDiff, DictItem, Invoice, Payment, Project, ProjectClose, ProjectCost, User
from app.models.enums import ADMIN, APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED, BUSINESS, PM, PROJECT_ACTIVE, PROJECT_APPROVED, PROJECT_CLOSED, PROJECT_DRAFT, PROJECT_PENDING
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


def _normalize_type_code(value: str) -> str:
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if ascii_part:
        return ascii_part[:40]
    return "custom_" + hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def ensure_project_type(db: Session, project_type: str | None) -> str | None:
    if not project_type:
        return project_type
    value = project_type.strip()
    if not value:
        return None
    exists = (
        db.query(DictItem)
        .filter(DictItem.dict_type == "project_type", ((DictItem.dict_code == value) | (DictItem.dict_name == value)))
        .first()
    )
    if exists:
        return exists.dict_code
    code = _normalize_type_code(value)
    origin = code
    index = 1
    while db.query(DictItem).filter(DictItem.dict_type == "project_type", DictItem.dict_code == code).first():
        index += 1
        code = f"{origin}_{index}"
    max_sort = db.query(func.coalesce(func.max(DictItem.sort), 0)).filter(DictItem.dict_type == "project_type").scalar() or 0
    db.add(DictItem(dict_type="project_type", dict_code=code, dict_name=value, sort=max_sort + 1))
    return code


def _missing_fields(project: Project) -> list[str]:
    missing = []
    if not project.name:
        missing.append("项目名称")
    if not (project.party_a or project.customer):
        missing.append("甲方/客户")
    if project.amount is None or project.amount <= 0:
        missing.append("合同金额")
    return missing


def _apply_extracted_to_project(project: Project, extracted: dict, fallback_name: str | None = None) -> None:
    project.name = extracted.get("project_name") or project.name or (Path(fallback_name).stem if fallback_name else "未命名项目")
    party_a = extracted.get("party_a") or extracted.get("customer") or project.party_a or project.customer or ""
    project.party_a = party_a
    project.customer = party_a or project.customer or ""
    project.party_b = extracted.get("party_b") or project.party_b
    amount = extracted.get("contract_amount")
    if amount not in {None, ""}:
        try:
            project.amount = Decimal(str(amount))
        except Exception:
            pass
    project.contract_no = extracted.get("contract_no") or project.contract_no
    sign_date = extracted.get("sign_date")
    if sign_date:
        try:
            project.sign_date = date.fromisoformat(sign_date)
        except ValueError:
            pass


@router.get("/next-no")
def next_project_no(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ok({"project_no": generate_project_no(db)})


@router.get("/draft/current")
def current_draft(db: Session = Depends(get_db), user: User = Depends(require_roles(BUSINESS, ADMIN))):
    project = (
        db.query(Project)
        .filter(Project.status == PROJECT_DRAFT, Project.create_by == user.id)
        .order_by(Project.update_time.desc(), Project.create_time.desc())
        .first()
    )
    if not project:
        return ok(None)
    return ok({"project": ProjectOut.model_validate(project).model_dump(), "missing_fields": _missing_fields(project)})


@router.post("/word/parse-draft")
async def parse_word_draft(
    word_contract: UploadFile = File(...),
    draft_id: int | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(BUSINESS, ADMIN)),
):
    project = db.query(Project).filter(Project.id == draft_id, Project.status == PROJECT_DRAFT, Project.create_by == user.id).first() if draft_id else None
    if not project:
        project = Project(
            project_no=generate_project_no(db),
            name=Path(word_contract.filename or "未命名项目").stem,
            customer="",
            party_a="",
            party_b="",
            amount=Decimal("0"),
            project_type="software",
            status=PROJECT_DRAFT,
            create_by=user.id,
        )
        db.add(project)
        db.flush()
    path = await save_upload(word_contract, "contracts")
    contract = Contract(project_id=project.id, version=1, file_type="word", file_path=path, file_name=word_contract.filename, file_size=word_contract.size, upload_by=user.id)
    db.add(contract)
    result = recognize_file(db, path, "contract")
    extracted = result.get("extracted_info") or {}
    _apply_extracted_to_project(project, extracted, word_contract.filename)
    project_type = ensure_project_type(db, extracted.get("project_type") or project.project_type)
    project.project_type = project_type or project.project_type
    log_action(db, user, "project_word_parse_draft", f"{project.project_no} {word_contract.filename}")
    db.commit()
    db.refresh(project)
    return ok({"project": ProjectOut.model_validate(project).model_dump(), "extracted": extracted, "missing_fields": _missing_fields(project), "ocr": result}, "解析完成")


@router.post("/draft/save")
def save_draft(
    project_id: int | None = Form(None),
    name: str | None = Form(None),
    party_a: str | None = Form(None),
    party_b: str | None = Form(None),
    customer: str | None = Form(None),
    amount: Decimal | None = Form(None),
    contract_no: str | None = Form(None),
    sign_date: date | None = Form(None),
    project_type: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(BUSINESS, ADMIN)),
):
    project = db.query(Project).filter(Project.id == project_id, Project.status == PROJECT_DRAFT).first() if project_id else None
    if project_id and not project:
        raise HTTPException(status_code=404, detail="草稿不存在或已提交")
    if project and user.role != ADMIN and project.create_by != user.id:
        raise HTTPException(status_code=403, detail="无权保存该草稿")
    if not project:
        project = Project(
            project_no=generate_project_no(db),
            name=name or "未命名项目",
            customer=party_a or customer or "",
            party_a=party_a or customer or "",
            party_b=party_b,
            amount=amount or Decimal("0"),
            project_type=ensure_project_type(db, project_type or "software"),
            status=PROJECT_DRAFT,
            create_by=user.id,
        )
        db.add(project)
        db.flush()
    if name is not None:
        project.name = name
    if party_a is not None:
        project.party_a = party_a
        project.customer = party_a
    elif customer is not None:
        project.customer = customer
        project.party_a = customer
    if party_b is not None:
        project.party_b = party_b
    if amount is not None:
        project.amount = amount
    if contract_no is not None:
        project.contract_no = contract_no
    if sign_date is not None:
        project.sign_date = sign_date
    if project_type is not None:
        project.project_type = ensure_project_type(db, project_type)
    log_action(db, user, "project_draft_save", f"{project.project_no} {project.name}")
    db.commit()
    db.refresh(project)
    return ok({"project": ProjectOut.model_validate(project).model_dump(), "missing_fields": _missing_fields(project)}, "草稿已保存")


@router.post("/stamped-contract/parse")
async def parse_stamped_contract(
    project_id: int = Form(...),
    pdf_contract: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(BUSINESS, ADMIN)),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status not in {PROJECT_DRAFT, PROJECT_PENDING} and user.role != ADMIN:
        raise HTTPException(status_code=400, detail="当前状态不可上传合同")
    path = await save_upload(pdf_contract, "contracts")
    version = (db.query(func.count(Contract.id)).filter(Contract.project_id == project_id).scalar() or 0) + 1
    contract = Contract(project_id=project.id, version=version, file_type="pdf", file_path=path, file_name=pdf_contract.filename, file_size=pdf_contract.size, upload_by=user.id)
    db.add(contract)
    db.flush()
    result = recognize_file(db, path, "contract")
    extracted = result.get("extracted_info") or {}
    db.query(ContractDiff).filter(ContractDiff.project_id == project.id).delete(synchronize_session=False)
    diffs, unrecognized_fields = _create_contract_diffs(db, project, contract.id, extracted)
    log_action(db, user, "project_stamped_contract_parse", f"{project.project_no} {pdf_contract.filename}")
    db.commit()
    line_count = len((result.get("raw_text") or "").splitlines()) if result.get("raw_text") else 0
    if result.get("status") == "failed":
        parse_status = "ocr_failed"
        message = f"OCR识别失败：{result.get('error_message') or '请检查文件质量或格式'}"
    elif not any(extracted.values()):
        parse_status = "field_extract_failed"
        message = "OCR已识别文本，但未提取到合同关键字段，请查看原文摘要或手动补充"
    elif diffs:
        parse_status = "diff_found"
        message = f"识别完成，生成 {len(diffs)} 条差异"
    else:
        parse_status = "no_diff"
        message = "识别完成，未发现差异"
    return ok(
        {
            "parse_status": parse_status,
            "diffs": [_diff_out(d) for d in diffs],
            "unrecognized_fields": unrecognized_fields,
            "extracted": extracted,
            "ocr": result,
            "raw_text_preview": (result.get("raw_text") or "")[:500],
            "recognized_line_count": line_count,
        },
        message,
    )


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
        {"id": p.id, "project_no": p.project_no, "contract_no": p.contract_no, "name": p.name, "customer": p.customer, "amount": float(p.amount), "status": p.status}
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


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(BUSINESS, ADMIN))):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status == PROJECT_CLOSED:
        raise HTTPException(status_code=400, detail="已结项项目不可删除")
    if user.role == BUSINESS and not (project.status == PROJECT_DRAFT and project.create_by == user.id):
        raise HTTPException(status_code=403, detail="商务只能删除自己创建的草稿项目")

    summary = f"{project.project_no} {project.name}"
    close_ids = [row[0] for row in db.query(ProjectClose.id).filter(ProjectClose.project_id == project.id).all()]
    conditions = [
        (ApprovalInstance.business_type == "project") & (ApprovalInstance.business_id == project.id),
        (ApprovalInstance.business_type == "invoice") & (ApprovalInstance.business_id == project.id),
    ]
    if close_ids:
        conditions.append((ApprovalInstance.business_type == "close") & (ApprovalInstance.business_id.in_(close_ids)))
    instances = db.query(ApprovalInstance).filter(or_(*conditions)).all()
    instance_ids = [item.id for item in instances]
    if instance_ids:
        db.query(ApprovalRecord).filter(ApprovalRecord.instance_id.in_(instance_ids)).delete(synchronize_session=False)
        db.query(ApprovalTask).filter(ApprovalTask.instance_id.in_(instance_ids)).delete(synchronize_session=False)
        db.query(ApprovalInstance).filter(ApprovalInstance.id.in_(instance_ids)).delete(synchronize_session=False)
    db.query(Payment).filter(Payment.project_id == project.id).delete(synchronize_session=False)
    db.query(Invoice).filter(Invoice.project_id == project.id).delete(synchronize_session=False)
    db.query(ProjectClose).filter(ProjectClose.project_id == project.id).delete(synchronize_session=False)
    db.query(ProjectCost).filter(ProjectCost.project_id == project.id).delete(synchronize_session=False)
    db.query(ContractDiff).filter(ContractDiff.project_id == project.id).delete(synchronize_session=False)
    db.query(Contract).filter(Contract.project_id == project.id).delete(synchronize_session=False)
    db.query(Project).filter(Project.id == project.id).delete(synchronize_session=False)
    log_action(db, user, "project_delete", summary)
    db.commit()
    return ok(message="项目已删除")


@router.post("/create")
async def create_project(
    name: str = Form(...),
    customer: str = Form(""),
    party_a: str | None = Form(None),
    party_b: str | None = Form(None),
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
    actual_party_a = party_a or customer
    project = Project(
        project_no=generate_project_no(db),
        name=name,
        customer=actual_party_a,
        party_a=actual_party_a,
        party_b=party_b,
        amount=amount,
        contract_no=contract_no,
        sign_date=sign_date,
        project_type=ensure_project_type(db, project_type),
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
    party_a: str | None = Form(None),
    party_b: str | None = Form(None),
    amount: Decimal | None = Form(None),
    project_type: str | None = Form(None),
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
        project.party_a = customer
    if party_a:
        project.party_a = party_a
        project.customer = party_a
    if party_b:
        project.party_b = party_b
    if amount is not None:
        project.amount = amount
    if project_type:
        project.project_type = ensure_project_type(db, project_type)
    path = await save_upload(pdf_contract, "contracts")
    if path:
        version = db.query(func.count(Contract.id)).filter(Contract.project_id == project_id).scalar() + 1
        contract = Contract(project_id=project.id, version=version, file_type="pdf", file_path=path, file_name=pdf_contract.filename, file_size=pdf_contract.size, upload_by=user.id)
        db.add(contract)
        db.flush()
        result = recognize_file(db, path, "contract")
        extracted = result["extracted_info"]
        db.query(ContractDiff).filter(ContractDiff.project_id == project.id).delete(synchronize_session=False)
        _create_contract_diffs(db, project, contract.id, extracted)
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
    missing = _missing_fields(project)
    if missing:
        raise HTTPException(status_code=400, detail="请先补充：" + "、".join(missing))
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
    if payload.result not in {APPROVAL_APPROVED, APPROVAL_REJECTED}:
        raise HTTPException(status_code=400, detail="审批结果无效")
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
        if instance:
            instance.status = payload.result
            instance.finish_time = datetime.now()
        project.status = PROJECT_APPROVED if payload.result == APPROVAL_APPROVED else PROJECT_DRAFT
    log_action(db, user, "project_approve", f"{project.project_no} {payload.result} {payload.opinion or payload.reason or ''}")
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
    project = db.query(Project).filter(Project.id == diff.project_id).first()
    if project and payload.diff_status == "confirmed" and payload.adopted_value is not None:
        _apply_diff_value(project, diff.field_name, payload.adopted_value, db)
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


def _create_contract_diffs(db: Session, project: Project, contract_id: int, extracted: dict) -> tuple[list[ContractDiff], list[dict]]:
    comparisons = [
        ("name", "项目名称", project.name, extracted.get("project_name")),
        ("party_a", "甲方/客户", project.party_a or project.customer, extracted.get("party_a") or extracted.get("customer")),
        ("party_b", "乙方", project.party_b, extracted.get("party_b")),
        ("amount", "合同金额", str(project.amount), extracted.get("contract_amount")),
        ("contract_no", "合同编号", project.contract_no, extracted.get("contract_no")),
        ("sign_date", "签订日期", project.sign_date.isoformat() if project.sign_date else None, extracted.get("sign_date")),
        ("project_type", "项目类型", project.project_type, extracted.get("project_type")),
    ]
    created = []
    unrecognized = []
    for field_name, label, registered, recognized in comparisons:
        registered_text = _display_value(db, field_name, registered)
        recognized_text = _display_value(db, field_name, recognized)
        if not recognized_text:
            if registered_text:
                unrecognized.append({"field_name": field_name, "field_label": label, "registered_value": registered_text})
            continue
        if _normalize_compare_value(db, field_name, registered_text) == _normalize_compare_value(db, field_name, recognized_text):
            continue
        diff = ContractDiff(
            project_id=project.id,
            contract_id=contract_id,
            field_name=field_name,
            field_label=label,
            registered_value=registered_text,
            recognized_value=recognized_text,
            adopted_value=recognized_text,
            diff_status="pending",
        )
        db.add(diff)
        created.append(diff)
    db.flush()
    return created, unrecognized


def _display_value(db: Session, field_name: str, value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if field_name == "amount":
        try:
            return f"{Decimal(text.replace(',', '')).quantize(Decimal('0.01'))}"
        except (InvalidOperation, AttributeError):
            return text
    if field_name == "project_type":
        item = db.query(DictItem).filter(DictItem.dict_type == "project_type", ((DictItem.dict_code == text) | (DictItem.dict_name == text))).first()
        return item.dict_name if item else text
    return " ".join(text.split())


def _normalize_compare_value(db: Session, field_name: str, value: str) -> str:
    text = _display_value(db, field_name, value)
    if field_name == "amount":
        return text
    if field_name == "project_type":
        item = db.query(DictItem).filter(DictItem.dict_type == "project_type", ((DictItem.dict_code == value) | (DictItem.dict_name == value))).first()
        return (item.dict_name if item else value).strip().lower()
    return re.sub(r"\s+", "", text).strip().lower()


def _apply_diff_value(project: Project, field_name: str, value: str, db: Session) -> None:
    if field_name == "name":
        project.name = value
    elif field_name == "party_a":
        project.party_a = value
        project.customer = value
    elif field_name == "party_b":
        project.party_b = value
    elif field_name == "amount":
        try:
            project.amount = Decimal(value)
        except Exception:
            return
    elif field_name == "contract_no":
        project.contract_no = value
    elif field_name == "sign_date":
        try:
            project.sign_date = date.fromisoformat(value)
        except ValueError:
            return
    elif field_name == "project_type":
        project.project_type = ensure_project_type(db, value)
