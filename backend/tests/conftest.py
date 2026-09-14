import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import SessionLocal, get_db


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """
    TestClient fixture for executing synchronous API test requests.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    SQLAlchemy database session fixture for integration tests.
    Rolls back any modifications upon completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
