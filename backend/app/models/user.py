"""Users and role assignments."""

import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base
from app.models.enums import RoleEnum, UserStatus  # re-exported below for convenience

__all__ = ["RoleEnum", "UserStatus", "User", "UserRole"]


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # E.164
    full_name: Mapped[str | None] = mapped_column(String(120))
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    # Demo-login identifier for seeded demonstration accounts (demo mode only).
    demo_code: Mapped[str | None] = mapped_column(String(40), unique=True)
    # Set for FPO operator accounts: which FPO they belong to.
    fpo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fpo_profiles.id"), index=True
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", native_enum=False),
        default=UserStatus.PENDING,
        nullable=False,
        index=True,
    )

    roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def has_role(self, role: RoleEnum) -> bool:
        return any(ur.role == role for ur in self.roles)


class UserRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_roles_user_id_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, name="role_enum", native_enum=False), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="roles")
