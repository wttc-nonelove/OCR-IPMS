from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import ADMIN
from app.schemas.auth import CreateUserRequest, LoginRequest, UpdateUserRequest, UserOut
from app.schemas.common import ok
from app.services.audit import log_action

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
def list_users(
    keyword: str | None = Query(None, description="用户名、姓名、部门、手机号、邮箱关键字"),
    role: str | None = None,
    status: int | None = Query(None, ge=0, le=1, description="用户状态：1启用，0禁用"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ADMIN)),
):
    query = db.query(User)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter(or_(
            User.username.like(like),
            User.name.like(like),
            User.dept.like(like),
            User.phone.like(like),
            User.email.like(like),
        ))
    if role:
        query = query.filter(User.role == role)
    if status is not None:
        query = query.filter(User.status == status)
    return ok([UserOut.model_validate(u).model_dump() for u in query.order_by(User.id).all()])


@router.post("/create")
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ADMIN)),
):
    # 检查用户名唯一
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    # 校验角色
    valid_roles = {"admin", "business", "finance", "pm"}
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"角色无效，可选：{', '.join(valid_roles)}")
    new_user = User(
        username=payload.username,
        password=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        role=payload.role,
        dept=payload.dept,
        status=1,
    )
    db.add(new_user)
    log_action(db, user, "user_create", f"{payload.username} role:{payload.role}")
    db.commit()
    db.refresh(new_user)
    return ok(UserOut.model_validate(new_user).model_dump(), "用户创建成功")


@router.put("/update")
def update_user(
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ADMIN)),
):
    target = db.query(User).filter(User.id == payload.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if payload.name is not None:
        target.name = payload.name
    if payload.phone is not None:
        target.phone = payload.phone
    if payload.email is not None:
        target.email = payload.email
    if payload.dept is not None:
        target.dept = payload.dept
    if payload.role is not None:
        valid_roles = {"admin", "business", "finance", "pm"}
        if payload.role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"角色无效，可选：{', '.join(valid_roles)}")
        target.role = payload.role
    log_action(db, user, "user_update", f"{target.username} id:{target.id}")
    db.commit()
    db.refresh(target)
    return ok(UserOut.model_validate(target).model_dump(), "用户更新成功")


@router.put("/{user_id}/status")
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ADMIN)),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    target.status = 0 if target.status == 1 else 1
    action = "user_enable" if target.status == 1 else "user_disable"
    log_action(db, user, action, f"{target.username} id:{target.id}")
    db.commit()
    db.refresh(target)
    return ok(UserOut.model_validate(target).model_dump(), "状态已更新")


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ADMIN)),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    username = target.username
    db.delete(target)
    log_action(db, user, "user_delete", f"{username} id:{user_id}")
    db.commit()
    return ok(message="用户已删除")


@router.put("/password")
def change_password(
    old_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(old_password, user.password):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    user.password = hash_password(new_password)
    log_action(db, user, "password_change", f"{user.username}")
    db.commit()
    return ok(message="密码修改成功")
