from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import ApprovalInstance, ApprovalNode, ApprovalRecord, ApprovalTask, ApprovalTemplate, Project, ProjectClose, User
from app.models.enums import APPROVAL_PENDING
from app.schemas.business import ApprovalProcessIn
from app.schemas.common import ok
from app.services.audit import log_action
from app.services.approval import process_task

router = APIRouter(prefix="/approval", tags=["approval"])


@router.get("/instance/list")
def list_instances(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(ApprovalInstance).order_by(ApprovalInstance.start_time.desc()).all()
    return ok([{"id": i.id, "business_type": i.business_type, "business_id": i.business_id, "status": i.status, "current_node_id": i.current_node_id} for i in items])


@router.get("/task/list")
def list_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(ApprovalTask).filter(ApprovalTask.approver_id == user.id, ApprovalTask.status == APPROVAL_PENDING).all()
    return ok([_task_out(db, t) for t in items])


@router.get("/flow/current")
def current_flow(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = (
        db.query(ApprovalTask)
        .filter(ApprovalTask.approver_id == user.id, ApprovalTask.status == APPROVAL_PENDING)
        .order_by(ApprovalTask.create_time.asc())
        .first()
    )
    if not task:
        return ok({"has_todo": False, "steps": [], "title": "暂无待办", "business_type": None})
    data = _task_out(db, task)
    return ok(
        {
            "has_todo": True,
            "title": data.get("title") or "审批待办",
            "business_type": data.get("business_type"),
            "business_id": data.get("business_id"),
            "project_no": data.get("project_no"),
            "current_node": data.get("node_name"),
            "next_step": _next_step_label(data.get("business_type")),
            "status": data.get("status"),
            "steps": [
                {"label": data.get("start_by") or "业务提交", "status": "done"},
                {"label": data.get("node_name") or "当前审批", "status": "current"},
                {"label": _next_step_label(data.get("business_type")), "status": "pending"},
            ],
        }
    )


@router.get("/template/list")
def list_templates(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    templates = db.query(ApprovalTemplate).order_by(ApprovalTemplate.id).all()
    result = []
    for template in templates:
        nodes = db.query(ApprovalNode).filter(ApprovalNode.template_id == template.id).order_by(ApprovalNode.node_order).all()
        result.append(
            {
                "id": template.id,
                "template_name": template.template_name,
                "business_type": template.business_type,
                "status": template.status,
                "nodes": [{"id": n.id, "node_name": n.node_name, "node_order": n.node_order, "timeout_hours": n.timeout_hours} for n in nodes],
            }
        )
    return ok(result)


@router.post("/process")
def process(payload: ApprovalProcessIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    instance = process_task(db, payload.task_id, payload.result, user, payload.opinion, payload.reason)
    log_action(db, user, "approval_process", f"{instance.business_type}:{instance.business_id} {payload.result}")
    db.commit()
    return ok({"instance_id": instance.id, "status": instance.status}, "审批完成")


def _business_summary(db: Session, instance: ApprovalInstance) -> dict:
    if instance.business_type == "project":
        project = db.query(Project).filter(Project.id == instance.business_id).first()
        return {
            "title": project.name if project else "立项审批",
            "project_no": project.project_no if project else None,
            "summary": f"{project.customer} / {float(project.amount):,.2f}" if project else "",
            "project_id": project.id if project else None,
        }
    if instance.business_type == "close":
        close = db.query(ProjectClose).filter(ProjectClose.id == instance.business_id).first()
        project = db.query(Project).filter(Project.id == close.project_id).first() if close else None
        return {
            "title": project.name if project else "结项审批",
            "project_no": project.project_no if project else None,
            "summary": close.description[:80] if close else "",
            "project_id": project.id if project else None,
            "close_id": close.id if close else None,
        }
    return {"title": "开票审批", "project_no": None, "summary": instance.remark or "", "project_id": instance.business_id}


def _task_out(db: Session, task: ApprovalTask) -> dict:
    instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == task.instance_id).first()
    node = db.query(ApprovalNode).filter(ApprovalNode.id == task.node_id).first()
    starter = db.query(User).filter(User.id == instance.start_by).first() if instance and instance.start_by else None
    summary = _business_summary(db, instance) if instance else {}
    return {
        "id": task.id,
        "instance_id": task.instance_id,
        "node_id": task.node_id,
        "node_name": node.node_name if node else "",
        "business_type": instance.business_type if instance else "",
        "business_id": instance.business_id if instance else None,
        "status": task.status,
        "create_time": task.create_time.isoformat(),
        "start_by": starter.name if starter else "",
        **summary,
    }


def _next_step_label(business_type: str | None) -> str:
    if business_type == "project":
        return "已立项"
    if business_type == "close":
        return "已结项"
    if business_type == "invoice":
        return "开票完成"
    return "流程完成"
