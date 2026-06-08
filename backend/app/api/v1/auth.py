from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.entities import User
from app.schemas.auth import LoginRequest, UserOut
from app.schemas.common import ok

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username, User.status == 1).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user.username, user.role)
    return ok({"token": token, "user": UserOut.model_validate(user).model_dump()})


@router.post("/logout")
def logout():
    return ok(message="退出成功")


@router.get("/list")
def list_users(role: str | None = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return ok([UserOut.model_validate(user).model_dump() for user in query.all()])
