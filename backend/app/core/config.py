from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "智能项目管理系统"
    api_prefix: str = "/api/v1"
    secret_key: str = "dev-secret-change-me-before-deploy"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 8 * 60
    database_url: str = "sqlite:///./project_mgmt.db"
    upload_dir: Path = Path("uploads")
    allowed_upload_size: int = 20 * 1024 * 1024
    paddleocr_url: str = "http://paddleocr:8000/api/v1/ocr"
    baidu_ocr_api_key: str | None = None
    baidu_ocr_secret_key: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
