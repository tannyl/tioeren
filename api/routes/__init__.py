"""API route handlers."""

from api.routes.auth import router as auth_router
from api.routes.budgets import router as budget_router
from api.routes.accounts import router as account_router
from api.routes.transactions import router as transaction_router
from api.routes.dashboard import router as dashboard_router
from api.routes.forecast import router as forecast_router
from api.routes.budget_posts import router as budget_post_router
from api.routes.bank_days import router as bank_days_router

__all__ = ["auth_router", "budget_router", "account_router", "transaction_router", "dashboard_router", "forecast_router", "budget_post_router", "bank_days_router"]
