from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Project


executor = ThreadPoolExecutor(max_workers=2)
tasks: dict[str, dict] = {}


def enqueue_export(project_ids: list[int] | None, export_types: list[str], fmt: str, db_factory) -> dict:
    task_id = f"export_{datetime.now():%Y%m%d}_{uuid4().hex[:8]}"
    tasks[task_id] = {"task_id": task_id, "status": "processing", "download_url": None}
    executor.submit(_run_export, task_id, project_ids, export_types, fmt, db_factory)
    return tasks[task_id]


def get_export_status(task_id: str) -> dict | None:
    return tasks.get(task_id)


def _run_export(task_id: str, project_ids: list[int] | None, export_types: list[str], fmt: str, db_factory) -> None:
    db: Session = db_factory()
    try:
        settings = get_settings()
        out_dir = settings.upload_dir / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{task_id}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "项目明细"
        ws.append(["项目编号", "项目名称", "客户", "金额", "状态"])
        query = db.query(Project)
        if project_ids:
            query = query.filter(Project.id.in_(project_ids))
        for project in query.all():
            ws.append([project.project_no, project.name, project.customer, float(project.amount), project.status])
        wb.save(path)
        tasks[task_id] = {"task_id": task_id, "status": "finished", "download_url": str(path)}
    except Exception as exc:
        tasks[task_id] = {"task_id": task_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()
