"""Authentication primitives: password hashing, JWT sessions, current-user dep."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Cookie, HTTPException

from .config import settings

SESSION_COOKIE = "aura_session"


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def generate_verification_code() -> str:
    # 6-digit numeric code; cryptographically random.
    return f"{secrets.randbelow(10**6):06d}"


def issue_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.jwt_expire_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid session: {exc}") from exc


async def current_user(aura_session: str | None = Cookie(default=None)) -> dict:
    """FastAPI dependency: requires a valid session cookie; returns {id, email}."""
    if not aura_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    claims = decode_token(aura_session)
    return {"id": int(claims["sub"]), "email": claims["email"]}


async def optional_user(aura_session: str | None = Cookie(default=None)) -> dict | None:
    if not aura_session:
        return None
    try:
        claims = decode_token(aura_session)
        return {"id": int(claims["sub"]), "email": claims["email"]}
    except HTTPException:
        return None
