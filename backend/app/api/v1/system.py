from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import DictItem, OcrRecognitionLog, SysLog, User
from app.schemas.common import ok

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
def list_logs(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit = max(1, min(limit, 200))
    logs = db.query(SysLog).order_by(SysLog.create_time.desc()).limit(limit).all()
    return ok(
        [
            {
                "id": log.id,
                "username": log.username,
                "action": log.action,
                "content": log.content,
                "create_time": log.create_time.isoformat() if log.create_time else None,
            }
            for log in logs
        ]
    )


@router.get("/ocr-logs")
def list_ocr_logs(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit = max(1, min(limit, 200))
    logs = db.query(OcrRecognitionLog).order_by(OcrRecognitionLog.create_time.desc()).limit(limit).all()
    return ok(
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
        ]
    )
