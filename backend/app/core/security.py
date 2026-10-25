"""Tokens and OTP primitives.

- Access tokens: JWT (HS256) carrying user id and roles.
- Registration tokens: short-lived JWTs issued after OTP verification for
  phones that have no account yet.
- OTPs: 6-digit codes, stored only as HMAC-SHA256 hashes bound to the app
  secret, with expiry and attempt limits enforced by the auth service.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import get_settings
from app.core.errors import AuthenticationError

settings = get_settings()

ACCESS_TOKEN_TYPE = "access"
REGISTRATION_TOKEN_TYPE = "registration"
REGISTRATION_TOKEN_MINUTES = 15


def hash_otp(phone: str, code: str) -> str:
    digest = hmac.new(
        settings.JWT_SECRET.encode(), f"{phone}:{code}".encode(), hashlib.sha256
    )
    return digest.hexdigest()


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _create_token(subject: str, token_type: str, minutes: int, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "typ": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, roles: list[str]) -> str:
    return _create_token(
        str(user_id), ACCESS_TOKEN_TYPE, settings.ACCESS_TOKEN_EXPIRE_MINUTES, {"roles": roles}
    )


def create_registration_token(phone: str) -> str:
    return _create_token(phone, REGISTRATION_TOKEN_TYPE, REGISTRATION_TOKEN_MINUTES)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid token.") from exc
    if payload.get("typ") != expected_type:
        raise AuthenticationError("Invalid token type for this action.")
    return payload
