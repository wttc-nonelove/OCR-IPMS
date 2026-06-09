from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.models import entities  # noqa: F401
from app.schemas.common import ok
from app.services.bootstrap import seed_initial_data
from app.services.schema_compat import ensure_compatible_schema

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    ensure_compatible_schema(engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return ok({"status": "ok"})
