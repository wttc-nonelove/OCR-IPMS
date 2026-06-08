from datetime import date
from decimal import Decimal

from sqlalchemy import func
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
