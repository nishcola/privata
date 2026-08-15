"""Health-check HTTP contract."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response returned by the service health check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ok"] = "ok"


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Report that the HTTP application is running."""
    return HealthResponse()
