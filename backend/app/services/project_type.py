"""项目类型管理服务"""
import hashlib
import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import DictItem


def normalize_type_code(value: str) -> str:
    """将项目类型名称转换为代码"""
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if ascii_part:
        return ascii_part[:40]
    return "custom_" + hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def ensure_project_type(db: Session, project_type: str | None) -> str | None:
    """确保项目类型存在，不存在则自动创建"""
    if not project_type:
        return project_type
    value = project_type.strip()
    if not value:
        return None
    exists = (
        db.query(DictItem)
        .filter(DictItem.dict_type == "project_type", ((DictItem.dict_code == value) | (DictItem.dict_name == value)))
        .first()
    )
    if exists:
        return exists.dict_code
    code = normalize_type_code(value)
    origin = code
    index = 1
    while db.query(DictItem).filter(DictItem.dict_type == "project_type", DictItem.dict_code == code).first():
        index += 1
        code = f"{origin}_{index}"
    max_sort = db.query(func.coalesce(func.max(DictItem.sort), 0)).filter(DictItem.dict_type == "project_type").scalar() or 0
    db.add(DictItem(dict_type="project_type", dict_code=code, dict_name=value, sort=max_sort + 1))
    return code
