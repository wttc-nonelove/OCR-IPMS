from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import User
from app.schemas.common import ok
from app.services.files import save_upload
from app.services.ocr import recognize_file

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/contract")
async def contract_ocr(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    path = await save_upload(file, "ocr")
    data = recognize_file(db, path, "contract")
    db.commit()
    return ok(data)


@router.post("/invoice")
async def invoice_ocr(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    path = await save_upload(file, "ocr")
    data = recognize_file(db, path, "invoice")
    db.commit()
    return ok(data)


@router.post("/payment")
async def payment_ocr(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    path = await save_upload(file, "ocr")
    data = recognize_file(db, path, "payment")
    db.commit()
    return ok(data)
