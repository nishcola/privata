"""Public dataset metadata and schema contracts."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

FiniteFloat = Annotated[float, Field(strict=True, allow_inf_nan=False)]
NonEmptyString = Annotated[str, Field(strict=True, min_length=1)]
PositiveInteger = Annotated[int, Field(strict=True, gt=0)]
StrictBoolean = Annotated[bool, Field(strict=True)]


class ContractModel(BaseModel):
    """Base configuration shared by dataset contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


class NumericValueType(StrEnum):
    """Declared representation of values in a numeric field."""

    INTEGER = "integer"
    FLOAT = "float"


class NumericHistogramBins(ContractModel):
    """Public bin edges for a numeric histogram."""

    edges: Annotated[tuple[FiniteFloat, ...], Field(min_length=2)]

    @model_validator(mode="after")
    def validate_strictly_increasing(self) -> Self:
        if any(
            left >= right
            for left, right in zip(self.edges, self.edges[1:], strict=False)
        ):
            raise ValueError("histogram edges must be strictly increasing")
        return self


class NumericFieldSchema(ContractModel):
    """Public schema for a bounded numeric field."""

    name: NonEmptyString
    field_type: Literal["numeric"] = "numeric"
    value_type: NumericValueType
    lower_bound: FiniteFloat
    upper_bound: FiniteFloat
    histogram_bins: NumericHistogramBins | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if self.upper_bound < self.lower_bound:
            raise ValueError("upper bound must be greater than or equal to lower bound")
        return self


class CategoricalFieldSchema(ContractModel):
    """Public schema for a categorical field."""

    name: NonEmptyString
    field_type: Literal["categorical"] = "categorical"
    categories: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_unique_categories(self) -> Self:
        if len(set(self.categories)) != len(self.categories):
            raise ValueError("categories must be unique")
        return self


FieldSchema = Annotated[
    NumericFieldSchema | CategoricalFieldSchema,
    Field(discriminator="field_type"),
]


class DatasetSchema(ContractModel):
    """Public fields declared for a dataset."""

    fields: Annotated[tuple[FieldSchema, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_unique_field_names(self) -> Self:
        names = [field.name for field in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("field names must be unique")
        return self


class DatasetMetadata(ContractModel):
    """Public dataset metadata. Raw records are deliberately excluded."""

    dataset_id: NonEmptyString
    name: NonEmptyString
    row_count: PositiveInteger
    safe_for_demo: StrictBoolean
    dataset_schema: DatasetSchema = Field(alias="schema", serialization_alias="schema")
