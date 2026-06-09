from pydantic import BaseModel


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


class UpdateUserRequest(BaseModel):
    user_id: int
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    role: str | None = None
    dept: str | None = None
