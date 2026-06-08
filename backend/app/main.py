import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.models import entities  # noqa: F401
from app.schemas.common import ok
from app.services.bootstrap import seed_initial_data

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


def _run_alembic_upgrade():
    """运行 Alembic 迁移到最新版本"""
    alembic_dir = Path(__file__).parent.parent / "alembic"
    if not alembic_dir.exists():
        # 没有 alembic 目录，回退到 create_all
        Base.metadata.create_all(bind=engine)
        return
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(alembic_dir.parent),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        # 迁移失败时回退到 create_all（开发环境兼容）
        print(f"Alembic migration failed: {exc.stderr}")
        Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def startup():
    _run_alembic_upgrade()
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return ok({"status": "ok"})
