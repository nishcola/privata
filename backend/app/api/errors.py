"""Structured HTTP serialization for expected domain errors."""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.errors import (
    BudgetExceededError,
    DomainError,
    ErrorCode,
    InvalidEpsilonError,
    InvalidQueryError,
    PrivacyModelConfigurationError,
    UnknownDatasetError,
    UnknownSessionError,
)


class ErrorBody(BaseModel):
    """Safe public details for an expected domain failure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ErrorCode
    message: str
    details: dict[str, Any]


class ErrorResponse(BaseModel):
    """Top-level structured error response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error: ErrorBody


async def domain_error_handler(_request: Request, error: DomainError) -> JSONResponse:
    """Serialize expected domain errors without exposing private state."""
    status_code = _status_code(error)
    if isinstance(error, PrivacyModelConfigurationError):
        body = ErrorBody(
            code=error.code,
            message="Privacy model configuration is invalid.",
            details={},
        )
    else:
        body = ErrorBody(
            code=error.code,
            message=error.message,
            details=error.details,
        )
    response = ErrorResponse(
        error=body
    )
    return JSONResponse(
        status_code=status_code, content=response.model_dump(mode="json")
    )


def _status_code(error: DomainError) -> int:
    if isinstance(error, (UnknownDatasetError, UnknownSessionError)):
        return 404
    if isinstance(error, BudgetExceededError):
        return 409
    if isinstance(error, (InvalidQueryError, InvalidEpsilonError)):
        return 400
    return 500
