import re

from pydantic import BaseModel, field_validator


VALID_ROLES = {"admin", "business", "finance", "pm"}
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,50}$")
PHONE_RE = re.compile(r"^[0-9+\-\s]{6,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _trim(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


def _validate_role(value: str | None) -> str | None:
    value = _trim(value)
    if value is not None and value not in VALID_ROLES:
        raise ValueError("角色无效")
    return value


def _validate_phone(value: str | None) -> str | None:
    value = _trim(value)
    if value and not PHONE_RE.match(value):
        raise ValueError("手机号格式不正确")
    return value


def _validate_email(value: str | None) -> str | None:
    value = _trim(value)
    if value and not EMAIL_RE.match(value):
        raise ValueError("邮箱格式不正确")
    return value or None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    name: str
    phone: str
    email: str | None = None
    role: str
    dept: str | None = None
    status: int

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class CreateUserRequest(BaseModel):
    username: str
    password: str
    name: str
    phone: str
    email: str | None = None
    role: str
    dept: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_RE.match(value):
            raise ValueError("用户名需为3-50位字母、数字或下划线")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("密码至少6位")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("姓名不能为空")
        return value

    @field_validator("phone")
    @classmethod
    def validate_create_phone(cls, value: str) -> str:
        value = _validate_phone(value)
        if not value:
            raise ValueError("手机号不能为空")
        return value

    @field_validator("email")
    @classmethod
    def validate_create_email(cls, value: str | None) -> str | None:
        return _validate_email(value)

    @field_validator("role")
    @classmethod
    def validate_create_role(cls, value: str) -> str:
        return _validate_role(value) or ""

    @field_validator("dept")
    @classmethod
    def validate_create_dept(cls, value: str | None) -> str | None:
        return _trim(value) or None


class UpdateUserRequest(BaseModel):
    user_id: int
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    role: str | None = None
    dept: str | None = None

    @field_validator("name")
    @classmethod
    def validate_update_name(cls, value: str | None) -> str | None:
        value = _trim(value)
        if value is not None and not value:
            raise ValueError("姓名不能为空")
        return value

    @field_validator("phone")
    @classmethod
    def validate_update_phone(cls, value: str | None) -> str | None:
        return _validate_phone(value)

    @field_validator("email")
    @classmethod
    def validate_update_email(cls, value: str | None) -> str | None:
        return _validate_email(value)

    @field_validator("role")
    @classmethod
    def validate_update_role(cls, value: str | None) -> str | None:
        return _validate_role(value)

    @field_validator("dept")
    @classmethod
    def validate_update_dept(cls, value: str | None) -> str | None:
        return _trim(value) or None
