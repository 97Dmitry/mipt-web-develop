from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.auth import (
    ADMIN_FULL_NAME,
    ADMIN_LOGIN,
    AdminPrincipal,
    authenticate_admin,
    issue_access_token,
    require_admin_jwt,
)
from app.schemas import data_response

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login: str
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    if not authenticate_admin(body.login, body.password):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid login or password", "details": {}})

    access_token, expires_in = issue_access_token()
    return data_response({
        "accessToken": access_token,
        "expiresIn": expires_in,
        "user": {
            "id": 1,
            "login": ADMIN_LOGIN,
            "fullName": ADMIN_FULL_NAME,
            "role": "admin",
        },
    })


@router.get("/me")
async def me(principal: AdminPrincipal = Depends(require_admin_jwt)):
    return data_response({
        "id": 1,
        "login": principal.login,
        "fullName": principal.full_name,
        "role": principal.role,
    })


@router.post("/logout", status_code=204)
async def logout(_: AdminPrincipal = Depends(require_admin_jwt)):
    return Response(status_code=204)
