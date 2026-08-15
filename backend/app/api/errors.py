"""Structured HTTP serialization for expected domain errors."""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.errors import ErrorCode, UnknownDatasetError


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


async def unknown_dataset_error_handler(
    _request: Request, error: UnknownDatasetError
) -> JSONResponse:
    """Map an unknown dataset to the stable public 404 contract."""
    response = ErrorResponse(
        error=ErrorBody(
            code=error.code,
            message=error.message,
            details=error.details,
        )
    )
    return JSONResponse(status_code=404, content=response.model_dump(mode="json"))
