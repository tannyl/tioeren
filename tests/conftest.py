"""Pytest configuration and shared fixtures."""

from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from api.models.base import Base
from api.models.user import User
from api.models.session import Session as SessionModel
from api.services.auth import hash_password
from api.main import app
from api.deps.database import get_db
from api.deps.config import settings


# ---------------------------------------------------------------------------
# Global test configuration
# ---------------------------------------------------------------------------

# Enable testing mode to disable secure cookies
settings.TESTING = True

# Reduce bcrypt rounds from default 12 to 4 (minimum) for test speed.
# Each hash goes from ~250ms to ~15ms. Does not affect correctness.
_original_gensalt = bcrypt.gensalt
bcrypt.gensalt = lambda rounds=4, prefix=b"2b": _original_gensalt(rounds=rounds, prefix=prefix)

# Ensure psycopg3 dialect is used
_test_db_url = settings.DATABASE_URL
if _test_db_url.startswith("postgresql://"):
    _test_db_url = _test_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
TEST_DATABASE_URL = _test_db_url


# ---------------------------------------------------------------------------
# Session-scoped fixtures (once per test run)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    return create_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)


@pytest.fixture(scope="session")
def tables(engine):
    """Create all tables before tests (idempotent)."""
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="session")
def _test_password_hash():
    """Compute the bcrypt hash once per test run, reused by all test_user fixtures."""
    return hash_password("SecurePassword123!")


@pytest.fixture(scope="session")
def _other_password_hash():
    """Compute the bcrypt hash once per test run, reused by all other_user fixtures."""
    return hash_password("SecurePassword123!")


# ---------------------------------------------------------------------------
# Function-scoped fixtures (per test, with transaction rollback isolation)
# ---------------------------------------------------------------------------

@pytest.fixture
def db(engine, tables):
    """
    Provide a database session for each test.

    Uses a connection-level transaction + session-level savepoint.
    session.commit() only releases the savepoint (not the real transaction).
    At teardown, the connection transaction is rolled back, cleaning up all data.
    """
    connection = engine.connect()
    transaction = connection.begin()

    session = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
    )()

    # Start a savepoint so session.commit() releases the savepoint,
    # not the outer connection transaction.
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def _create_auth_session(db_session, user):
    """
    Create a session record directly in DB (bypasses bcrypt verify).

    Returns the session_id string for use in cookies/headers.
    """
    now = datetime.now(timezone.utc)
    session = SessionModel(
        user_id=user.id,
        expires_at=now + timedelta(days=30),
        last_activity=now,
    )
    db_session.add(session)
    db_session.flush()
    return str(session.id)


@pytest.fixture
def test_user(db, _test_password_hash):
    """Shared test user - uses pre-computed hash (no bcrypt per test)."""
    user = User(
        email="testuser@example.com",
        password_hash=_test_password_hash,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user(db, _other_password_hash):
    """Second user for ownership/authorization tests - uses pre-computed hash."""
    user = User(
        email="otheruser@example.com",
        password_hash=_other_password_hash,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def client(db):
    """Test client with DB dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client, db, test_user):
    """
    Authenticated test client (cookie-based).

    Creates session directly in DB - no bcrypt verify needed.
    Used by tests that call `authenticated_client.get(...)`.
    """
    session_id = _create_auth_session(db, test_user)
    client.cookies.set("session_id", session_id)
    return client


@pytest.fixture
def auth_headers(client, db, test_user):
    """
    Auth headers for tests using `headers=auth_headers` pattern.

    Creates session directly in DB - no bcrypt verify needed.
    Returns Cookie header dict for use with client.get(..., headers=auth_headers).
    """
    session_id = _create_auth_session(db, test_user)
    return {"Cookie": f"session_id={session_id}"}


@pytest.fixture
def other_auth_headers(client, db, other_user):
    """Auth headers for the other_user (used in ownership/IDOR tests)."""
    session_id = _create_auth_session(db, other_user)
    return {"Cookie": f"session_id={session_id}"}
