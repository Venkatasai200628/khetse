"""Auth request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import RoleEnum, UserStatus

PHONE_PATTERN = r"^\+\d{10,15}$"

# Roles a person may choose during self-registration. Admin and FPO operator
# accounts are provisioned by administrators / seeded demo data only.
SELF_REGISTRATION_ROLES = (
    RoleEnum.FARMER,
    RoleEnum.BUYER,
    RoleEnum.BUSINESS,
    RoleEnum.DRIVER,
)


def _normalise_phone(value: str) -> str:
    value = value.strip().replace(" ", "").replace("-", "")
    if value.startswith("00"):
        value = "+" + value[2:]
    if not value.startswith("+") and len(value) == 10:
        value = "+91" + value  # default to India for 10-digit local numbers
    return value


class PhoneRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = _normalise_phone(v)
        import re

        if not re.match(PHONE_PATTERN, v):
            raise ValueError("Phone must be a valid number like +919876543210.")
        return v


class OtpVerifyRequest(PhoneRequest):
    code: str = Field(min_length=4, max_length=8)


class RegisterRequest(BaseModel):
    registration_token: str
    full_name: str = Field(min_length=2, max_length=120)
    role: RoleEnum
    preferred_language: str = Field(default="en", pattern="^[a-z]{2}(-[A-Za-z]{2,4})?$")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: RoleEnum) -> RoleEnum:
        if v not in SELF_REGISTRATION_ROLES:
            raise ValueError(
                f"Role '{v.value}' cannot be self-registered. Contact the platform team."
            )
        return v


class DemoLoginRequest(BaseModel):
    demo_code: str = Field(min_length=2, max_length=40)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str
    full_name: str | None
    preferred_language: str
    status: UserStatus
    roles: list[RoleEnum] = []
    created_at: datetime

    @field_validator("roles", mode="before")
    @classmethod
    def extract_role_values(cls, v):
        """Accept both raw enums and UserRole ORM objects."""
        return [item.role if hasattr(item, "role") else item for item in v]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class RegistrationRequiredResponse(BaseModel):
    outcome: str = "registration_required"
    registration_token: str
    phone: str


class AuthenticatedResponse(TokenResponse):
    outcome: str = "authenticated"


class OtpSentResponse(BaseModel):
    status: str = "sent"
    expires_in_seconds: int
    # Present ONLY when the SMS provider is a mock and ENV is not production —
    # lets developers complete login without a real SMS provider. Never in prod.
    dev_otp: str | None = None
    note: str | None = None
