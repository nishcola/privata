"""HTTP routes for privacy-session orchestration."""

from fastapi import APIRouter, Request

from app.api.errors import ErrorResponse
from app.dp.queries.models import QueryRequest
from app.services.analysis import AnalysisService
from app.services.models import (
    CreateSessionRequest,
    QueryHistoryResponse,
    QueryReleaseResponse,
    SessionResponse,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


@router.post(
    "",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}},
)
def create_session(
    request_body: CreateSessionRequest, request: Request
) -> SessionResponse:
    """Create an in-memory privacy session for a public dataset."""
    return _service(request).create_session(**request_body.model_dump())


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_session(session_id: str, request: Request) -> SessionResponse:
    """Return public accounting state for one privacy session."""
    return _service(request).get_session(session_id=session_id)


@router.post(
    "/{session_id}/queries",
    response_model=QueryReleaseResponse,
    response_model_exclude_none=True,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def execute_query(
    session_id: str, request_body: QueryRequest, request: Request
) -> QueryReleaseResponse:
    """Execute and account for one valid differential privacy query."""
    return _service(request).execute_query(session_id=session_id, request=request_body)


@router.get(
    "/{session_id}/history",
    response_model=list[QueryHistoryResponse],
    responses={404: {"model": ErrorResponse}},
)
def get_history(session_id: str, request: Request) -> tuple[QueryHistoryResponse, ...]:
    """Return safe metadata for completed queries in a privacy session."""
    return _service(request).get_history(session_id=session_id)
