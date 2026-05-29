from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AdminSession, issue_access_token, require_current_admin, verify_password
from app.database import get_db
from app.models import AdminUser
from app.schemas import LoginRequest, admin_user_response, data_response


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.login == body.login,
            AdminUser.is_active == True,
            AdminUser.role == "admin",
        )
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid login or password", "details": {}},
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    access_token, expires_in = issue_access_token(user)
    return data_response(
        {
            "accessToken": access_token,
            "expiresIn": expires_in,
            "user": admin_user_response(user),
        }
    )


@router.get("/me")
async def me(session: AdminSession = Depends(require_current_admin)):
    return data_response(admin_user_response(session.user))


@router.post("/logout", status_code=204)
async def logout(_: AdminSession = Depends(require_current_admin)):
    return Response(status_code=204)
