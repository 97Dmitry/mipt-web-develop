import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Header, HTTPException


ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123!")
ADMIN_FULL_NAME = os.environ.get("ADMIN_FULL_NAME", "Администратор")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-env")
JWT_ALG = os.environ.get("JWT_ALG", "HS256")
JWT_EXPIRES_MIN = int(os.environ.get("JWT_EXPIRES_MIN", "60"))


@dataclass
class AdminPrincipal:
    login: str
    role: str
    full_name: str


def _auth_error(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"code": code, "message": message, "details": {}})


def authenticate_admin(login: str, password: str) -> bool:
    return secrets.compare_digest(login, ADMIN_LOGIN) and secrets.compare_digest(password, ADMIN_PASSWORD)


def issue_access_token() -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=JWT_EXPIRES_MIN)
    payload = {
        "sub": ADMIN_LOGIN,
        "role": "admin",
        "fullName": ADMIN_FULL_NAME,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return token, JWT_EXPIRES_MIN * 60


def require_admin_jwt(authorization: str | None = Header(default=None)) -> AdminPrincipal:
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
    full_name = payload.get("fullName") or ADMIN_FULL_NAME
    if not isinstance(login, str) or not login:
        raise _auth_error("INVALID_TOKEN", "Token subject is invalid")
    if role != "admin":
        raise _auth_error("FORBIDDEN", "Admin role is required")

    return AdminPrincipal(login=login, role=role, full_name=full_name)
