"""API route handlers."""

from api.routes.auth import router as auth_router
from api.routes.budgets import router as budget_router
from api.routes.accounts import router as account_router
from api.routes.categories import router as category_router
from api.routes.transactions import router as transaction_router

__all__ = ["auth_router", "budget_router", "account_router", "category_router", "transaction_router"]
