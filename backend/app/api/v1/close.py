from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.entities import Project, ProjectClose, User
from app.models.enums import ADMIN, FINANCE, PM, PROJECT_ACTIVE, PROJECT_APPROVED, PROJECT_CLOSED
from app.schemas.business import CloseWithdrawIn
from app.schemas.common import ok
from app.services.audit import log_action
from app.services.approval import create_approval_instance
from app.services.files import save_upload
from app.services.finance import calculate_receivable

router = APIRouter(prefix="/close", tags=["close"])


@router.get("/list")
def list_closes(db: Session = Depends(get_db), user: User = Depends(require_roles(FINANCE, ADMIN, PM))):
    items = db.query(ProjectClose).order_by(ProjectClose.create_time.desc()).all()
    data = []
    for c in items:
        project = db.query(Project).filter(Project.id == c.project_id).first()
        data.append(
            {
                "id": c.id,
                "project_id": c.project_id,
                "project_no": project.project_no if project else None,
                "project_name": project.name if project else None,
                "close_time": c.close_time.isoformat(),
                "status": c.status,
                "balance_status": c.balance_status,
                "description": c.description,
                "create_time": c.create_time.isoformat() if c.create_time else None,
            }
        )
    return ok(data)


@router.post("/apply")
async def apply_close(
    project_id: int = Form(...),
    close_time: date = Form(...),
    description: str = Form(...),
    actual_start: date | None = Form(None),
    report_file: UploadFile | None = File(None),
    attachment: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(PM)),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or project.status not in {PROJECT_APPROVED, PROJECT_ACTIVE}:
        raise HTTPException(status_code=400, detail="仅已立项或进行中项目可结项")
    report_path = await save_upload(report_file, "close")
    attachment_path = await save_upload(attachment, "close")
    balance = calculate_receivable(db, project_id)["balance_status"]
    item = ProjectClose(project_id=project_id, actual_start=actual_start, close_time=close_time, report_file=report_path, attachment=attachment_path, description=description, balance_status=balance, create_by=user.id)
    db.add(item)
    db.flush()
    create_approval_instance(db, "close", item.id, user.id)
    log_action(db, user, "close_apply", f"project:{project.project_no} close:{item.id}")
    db.commit()
    return ok({"id": item.id}, "结项申请已提交")


@router.post("/withdraw")
def withdraw_close(payload: CloseWithdrawIn, db: Session = Depends(get_db), user: User = Depends(require_roles(ADMIN))):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project or project.status != PROJECT_CLOSED:
        raise HTTPException(status_code=400, detail="仅已结项项目可撤回")
    project.status = PROJECT_ACTIVE
    log_action(db, user, "close_withdraw", f"{project.project_no} {payload.reason}")
    db.commit()
    return ok(message="结项已撤回")
