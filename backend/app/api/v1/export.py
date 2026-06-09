from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import SessionLocal, get_db
from app.models.entities import User
from app.models.enums import ADMIN, FINANCE
from app.schemas.common import ok
from app.services.export_queue import enqueue_export, get_export_path, get_export_status

router = APIRouter(prefix="/export", tags=["export"])


class ExportBatchIn(BaseModel):
    project_ids: list[int] | None = None
    export_types: list[str] = ["project"]
    format: str = "excel"
    mode: str = "year"
    year: int | None = None
    month: str | None = None
    keyword: str | None = None


@router.post("/batch")
def export_batch(payload: ExportBatchIn, db: Session = Depends(get_db), user: User = Depends(require_roles(ADMIN, FINANCE))):
    return ok(enqueue_export(payload.project_ids, payload.export_types, payload.format, SessionLocal, payload.year, payload.keyword, payload.mode, payload.month))


@router.get("/status")
def export_status(task_id: str, user: User = Depends(require_roles(ADMIN, FINANCE))):
    task = get_export_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="导出任务不存在或已失效")
    return ok(task)


@router.get("/download")
def export_download(task_id: str, user: User = Depends(require_roles(ADMIN, FINANCE))):
    path = get_export_path(task_id)
    if not path:
        raise HTTPException(status_code=404, detail="导出文件不存在或任务未完成")
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
