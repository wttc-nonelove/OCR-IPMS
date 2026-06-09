import re

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_pagination
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import DictItem, OcrRecognitionLog, SysLog, User
from app.schemas.common import ok, paginated

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/dicts")
def list_dicts(dict_type: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(DictItem)
    if dict_type:
        query = query.filter(DictItem.dict_type == dict_type)
    items = query.order_by(DictItem.dict_type, DictItem.sort, DictItem.id).all()
    return ok(
        [
            {
                "id": item.id,
                "dict_type": item.dict_type,
                "dict_code": item.dict_code,
                "dict_name": item.dict_name,
                "sort": item.sort,
                "status": item.status,
            }
            for item in items
        ]
    )


@router.get("/logs")
def list_logs(pg: Pagination = Depends(get_pagination), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(SysLog)
    total = query.count()
    logs = query.order_by(SysLog.create_time.desc()).offset(pg.offset).limit(pg.limit).all()
    return paginated(
        [
            {
                "id": log.id,
                "username": log.username,
                "action": log.action,
                "content": log.content,
                "create_time": log.create_time.isoformat() if log.create_time else None,
            }
            for log in logs
        ],
        total, pg.page, pg.page_size,
    )


@router.get("/ocr-logs")
def list_ocr_logs(pg: Pagination = Depends(get_pagination), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(OcrRecognitionLog)
    total = query.count()
    logs = query.order_by(OcrRecognitionLog.create_time.desc()).offset(pg.offset).limit(pg.limit).all()
    return paginated(
        [
            {
                "id": log.id,
                "file_name": log.file_name,
                "recognition_type": log.recognition_type,
                "engine": log.engine,
                "confidence": float(log.confidence) if log.confidence is not None else None,
                "status": log.status,
                "duration": float(log.duration) if log.duration is not None else None,
                "error_message": log.error_message,
                "create_time": log.create_time.isoformat() if log.create_time else None,
            }
            for log in logs
        ],
        total, pg.page, pg.page_size,
    )


@router.get("/ocr-health")
def ocr_health(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    settings = get_settings()
    health_url = re.sub(r"/api/v1/ocr/?$", "/health", settings.paddleocr_url)
    latest = db.query(OcrRecognitionLog).order_by(OcrRecognitionLog.create_time.desc()).first()
    service = {
        "reachable": False,
        "status": "unreachable",
        "url": settings.paddleocr_url,
        "health_url": health_url,
        "model_loaded": False,
        "load_error": None,
        "error": None,
    }
    try:
        response = httpx.get(health_url, timeout=5)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", payload)
        service.update(
            {
                "reachable": True,
                "status": data.get("status") or "ready",
                "model_loaded": bool(data.get("model_loaded")),
                "load_error": data.get("load_error"),
            }
        )
    except Exception as exc:
        service["error"] = str(exc)

    return ok(
        {
            "service": service,
            "latest_log": None
            if not latest
            else {
                "id": latest.id,
                "file_name": latest.file_name,
                "recognition_type": latest.recognition_type,
                "engine": latest.engine,
                "status": latest.status,
                "error_message": latest.error_message,
                "create_time": latest.create_time.isoformat() if latest.create_time else None,
            },
        }
    )
