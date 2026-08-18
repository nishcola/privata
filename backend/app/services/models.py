"""Typed, API-safe contracts produced by analysis orchestration."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.datasets.models import StrictBoolean
from app.dp.models import (
    NonEmptyString,
    NonNegativeFiniteFloat,
    PositiveFiniteFloat,
    QueryResultMetadata,
)
from app.dp.queries.models import QueryType

NoisyResult = float | tuple[float, ...]
TrueResult = int | float | tuple[int, ...]
DemoResult = Annotated[TrueResult | None, Field(default=None)]


class ServiceContractModel(BaseModel):
    """Base configuration for immutable API-safe service contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class CreateSessionRequest(ServiceContractModel):
    """Required public input for an in-memory privacy session."""

    dataset_id: NonEmptyString
    epsilon_total: PositiveFiniteFloat
    strict_mode: StrictBoolean


class SessionResponse(ServiceContractModel):
    """Public accounting state for one analysis session."""

    session_id: NonEmptyString
    dataset_id: NonEmptyString
    epsilon_total: PositiveFiniteFloat
    epsilon_spent: NonNegativeFiniteFloat
    epsilon_remaining: NonNegativeFiniteFloat
    strict_mode: StrictBoolean


class QueryHistoryResponse(ServiceContractModel):
    """Safe accounting metadata for one completed private release."""

    query_id: NonEmptyString
    query_type: QueryType
    epsilon_charged: PositiveFiniteFloat
    epsilon_remaining: NonNegativeFiniteFloat
    timestamp: datetime


class QueryReleaseResponse(QueryResultMetadata):
    """Public response for a successful differential privacy release."""

    noisy_result: NoisyResult
    true_result: DemoResult
    true_result_is_demo: StrictBoolean | None = None
