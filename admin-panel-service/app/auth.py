import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal, get_db
from app.models import AdminUser


ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123!")
ADMIN_FULL_NAME = os.environ.get("ADMIN_FULL_NAME", "Администратор")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-env")
JWT_ALG = os.environ.get("JWT_ALG", "HS256")
JWT_EXPIRES_MIN = int(os.environ.get("JWT_EXPIRES_MIN", "60"))
PASSWORD_HASH_ITERATIONS = 210_000


@dataclass
class AdminSession:
    user: AdminUser
    token: str


def _auth_error(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"code": code, "message": message, "details": {}})


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, expected = password_hash.split("$", 3)
        iterations = int(iterations_raw)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        iterations,
    ).hex()
    return secrets.compare_digest(actual, expected)


def issue_access_token(user: AdminUser) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=JWT_EXPIRES_MIN)
    payload = {
        "sub": user.login,
        "role": user.role,
        "fullName": user.full_name,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return token, JWT_EXPIRES_MIN * 60


async def seed_admin_user() -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(AdminUser).where(AdminUser.login == ADMIN_LOGIN))
        user = result.scalar_one_or_none()
        next_hash = hash_password(ADMIN_PASSWORD)
        if user is None:
            db.add(
                AdminUser(
                    login=ADMIN_LOGIN,
                    password_hash=next_hash,
                    full_name=ADMIN_FULL_NAME,
                    role="admin",
                    is_active=True,
                )
            )
        else:
            user.full_name = ADMIN_FULL_NAME
            user.role = "admin"
            user.is_active = True
            if not verify_password(ADMIN_PASSWORD, user.password_hash):
                user.password_hash = next_hash
        await db.commit()


async def require_current_admin(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> AdminSession:
    if not authorization:
        raise _auth_error("AUTH_REQUIRED", "Authorization header is required")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _auth_error("INVALID_AUTH_HEADER", "Authorization header must be 'Bearer <token>'")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError as exc:
        raise _auth_error("TOKEN_EXPIRED", "Token is expired") from exc
    except jwt.InvalidTokenError as exc:
        raise _auth_error("INVALID_TOKEN", "Token is invalid") from exc

    login = payload.get("sub")
    role = payload.get("role")
    if not isinstance(login, str) or not login:
        raise _auth_error("INVALID_TOKEN", "Token subject is invalid")
    if role != "admin":
        raise _auth_error("FORBIDDEN", "Admin role is required")

    result = await db.execute(
        select(AdminUser).where(
            AdminUser.login == login,
            AdminUser.is_active == True,
            AdminUser.role == "admin",
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise _auth_error("INVALID_TOKEN", "Admin user is inactive or missing")

    return AdminSession(user=user, token=token)
