import re

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_pagination, require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import DictItem, OcrRecognitionLog, SysLog, User
from app.models.enums import ADMIN
from app.schemas.common import ok, paginated
from app.services.system_config import (
    get_llm_config_payload,
    get_llm_runtime_config,
    runtime_from_profile,
    test_llm_connection,
    update_llm_config,
)

router = APIRouter(prefix="/system", tags=["system"])


class LLMProfilePayload(BaseModel):
    id: str | None = None
    name: str
    api_base_url: str
    model: str
    api_key: str | None = None


class LLMConfigUpdate(BaseModel):
    enabled: bool
    active_profile_id: str | None = None
    profiles: list[LLMProfilePayload]


class LLMConfigTest(BaseModel):
    enabled: bool | None = None
    profile: LLMProfilePayload | None = None


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


@router.get("/config/llm")
def get_llm_config(db: Session = Depends(get_db), user: User = Depends(require_roles(ADMIN))):
    return ok(get_llm_config_payload(db))


@router.put("/config/llm")
def save_llm_config(payload: LLMConfigUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(ADMIN))):
    data = update_llm_config(
        db,
        user,
        enabled=payload.enabled,
        profiles=[profile.model_dump() for profile in payload.profiles],
        active_profile_id=payload.active_profile_id,
    )
    return ok(data, "LLM 配置已保存")


@router.post("/config/llm/test")
def test_llm_config(payload: LLMConfigTest, db: Session = Depends(get_db), user: User = Depends(require_roles(ADMIN))):
    current = get_llm_runtime_config(db)
    if payload.profile:
        config = runtime_from_profile(current.enabled if payload.enabled is None else payload.enabled, payload.profile.model_dump(), current)
    else:
        config = current
        if payload.enabled is not None:
            config.enabled = payload.enabled
    return ok(test_llm_connection(config))


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
