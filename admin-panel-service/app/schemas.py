from typing import Any

from pydantic import BaseModel


class LoginRequest(BaseModel):
    login: str
    password: str


class AdminUserResponse(BaseModel):
    id: int
    login: str
    fullName: str
    role: str


def admin_user_response(user) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        login=user.login,
        fullName=user.full_name,
        role=user.role,
    )


def data_response(data: Any) -> dict:
    return {"data": data}
