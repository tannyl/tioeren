"""FastAPI dependencies for auth, database, etc."""

from api.deps.auth import get_current_user, CurrentUser
from api.deps.database import get_db

__all__ = ["get_current_user", "CurrentUser", "get_db"]
