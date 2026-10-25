"""Test configuration.

Runs against a throwaway SQLite database with foreign keys enforced, so tests
exercise the same constraint behaviour as PostgreSQL without needing Docker.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_khetse.db")
os.environ.setdefault(
    "JWT_SECRET", "test-only-secret-0123456789abcdef0123456789abcdef"
)
os.environ.setdefault("ENV", "development")
os.environ.setdefault("DEMO_MODE", "true")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: F402,E401 — register all models
from app.db.session import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DB_PATH = "test_khetse.db"


@pytest.fixture(scope="session", autouse=True)
def _database():
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture()
def db():
    """Fresh tables for every test — full isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture()
def client(db):
    def override_get_db():
        from app.db.session import SessionLocal

        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
