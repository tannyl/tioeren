"""Main FastAPI application entry point."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.deps.config import settings
from api.routes import auth_router, budget_router, account_router, category_router, transaction_router, dashboard_router, forecast_router, budget_post_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Tiøren API",
    description="Personal finance management API",
    version="0.1.0",
    debug=settings.DEBUG,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost"],  # Vite, SvelteKit, Caddy proxy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch all unhandled exceptions and return a safe JSON response.

    Logs the full traceback server-side but never exposes it to the client.
    """
    # Log the full exception with traceback
    logger.exception(
        "Unhandled exception occurred",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
        }
    )

    # Return safe JSON response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Register routers
app.include_router(auth_router, prefix="/api")
app.include_router(budget_router, prefix="/api")
app.include_router(account_router, prefix="/api")
app.include_router(category_router, prefix="/api")
app.include_router(transaction_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(forecast_router, prefix="/api")
app.include_router(budget_post_router, prefix="/api")


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
