from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import ApprovalTask, ContractDiff, Invoice, OcrRecognitionLog, Payment, Project, ProjectClose, User
from app.models.enums import APPROVAL_PENDING, FINANCE, PROJECT_ACTIVE, PROJECT_APPROVED, PROJECT_CLOSED, PROJECT_DRAFT, PROJECT_PENDING
from app.schemas.common import ok

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    active_projects = db.query(func.count(Project.id)).filter(Project.status == PROJECT_ACTIVE).scalar() or 0
    contract_amount = db.query(func.coalesce(func.sum(Project.amount), 0)).scalar() or 0
    invoice_amount = db.query(func.coalesce(func.sum(Invoice.amount), 0)).scalar() or 0
    payment_amount = db.query(func.coalesce(func.sum(Payment.amount), 0)).scalar() or 0
    return ok(
        {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "total_contract_amount": float(contract_amount),
            "total_invoice_amount": float(invoice_amount),
            "total_payment_amount": float(payment_amount),
            "total_receivable": float(invoice_amount - payment_amount),
        }
    )


def _money(value) -> float:
    return float(value or 0)


def _month_key(day: date) -> str:
    return f"{day.year}-{day.month:02d}"


def _year_range(year: int) -> tuple[datetime, datetime, date, date]:
    start_dt = datetime(year, 1, 1)
    end_dt = datetime(year + 1, 1, 1)
    start_day = date(year, 1, 1)
    end_day = date(year + 1, 1, 1)
    return start_dt, end_dt, start_day, end_day


def _month_range(month: str | None) -> tuple[int, int, date, date]:
    if month:
        try:
            year, month_num = [int(part) for part in month.split("-", 1)]
        except ValueError:
            today = date.today()
            year, month_num = today.year, today.month
    else:
        today = date.today()
        year, month_num = today.year, today.month
    if month_num < 1 or month_num > 12:
        today = date.today()
        year, month_num = today.year, today.month
    _, days = monthrange(year, month_num)
    start_day = date(year, month_num, 1)
    if month_num == 12:
        end_day = date(year + 1, 1, 1)
    else:
        end_day = date(year, month_num + 1, 1)
    return year, month_num, start_day, end_day


def _day_key(day: date) -> str:
    return f"{day.year}-{day.month:02d}-{day.day:02d}"


def _invoice_out(invoice: Invoice) -> dict:
    project = invoice.project
    return {
        "id": invoice.id,
        "project_id": invoice.project_id,
        "project_no": project.project_no if project else None,
        "project_name": project.name if project else None,
        "invoice_no": invoice.invoice_no,
        "amount": _money(invoice.amount),
        "amount_without_tax": _money(invoice.amount_without_tax),
        "tax_rate": _money(invoice.tax_rate),
        "tax_amount": _money(invoice.tax_amount),
        "invoice_date": invoice.invoice_date.isoformat(),
        "buyer": invoice.buyer,
        "seller": invoice.seller,
    }


def _payment_out(payment: Payment) -> dict:
    project = payment.project
    return {
        "id": payment.id,
        "project_id": payment.project_id,
        "project_no": project.project_no if project else None,
        "project_name": project.name if project else None,
        "invoice_no": payment.invoice.invoice_no if payment.invoice else None,
        "amount": _money(payment.amount),
        "payment_date": payment.payment_date.isoformat(),
        "payment_method": payment.payment_method,
        "voucher_file": payment.voucher_file,
        "remark": payment.remark,
    }


def _project_keyword_filter(keyword: str):
    like = f"%{keyword.strip()}%"
    return or_(
        Project.project_no.like(like),
        Project.contract_no.like(like),
        Project.name.like(like),
        Project.customer.like(like),
        Project.party_a.like(like),
    )


def _role_panel(db: Session, user: User) -> dict:
    pending_tasks = db.query(func.count(ApprovalTask.id)).filter(ApprovalTask.approver_id == user.id, ApprovalTask.status == APPROVAL_PENDING).scalar() or 0
    pending_projects = db.query(func.count(Project.id)).filter(Project.status == PROJECT_PENDING).scalar() or 0
    draft_projects = db.query(func.count(Project.id)).filter(Project.status == PROJECT_DRAFT, Project.create_by == user.id).scalar() or 0
    pending_diffs = db.query(func.count(ContractDiff.id)).filter(ContractDiff.diff_status == "pending").scalar() or 0
    pending_closes = db.query(func.count(ProjectClose.id)).filter(ProjectClose.status == APPROVAL_PENDING).scalar() or 0
    active_projects = db.query(func.count(Project.id)).filter(Project.status == PROJECT_ACTIVE).scalar() or 0
    ocr_logs = db.query(func.count(OcrRecognitionLog.id)).scalar() or 0

    base = {
        "todo_count": pending_tasks,
        "stats": [],
        "tasks": [],
        "actions": [],
        "todos": [],
    }
    if user.role == "admin":
        base.update(
            {
                "title": "审核与系统治理",
                "summary": "集中处理立项审核、项目启动、系统配置和全量数据查询。",
                "badge": "全量权限",
                "stats": [
                    {"value": pending_projects, "label": "待审核立项"},
                    {"value": pending_closes, "label": "待归档结项"},
                    {"value": pending_tasks, "label": "我的审批待办"},
                ],
                "tasks": ["审核立项申请", "确认项目开始", "维护用户、字典和审批模板"],
                "actions": [{"label": "立项审核", "path": "/project"}, {"label": "系统配置", "path": "/system"}],
                "todos": [
                    {"title": "待审核立项", "desc": f"{pending_projects} 个项目等待审核", "path": "/project", "level": "warn"},
                    {"title": "我的审批任务", "desc": f"{pending_tasks} 个审批任务待处理", "path": "/project", "level": "ok"},
                ],
            }
        )
    elif user.role == "business":
        base.update(
            {
                "title": "合同与立项办理",
                "summary": "处理合同解析、差异确认、立项登记和审核提交。",
                "badge": "立项入口",
                "stats": [
                    {"value": draft_projects, "label": "我的草稿"},
                    {"value": pending_diffs, "label": "合同待校验"},
                    {"value": ocr_logs, "label": "OCR记录"},
                ],
                "tasks": ["上传合同并提取字段", "确认合同差异", "提交立项审批"],
                "actions": [{"label": "合同登记", "path": "/project"}, {"label": "差异确认", "path": "/project"}],
                "todos": [
                    {"title": "合同差异待确认", "desc": f"{pending_diffs} 条差异需要人工确认", "path": "/project", "level": "warn"},
                    {"title": "草稿待提交", "desc": f"{draft_projects} 个草稿尚未提交", "path": "/project", "level": "ok"},
                ],
            }
        )
    elif user.role == FINANCE:
        month_start = date.today().replace(day=1)
        month_invoice = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.invoice_date >= month_start).scalar() or Decimal("0")
        month_payment = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.payment_date >= month_start).scalar() or Decimal("0")
        base.update(
            {
                "title": "开票回款与结项审核",
                "summary": "处理发票识别、开票登记、回款登记、结项财务审批。",
                "badge": "金额锁定",
                "stats": [
                    {"value": _money(month_invoice), "label": "本月开票"},
                    {"value": _money(month_payment), "label": "本月回款"},
                    {"value": pending_closes, "label": "结项待审"},
                ],
                "tasks": ["识别并登记发票", "登记回款并绑定单张发票", "审批结项申请"],
                "actions": [{"label": "发票识别", "path": "/invoice"}, {"label": "结项审核", "path": "/close"}],
                "todos": [
                    {"title": "待审核结项", "desc": f"{pending_closes} 个结项申请需要确认", "path": "/close", "level": "danger"},
                    {"title": "我的审批任务", "desc": f"{pending_tasks} 个审批任务待处理", "path": "/close", "level": "warn"},
                ],
            }
        )
    else:
        rejected_closes = db.query(func.count(ProjectClose.id)).filter(ProjectClose.create_by == user.id, ProjectClose.status == "rejected").scalar() or 0
        base.update(
            {
                "title": "项目跟踪与结项申请",
                "summary": "查看所有项目执行状态，提交验收材料和结项申请。",
                "badge": "项目视图",
                "stats": [
                    {"value": active_projects, "label": "进行中项目"},
                    {"value": pending_closes, "label": "结项审批中"},
                    {"value": rejected_closes, "label": "驳回补充"},
                ],
                "tasks": ["查看项目执行状态", "提交验收报告和结项说明", "补充被驳回的结项材料"],
                "actions": [{"label": "提交结项", "path": "/close"}, {"label": "项目详情", "path": "/project"}],
                "todos": [
                    {"title": "结项材料待补充", "desc": f"{rejected_closes} 个结项申请被驳回", "path": "/close", "level": "danger"},
                    {"title": "项目进度核对", "desc": f"{active_projects} 个进行中项目", "path": "/project", "level": "ok"},
                ],
            }
        )
    return base


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    active_projects = db.query(func.count(Project.id)).filter(Project.status == PROJECT_ACTIVE).scalar() or 0
    contract_amount = db.query(func.coalesce(func.sum(Project.amount), 0)).scalar() or 0
    invoice_amount = db.query(func.coalesce(func.sum(Invoice.amount), 0)).scalar() or 0
    payment_amount = db.query(func.coalesce(func.sum(Payment.amount), 0)).scalar() or 0
    summary = {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "total_contract_amount": _money(contract_amount),
        "total_invoice_amount": _money(invoice_amount),
        "total_payment_amount": _money(payment_amount),
        "total_receivable": _money(invoice_amount - payment_amount),
    }
    lifecycle = {
        "draft": db.query(func.count(Project.id)).filter(Project.status == PROJECT_DRAFT).scalar() or 0,
        "pending": db.query(func.count(Project.id)).filter(Project.status == PROJECT_PENDING).scalar() or 0,
        "approved": db.query(func.count(Project.id)).filter(Project.status == PROJECT_APPROVED).scalar() or 0,
        "active": db.query(func.count(Project.id)).filter(Project.status == PROJECT_ACTIVE).scalar() or 0,
        "closed": db.query(func.count(Project.id)).filter(Project.status == PROJECT_CLOSED).scalar() or 0,
    }

    today = date.today()
    months = []
    for offset in range(5, -1, -1):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year}-{month:02d}")
    invoice_map = {key: 0.0 for key in months}
    payment_map = {key: 0.0 for key in months}
    for invoice in db.query(Invoice).all():
        key = _month_key(invoice.invoice_date)
        if key in invoice_map:
            invoice_map[key] += _money(invoice.amount)
    for payment in db.query(Payment).all():
        key = _month_key(payment.payment_date)
        if key in payment_map:
            payment_map[key] += _money(payment.amount)

    monthly = [{"month": key, "invoice": invoice_map[key], "payment": payment_map[key]} for key in months]
    return ok({"summary": summary, "role_panel": _role_panel(db, user), "lifecycle": lifecycle, "monthly": monthly})


@router.get("/report")
def report(
    mode: str = "year",
    year: int | None = None,
    month: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mode = mode if mode in {"year", "month"} else "year"
    if mode == "month":
        target_year, target_month, start_day, end_day = _month_range(month)
        start_dt = datetime.combine(start_day, datetime.min.time())
        end_dt = datetime.combine(end_day, datetime.min.time())
        labels = [_day_key(date(target_year, target_month, day)) for day in range(1, monthrange(target_year, target_month)[1] + 1)]
        range_label = f"{target_year}-{target_month:02d}"
    else:
        target_year = year or date.today().year
        start_dt, end_dt, start_day, end_day = _year_range(target_year)
        labels = [f"{target_year}-{month_num:02d}" for month_num in range(1, 13)]
        range_label = str(target_year)

    project_query = db.query(Project).filter(Project.create_time >= start_dt, Project.create_time < end_dt)
    invoice_query = db.query(Invoice).join(Project).filter(Invoice.invoice_date >= start_day, Invoice.invoice_date < end_day)
    payment_query = db.query(Payment).join(Project).filter(Payment.payment_date >= start_day, Payment.payment_date < end_day)
    if keyword and keyword.strip():
        condition = _project_keyword_filter(keyword)
        project_query = project_query.filter(condition)
        invoice_query = invoice_query.filter(condition)
        payment_query = payment_query.filter(condition)

    total_projects = project_query.count()
    contract_amount = project_query.with_entities(func.coalesce(func.sum(Project.amount), 0)).scalar() or Decimal("0")
    invoice_amount = invoice_query.with_entities(func.coalesce(func.sum(Invoice.amount), 0)).scalar() or Decimal("0")
    payment_amount = payment_query.with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar() or Decimal("0")

    invoice_map = {key: 0.0 for key in labels}
    payment_map = {key: 0.0 for key in labels}
    for invoice in invoice_query.all():
        key = _day_key(invoice.invoice_date) if mode == "month" else _month_key(invoice.invoice_date)
        if key in invoice_map:
            invoice_map[key] += _money(invoice.amount)
    for payment in payment_query.all():
        key = _day_key(payment.payment_date) if mode == "month" else _month_key(payment.payment_date)
        if key in payment_map:
            payment_map[key] += _money(payment.amount)

    trend = [{"period": key, "month": key, "invoice": invoice_map[key], "payment": payment_map[key]} for key in labels]
    data = {
        "mode": mode,
        "year": target_year,
        "month": range_label if mode == "month" else None,
        "range_label": range_label,
        "summary": {
            "total_projects": total_projects,
            "total_contract_amount": _money(contract_amount),
            "total_invoice_amount": _money(invoice_amount),
            "total_payment_amount": _money(payment_amount),
            "total_receivable": _money(invoice_amount - payment_amount),
        },
        "monthly": trend,
        "trend": trend,
    }
    if mode == "month":
        data["invoices"] = [_invoice_out(invoice) for invoice in invoice_query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).all()]
        data["payments"] = [_payment_out(payment) for payment in payment_query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()]
    return ok(data)
