from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings


ALLOWED_EXTENSIONS = {".doc", ".docx", ".pdf", ".jpg", ".jpeg", ".png", ".xlsx"}


async def save_upload(file: UploadFile | None, folder: str) -> str | None:
    if not file or not file.filename:
        return None
    settings = get_settings()
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    content = await file.read()
    if len(content) > settings.allowed_upload_size:
        raise HTTPException(status_code=400, detail="文件超过20MB限制")
    target_dir = settings.upload_dir / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid4().hex}{suffix}"
    target.write_bytes(content)
    return str(target)
