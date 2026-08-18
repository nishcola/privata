"""FastAPI application assembly for Privata."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.datasets import router as datasets_router
from app.api.errors import domain_error_handler
from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.datasets.synthetic import create_builtin_registry
from app.dp.accounting import PrivacySessionStore
from app.errors import DomainError
from app.services.analysis import AnalysisService


def create_app() -> FastAPI:
    """Create the Privata HTTP application."""
    application = FastAPI(title="Privata", version="0.1.0")
    application.state.dataset_registry = create_builtin_registry()
    application.state.session_store = PrivacySessionStore()
    application.state.analysis_service = AnalysisService(
        dataset_registry=application.state.dataset_registry,
        session_store=application.state.session_store,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=("http://localhost:5173", "http://127.0.0.1:5173"),
        allow_methods=("GET", "POST"),
        allow_headers=("Content-Type",),
    )
    application.add_exception_handler(DomainError, domain_error_handler)
    application.include_router(health_router)
    application.include_router(datasets_router)
    application.include_router(sessions_router)
    return application


app = create_app()
