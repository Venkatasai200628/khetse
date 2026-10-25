"""Request dependencies: authentication and role/ownership guards.

Role checks are enforced here — on the server — never merely hidden in the UI.
"""

import uuid
from collections.abc import Callable, Generator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, AuthorizationError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.models.user import RoleEnum, User, UserStatus

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthenticationError("Authentication required.")
    payload = decode_token(credentials.credentials, ACCESS_TOKEN_TYPE)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Invalid token.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError("User no longer exists.")
    if user.status == UserStatus.SUSPENDED:
        raise AuthorizationError("Account is suspended.")
    return user


def require_roles(
    *allowed: RoleEnum,
) -> Callable[[User], User]:
    """Dependency factory: allow the request only for the given roles."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if not any(user.has_role(role) for role in allowed):
            raise AuthorizationError(
                "You do not have permission to perform this action.",
                details={"required_roles": [r.value for r in allowed]},
            )
        return user

    return checker


def get_db_session() -> Generator[Session, None, None]:
    # Convenience alias for services importing a session dependency directly.
    yield from get_db()
