"""Metadata contracts shared by differential privacy releases."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.dp.queries.models import QueryType

NonEmptyString = Annotated[str, Field(strict=True, min_length=1)]
PositiveFiniteFloat = Annotated[
    float,
    Field(strict=True, gt=0, allow_inf_nan=False),
]
NonNegativeFiniteFloat = Annotated[
    float,
    Field(strict=True, ge=0, allow_inf_nan=False),
]


class MechanismName(StrEnum):
    """Mechanisms supported by release metadata."""

    LAPLACE = "laplace"


class QueryResultMetadata(BaseModel):
    """Public metadata describing a successful private release."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query_id: NonEmptyString
    query_type: QueryType
    dataset_id: NonEmptyString
    epsilon_charged: PositiveFiniteFloat
    epsilon_remaining: NonNegativeFiniteFloat
    sensitivity: NonNegativeFiniteFloat
    mechanism_name: MechanismName = MechanismName.LAPLACE
    mechanism_scale: NonNegativeFiniteFloat
    timestamp: datetime
