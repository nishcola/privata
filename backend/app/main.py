"""FastAPI application assembly for Privata."""

from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    """Create the Privata HTTP application."""
    application = FastAPI(title="Privata", version="0.1.0")
    application.include_router(health_router)
    return application


app = create_app()
