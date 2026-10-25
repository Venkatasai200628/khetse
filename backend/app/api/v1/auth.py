"""Authentication endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, create_registration_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthenticatedResponse,
    DemoLoginRequest,
    OtpSentResponse,
    OtpVerifyRequest,
    PhoneRequest,
    RegisterRequest,
    RegistrationRequiredResponse,
    TokenResponse,
    UserPublic,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _token_response(user: User) -> TokenResponse:
    roles = [ur.role.value for ur in user.roles]
    return TokenResponse(
        access_token=create_access_token(str(user.id), roles),
        user=UserPublic.model_validate(user),
    )


@router.post("/otp/request", response_model=OtpSentResponse)
def request_otp(body: PhoneRequest, db: Session = Depends(get_db)):
    _, code = auth_service.request_otp(db, body.phone)
    dev_otp = None
    note = None
    if settings.demo_mode and settings.SMS_PROVIDER == "mock":
        # Development convenience only — impossible once a real SMS provider
        # is configured or the environment is production.
        dev_otp = code
        note = (
            "OTP returned in response because the SMS provider is a mock in a "
            "non-production environment. This never happens in production."
        )
    return OtpSentResponse(
        expires_in_seconds=settings.OTP_EXPIRE_SECONDS, dev_otp=dev_otp, note=note
    )


@router.post("/otp/verify", response_model=AuthenticatedResponse | RegistrationRequiredResponse)
def verify_otp(body: OtpVerifyRequest, db: Session = Depends(get_db)):
    user = auth_service.verify_otp(db, body.phone, body.code)
    if user is not None:
        response = AuthenticatedResponse(**_token_response(user).model_dump())
        return response
    return RegistrationRequiredResponse(
        registration_token=create_registration_token(body.phone), phone=body.phone
    )


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register_user(
        db,
        body.registration_token,
        full_name=body.full_name,
        role=body.role,
        preferred_language=body.preferred_language,
    )
    return _token_response(user)


@router.post("/demo-login", response_model=TokenResponse)
def demo_login(body: DemoLoginRequest, db: Session = Depends(get_db)):
    user = auth_service.demo_login(db, body.demo_code)
    return _token_response(user)


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user
