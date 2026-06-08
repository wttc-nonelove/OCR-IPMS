from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import (
    ApprovalApprover,
    ApprovalInstance,
    ApprovalNode,
    ApprovalRecord,
    ApprovalTask,
    ApprovalTemplate,
    Project,
    ProjectClose,
    User,
)
from app.models.enums import APPROVAL_APPROVED, APPROVAL_PENDING, APPROVAL_REJECTED, PROJECT_APPROVED, PROJECT_CLOSED, PROJECT_PENDING


def create_approval_instance(db: Session, business_type: str, business_id: int, start_by: int | None) -> ApprovalInstance:
    template = db.query(ApprovalTemplate).filter(ApprovalTemplate.business_type == business_type, ApprovalTemplate.status == 1).first()
    if not template:
        raise HTTPException(status_code=400, detail="审批模板不存在")
    node = db.query(ApprovalNode).filter(ApprovalNode.template_id == template.id).order_by(ApprovalNode.node_order).first()
    if not node:
        raise HTTPException(status_code=400, detail="审批节点不存在")
    instance = ApprovalInstance(business_type=business_type, business_id=business_id, template_id=template.id, current_node_id=node.id, start_by=start_by)
    db.add(instance)
    db.flush()
    approvers = db.query(ApprovalApprover).filter(ApprovalApprover.node_id == node.id).all()
    for approver in approvers:
        users = db.query(User).filter(User.role == approver.approver_id, User.status == 1).all() if approver.approver_type == "role" else []
        for user in users:
            db.add(ApprovalTask(instance_id=instance.id, node_id=node.id, approver_id=user.id))
    return instance


def process_task(db: Session, task_id: int, result: str, user: User, opinion: str | None, reason: str | None) -> ApprovalInstance:
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id, ApprovalTask.status == APPROVAL_PENDING).first()
    if not task:
        raise HTTPException(status_code=404, detail="审批任务不存在")
    if task.approver_id != user.id:
        raise HTTPException(status_code=403, detail="无权处理该审批任务")
    if result not in {APPROVAL_APPROVED, APPROVAL_REJECTED}:
        raise HTTPException(status_code=400, detail="审批结果无效")

    instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == task.instance_id).first()
    task.status = result
    task.opinion = opinion
    task.reason = reason
    task.approve_time = datetime.now()
    db.add(
        ApprovalRecord(
            instance_id=instance.id,
            task_id=task.id,
            business_type=instance.business_type,
            business_id=instance.business_id,
            template_id=instance.template_id,
            node_id=task.node_id,
            approver_id=user.id,
            status=result,
            opinion=opinion,
            reason=reason,
        )
    )

    if result == APPROVAL_REJECTED:
        instance.status = APPROVAL_REJECTED
        instance.finish_time = datetime.now()
        _apply_business_status(db, instance, APPROVAL_REJECTED)
        return instance

    current_node = db.query(ApprovalNode).filter(ApprovalNode.id == task.node_id).first()
    next_node = (
        db.query(ApprovalNode)
        .filter(ApprovalNode.template_id == instance.template_id, ApprovalNode.node_order > current_node.node_order)
        .order_by(ApprovalNode.node_order)
        .first()
    )
    if next_node:
        instance.current_node_id = next_node.id
        for approver in db.query(ApprovalApprover).filter(ApprovalApprover.node_id == next_node.id):
            if approver.approver_type == "role":
                for next_user in db.query(User).filter(User.role == approver.approver_id, User.status == 1):
                    db.add(ApprovalTask(instance_id=instance.id, node_id=next_node.id, approver_id=next_user.id))
    else:
        instance.status = APPROVAL_APPROVED
        instance.finish_time = datetime.now()
        _apply_business_status(db, instance, APPROVAL_APPROVED)
    return instance


def _apply_business_status(db: Session, instance: ApprovalInstance, result: str) -> None:
    if instance.business_type == "project":
        project = db.query(Project).filter(Project.id == instance.business_id).first()
        if project:
            project.status = PROJECT_APPROVED if result == APPROVAL_APPROVED else "draft"
    elif instance.business_type == "close":
        close = db.query(ProjectClose).filter(ProjectClose.id == instance.business_id).first()
        if close:
            close.status = "closed" if result == APPROVAL_APPROVED else "rejected"
            project = db.query(Project).filter(Project.id == close.project_id).first()
            if project and result == APPROVAL_APPROVED:
                project.status = PROJECT_CLOSED
    elif instance.business_type == "invoice":
        instance.remark = "开票审批完成"
