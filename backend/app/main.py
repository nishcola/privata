"""FastAPI application assembly for Privata."""

from fastapi import FastAPI

from app.api.datasets import router as datasets_router
from app.api.errors import unknown_dataset_error_handler
from app.api.health import router as health_router
from app.datasets.synthetic import create_builtin_registry
from app.errors import UnknownDatasetError


def create_app() -> FastAPI:
    """Create the Privata HTTP application."""
    application = FastAPI(title="Privata", version="0.1.0")
    application.state.dataset_registry = create_builtin_registry()
    application.add_exception_handler(
        UnknownDatasetError, unknown_dataset_error_handler
    )
    application.include_router(health_router)
    application.include_router(datasets_router)
    return application


app = create_app()
