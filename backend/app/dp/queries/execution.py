"""Framework-independent implementations of Privata's supported DP queries."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.datasets.models import (
    CategoricalFieldSchema,
    DatasetSchema,
    FieldSchema,
    NumericFieldSchema,
)
from app.datasets.registry import DatasetRecord
from app.dp.clipping import clip_numeric_value
from app.dp.mechanisms.laplace import UniformSampler, laplace_release, laplace_scale
from app.dp.models import MechanismName
from app.dp.queries.models import (
    CountCategoryRequest,
    HistogramRequest,
    MeanRequest,
    QueryRequest,
)
from app.dp.sensitivity import (
    count_category_sensitivity,
    histogram_sensitivity,
    mean_sensitivity,
)
from app.errors import InvalidQueryError, PrivacyModelConfigurationError


@dataclass(frozen=True, slots=True)
class ScalarQueryResult:
    """Trusted scalar aggregate and its private Laplace release."""

    noisy_result: float
    true_result: int | float
    sensitivity: float
    mechanism: MechanismName
    scale: float


@dataclass(frozen=True, slots=True)
class HistogramQueryResult:
    """Trusted histogram counts and their independent private releases."""

    noisy_result: tuple[float, ...]
    true_result: tuple[int, ...]
    sensitivity: float
    mechanism: MechanismName
    scale: float


def validate_query_request(*, request: QueryRequest, schema: DatasetSchema) -> None:
    """Validate a typed query against public schema without releasing data."""
    if isinstance(request, CountCategoryRequest):
        field = _categorical_field(schema, request.field)
        if request.category not in field.categories:
            raise InvalidQueryError(
                "Category is not declared for the field.",
                details={"field": request.field, "category": request.category},
            )
        return
    if isinstance(request, MeanRequest):
        _numeric_field(schema, request.field)
        return
    if isinstance(request, HistogramRequest):
        field = _field(schema, request.field)
        if isinstance(field, NumericFieldSchema) and field.histogram_bins is None:
            raise InvalidQueryError(
                "Numeric histogram requires declared public bin edges.",
                details={"field": request.field},
            )
        return
    raise TypeError("request must be a supported QueryRequest")


def execute_count_category(
    *,
    request: CountCategoryRequest,
    schema: DatasetSchema,
    records: Sequence[DatasetRecord],
    uniform_sampler: UniformSampler | None = None,
) -> ScalarQueryResult:
    """Release a noisy count for one declared categorical value."""
    validate_query_request(request=request, schema=schema)
    field = _categorical_field(schema, request.field)

    true_result = sum(record[field.name] == request.category for record in records)
    sensitivity = count_category_sensitivity()
    scale = laplace_scale(sensitivity=sensitivity, epsilon=request.epsilon)
    noisy_result = laplace_release(
        value=true_result,
        sensitivity=sensitivity,
        epsilon=request.epsilon,
        uniform_sampler=uniform_sampler,
    )
    return ScalarQueryResult(
        noisy_result=noisy_result,
        true_result=true_result,
        sensitivity=sensitivity,
        mechanism=MechanismName.LAPLACE,
        scale=scale,
    )


def execute_mean(
    *,
    request: MeanRequest,
    schema: DatasetSchema,
    records: Sequence[DatasetRecord],
    uniform_sampler: UniformSampler | None = None,
) -> ScalarQueryResult:
    """Release a noisy bounded mean after clipping every numeric value."""
    validate_query_request(request=request, schema=schema)
    field = _numeric_field(schema, request.field)
    n = len(records)
    sensitivity = mean_sensitivity(
        lower_bound=field.lower_bound,
        upper_bound=field.upper_bound,
        n=n,
    )
    true_result = sum(
        clip_numeric_value(
            record[field.name],
            lower_bound=field.lower_bound,
            upper_bound=field.upper_bound,
        )
        for record in records
    ) / n
    scale = laplace_scale(sensitivity=sensitivity, epsilon=request.epsilon)
    noisy_result = laplace_release(
        value=true_result,
        sensitivity=sensitivity,
        epsilon=request.epsilon,
        uniform_sampler=uniform_sampler,
    )
    return ScalarQueryResult(
        noisy_result=noisy_result,
        true_result=true_result,
        sensitivity=sensitivity,
        mechanism=MechanismName.LAPLACE,
        scale=scale,
    )


def execute_histogram(
    *,
    request: HistogramRequest,
    schema: DatasetSchema,
    records: Sequence[DatasetRecord],
    uniform_sampler: UniformSampler | None = None,
) -> HistogramQueryResult:
    """Release independently noised counts across a declared public partition."""
    validate_query_request(request=request, schema=schema)
    field = _field(schema, request.field)
    if isinstance(field, CategoricalFieldSchema):
        true_result = _categorical_histogram(field, records)
    else:
        true_result = _numeric_histogram(field, records)

    sensitivity = histogram_sensitivity()
    scale = laplace_scale(sensitivity=sensitivity, epsilon=request.epsilon)
    noisy_result = tuple(
        laplace_release(
            value=count,
            sensitivity=sensitivity,
            epsilon=request.epsilon,
            uniform_sampler=uniform_sampler,
        )
        for count in true_result
    )
    return HistogramQueryResult(
        noisy_result=noisy_result,
        true_result=true_result,
        sensitivity=sensitivity,
        mechanism=MechanismName.LAPLACE,
        scale=scale,
    )


def _field(schema: DatasetSchema, field_name: str) -> FieldSchema:
    for field in schema.fields:
        if field.name == field_name:
            return field
    raise InvalidQueryError("Field is not declared.", details={"field": field_name})


def _categorical_field(
    schema: DatasetSchema, field_name: str
) -> CategoricalFieldSchema:
    field = _field(schema, field_name)
    if not isinstance(field, CategoricalFieldSchema):
        raise InvalidQueryError(
            "Query requires a categorical field.", details={"field": field_name}
        )
    return field


def _numeric_field(schema: DatasetSchema, field_name: str) -> NumericFieldSchema:
    field = _field(schema, field_name)
    if not isinstance(field, NumericFieldSchema):
        raise InvalidQueryError(
            "Query requires a numeric field.", details={"field": field_name}
        )
    return field


def _categorical_histogram(
    field: CategoricalFieldSchema, records: Sequence[DatasetRecord]
) -> tuple[int, ...]:
    index_by_category = {
        category: index for index, category in enumerate(field.categories)
    }
    counts = [0] * len(field.categories)
    for record in records:
        try:
            index = index_by_category[record[field.name]]
        except KeyError as error:
            raise PrivacyModelConfigurationError(
                "Dataset records do not match public configuration.",
                details={"field": field.name},
            ) from error
        counts[index] += 1
    return tuple(counts)


def _numeric_histogram(
    field: NumericFieldSchema, records: Sequence[DatasetRecord]
) -> tuple[int, ...]:
    if field.histogram_bins is None:
        raise InvalidQueryError(
            "Numeric histogram requires declared public bin edges.",
            details={"field": field.name},
        )

    edges = field.histogram_bins.edges
    counts = [0] * (len(edges) - 1)
    for record in records:
        value = clip_numeric_value(
            record[field.name],
            lower_bound=field.lower_bound,
            upper_bound=field.upper_bound,
        )
        index = _numeric_bin_index(value, edges)
        if index is None:
            raise PrivacyModelConfigurationError(
                "Numeric histogram bins do not cover the declared values.",
                details={"field": field.name},
            )
        counts[index] += 1
    return tuple(counts)


def _numeric_bin_index(value: float, edges: tuple[float, ...]) -> int | None:
    for index, upper_edge in enumerate(edges[1:]):
        if value < upper_edge:
            return index
    if value == edges[-1]:
        return len(edges) - 2
    return None
