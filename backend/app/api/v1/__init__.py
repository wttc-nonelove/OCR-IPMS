from fastapi import APIRouter

from app.api.v1 import approval, auth, close, export, finance, invoice, ocr, payment, project, statistics, system

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(project.router)
api_router.include_router(approval.router)
api_router.include_router(invoice.router)
api_router.include_router(payment.router)
api_router.include_router(finance.router)
api_router.include_router(close.router)
api_router.include_router(statistics.router)
api_router.include_router(export.router)
api_router.include_router(ocr.router)
api_router.include_router(system.router)
