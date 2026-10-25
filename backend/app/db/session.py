"""Database engine, session factory and declarative base.

Works with PostgreSQL (primary) and SQLite (tests / quick local runs).
SQLite connections enable foreign-key enforcement so constraint behaviour
matches PostgreSQL in tests.
"""

from collections.abc import Generator

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Explicit naming convention keeps Alembic-generated constraint names stable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _normalise_driver(url: str) -> str:
    """Managed Postgres providers (Render, Neon, Supabase, Heroku) hand out
    bare postgresql:// URLs; SQLAlchemy needs the DBAPI dialect named."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _build_engine(url: str):
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _record):  # pragma: no cover
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(_normalise_driver(url), pool_pre_ping=True, pool_size=5, max_overflow=10)


settings = get_settings()
engine = _build_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
