"""Consistent application errors and handlers.

Every error response has the shape:

    {"error": {"code": "...", "message": "...", "details": {...}}}
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class AppError(Exception):
    """Base class for expected application errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "app_error"

    def __init__(self, message: str, *, details: dict | None = None, status_code: int | None = None):
        self.message = message
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthenticated"


class AuthorizationError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"


def _error_response(status_code: int, code: str, message: str, details: dict) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError):
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError):
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            "Request validation failed.",
            {"fields": [err["loc"][-1] if err.get("loc") else "?" for err in exc.errors()]},
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(_request: Request, exc: SQLAlchemyError):  # pragma: no cover
        # Log server-side; never leak SQL details to clients.
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "database_error",
            "A database error occurred.",
            {},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception):  # pragma: no cover
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
            {},
        )
