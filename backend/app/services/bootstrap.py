from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.entities import ApprovalApprover, ApprovalNode, ApprovalTemplate, DictItem, Role, User
from app.services.system_config import ensure_default_configs


def seed_initial_data(db: Session) -> None:
    ensure_default_configs(db)
    if db.query(User).first():
        db.commit()
        return

    users = [
        User(username="admin", password=hash_password("123456"), name="系统管理员", phone="13800138000", role="admin", dept="运营中心"),
        User(username="business01", password=hash_password("123456"), name="商务用户", phone="13800138001", role="business", dept="市场部"),
        User(username="finance01", password=hash_password("123456"), name="财务用户", phone="13800138002", role="finance", dept="财务部"),
        User(username="pm01", password=hash_password("123456"), name="项目经理", phone="13800138003", role="pm", dept="项目部"),
    ]
    db.add_all(users)

    roles = [
        Role(role_name="管理员", role_code="admin", permissions='["all"]'),
        Role(role_name="商务", role_code="business", permissions='["project","statistics:partial"]'),
        Role(role_name="财务", role_code="finance", permissions='["invoice","payment","close","statistics","export"]'),
        Role(role_name="项目经理", role_code="pm", permissions='["project:view","close","statistics:partial"]'),
    ]
    db.add_all(roles)

    dicts = [
        ("project_type", "software", "软件开发", 1),
        ("project_type", "integration", "系统集成", 2),
        ("project_type", "consulting", "咨询服务", 3),
        ("project_status", "draft", "草稿", 1),
        ("project_status", "pending", "待审核", 2),
        ("project_status", "approved", "已立项", 3),
        ("project_status", "active", "进行中", 4),
        ("project_status", "closed", "已结项", 5),
        ("invoice_type", "special", "增值税专用发票", 1),
        ("invoice_type", "normal", "增值税普通发票", 2),
        ("payment_method", "bank", "银行转账", 1),
        ("payment_method", "check", "支票", 2),
        ("payment_method", "cash", "现金", 3),
    ]
    db.add_all([DictItem(dict_type=t, dict_code=c, dict_name=n, sort=s) for t, c, n, s in dicts])
    db.flush()

    project_template = ApprovalTemplate(template_name="立项审批", business_type="project")
    invoice_template = ApprovalTemplate(template_name="开票审批", business_type="invoice")
    close_template = ApprovalTemplate(template_name="结项审批", business_type="close")
    db.add_all([project_template, invoice_template, close_template])
    db.flush()

    nodes = [
        ApprovalNode(template_id=project_template.id, node_name="管理员审核", node_order=1, approval_type="或签", timeout_hours=48),
        ApprovalNode(template_id=invoice_template.id, node_name="管理员审核", node_order=1, approval_type="或签", timeout_hours=48),
        ApprovalNode(template_id=close_template.id, node_name="财务审核", node_order=1, approval_type="或签", timeout_hours=24),
    ]
    db.add_all(nodes)
    db.flush()
    db.add_all(
        [
            ApprovalApprover(node_id=nodes[0].id, approver_type="role", approver_id="admin"),
            ApprovalApprover(node_id=nodes[1].id, approver_type="role", approver_id="admin"),
            ApprovalApprover(node_id=nodes[2].id, approver_type="role", approver_id="finance"),
        ]
    )
    db.commit()
