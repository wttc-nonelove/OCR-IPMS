import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "智能项目管理系统"
    api_prefix: str = "/api/v1"
    # 生产环境必须通过环境变量 SECRET_KEY 设置固定密钥；
    # 未设置时自动生成随机密钥（每次重启会变，仅适合开发）
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 8 * 60
    database_url: str = "sqlite:///./project_mgmt.db"
    upload_dir: Path = Path("uploads")
    allowed_upload_size: int = 20 * 1024 * 1024
    paddleocr_url: str = "http://paddleocr:8000/api/v1/ocr"
    baidu_ocr_api_key: str | None = None
    baidu_ocr_secret_key: str | None = None
    llm_enabled: bool = False
    llm_api_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    # CORS 允许的来源列表，逗号分隔；生产环境应设置具体域名
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origin_list(self) -> list[str]:
        """将逗号分隔的 cors_origins 解析为列表"""
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.secret_key:
        settings.secret_key = secrets.token_urlsafe(32)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
