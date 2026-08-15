"""Typed request contracts for supported query kinds."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Epsilon = Annotated[
    float,
    Field(strict=True, gt=0, le=10, allow_inf_nan=False),
]
NonEmptyString = Annotated[str, Field(strict=True, min_length=1)]


class QueryContractModel(BaseModel):
    """Base configuration shared by query request contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryType(StrEnum):
    """Aggregate query types supported by the MVP."""

    COUNT_CATEGORY = "COUNT_CATEGORY"
    MEAN = "MEAN"
    HISTOGRAM = "HISTOGRAM"


class CountCategoryRequest(QueryContractModel):
    """Request to count rows in one declared public category."""

    query_type: Literal[QueryType.COUNT_CATEGORY] = QueryType.COUNT_CATEGORY
    field: NonEmptyString
    category: NonEmptyString
    epsilon: Epsilon


class MeanRequest(QueryContractModel):
    """Request for a bounded numeric mean."""

    query_type: Literal[QueryType.MEAN] = QueryType.MEAN
    field: NonEmptyString
    epsilon: Epsilon


class HistogramRequest(QueryContractModel):
    """Request for a histogram over a field's declared public partition."""

    query_type: Literal[QueryType.HISTOGRAM] = QueryType.HISTOGRAM
    field: NonEmptyString
    epsilon: Epsilon


QueryRequest = Annotated[
    CountCategoryRequest | MeanRequest | HistogramRequest,
    Field(discriminator="query_type"),
]
