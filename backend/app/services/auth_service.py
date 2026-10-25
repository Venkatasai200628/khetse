"""Phone-OTP authentication business logic."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from app.core.security import (
    REGISTRATION_TOKEN_TYPE,
    decode_token,
    generate_otp,
    hash_otp,
)
from app.models.otp import OtpCode
from app.models.user import RoleEnum, User, UserRole, UserStatus

settings = get_settings()


def request_otp(db: Session, phone: str) -> tuple[OtpCode, str]:
    """Create a fresh OTP for the phone, enforcing an hourly rate limit."""
    hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_count = (
        db.scalar(
            select(func.count())
            .select_from(OtpCode)
            .where(OtpCode.phone == phone, OtpCode.created_at >= hour_ago)
        )
        or 0
    )
    if recent_count >= settings.OTP_RATE_LIMIT_PER_HOUR:
        raise RateLimitError(
            "Too many OTP requests for this number. Please try again later."
        )

    code = generate_otp()
    otp = OtpCode(
        phone=phone,
        code_hash=hash_otp(phone, code),
        expires_at=datetime.now(timezone.utc)
        + timedelta(seconds=settings.OTP_EXPIRE_SECONDS),
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return otp, code


def _latest_active_otp(db: Session, phone: str) -> OtpCode | None:
    return db.scalar(
        select(OtpCode)
        .where(OtpCode.phone == phone, OtpCode.consumed_at.is_(None))
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )


def verify_otp(db: Session, phone: str, code: str) -> User | None:
    """Consume a valid OTP. Returns the matching user, or None if the phone
    has no account yet (caller should issue a registration token)."""
    otp = _latest_active_otp(db, phone)
    if otp is None:
        raise AuthenticationError("No active code. Request a new one.")
    if otp.is_expired:
        raise AuthenticationError("Code expired. Request a new one.")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise AuthenticationError("Too many incorrect attempts. Request a new code.")

    if otp.code_hash != hash_otp(phone, code):
        otp.attempts += 1
        db.commit()
        raise AuthenticationError("Incorrect code.")

    otp.consumed_at = datetime.now(timezone.utc)
    db.commit()
    return db.scalar(select(User).where(User.phone == phone))


def register_user(
    db: Session,
    registration_token: str,
    *,
    full_name: str,
    role: RoleEnum,
    preferred_language: str,
) -> User:
    payload = decode_token(registration_token, REGISTRATION_TOKEN_TYPE)
    phone = payload["sub"]

    existing = db.scalar(select(User).where(User.phone == phone))
    if existing is not None:
        raise ConflictError("An account already exists for this phone number.")

    # Business buyers and drivers require verification before acting on the
    # platform; farmers and household buyers are active immediately.
    status = (
        UserStatus.PENDING
        if role in (RoleEnum.BUSINESS, RoleEnum.DRIVER)
        else UserStatus.ACTIVE
    )
    user = User(
        phone=phone,
        full_name=full_name,
        preferred_language=preferred_language,
        status=status,
        roles=[UserRole(role=role)],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def demo_login(db: Session, demo_code: str) -> User:
    if not settings.demo_mode:
        raise AuthorizationError("Demo login is disabled in this environment.")
    user = db.scalar(select(User).where(User.demo_code == demo_code))
    if user is None:
        raise NotFoundError("Unknown demo account.")
    return user
