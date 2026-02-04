"""Pytest configuration and fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.models.base import Base
from api.deps.config import settings


# Use a test database URL (can be overridden with TEST_DATABASE_URL env var)
TEST_DATABASE_URL = settings.DATABASE_URL


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    test_engine = create_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    return test_engine


@pytest.fixture(scope="session")
def tables(engine):
    """Create all tables before tests and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(engine, tables):
    """
    Provide a database session for each test.

    The session is rolled back after each test to maintain isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()

    TestSessionLocal = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
    )

    session = TestSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
