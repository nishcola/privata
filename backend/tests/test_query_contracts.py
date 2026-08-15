from collections.abc import Callable
from datetime import UTC, datetime
from importlib import import_module
from typing import Any

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.dp.models import MechanismName, QueryResultMetadata
from app.dp.queries.models import (
    CountCategoryRequest,
    HistogramRequest,
    MeanRequest,
    QueryRequest,
    QueryType,
)
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

REQUEST_CASES: tuple[tuple[type[BaseModel], dict[str, str]], ...] = (
    (CountCategoryRequest, {"field": "group", "category": "a"}),
    (MeanRequest, {"field": "age"}),
    (HistogramRequest, {"field": "age"}),
)


def test_query_modules_expose_phase_one_contracts() -> None:
    query_models = import_module("app.dp.queries.models")
    result_models = import_module("app.dp.models")
    errors = import_module("app.errors")

    assert {
        "CountCategoryRequest",
        "HistogramRequest",
        "MeanRequest",
        "QueryRequest",
        "QueryType",
    } <= set(dir(query_models))
    assert {"MechanismName", "QueryResultMetadata"} <= set(dir(result_models))
    assert {
        "BudgetExceededError",
        "DomainError",
        "ErrorCode",
        "InvalidEpsilonError",
        "InvalidQueryError",
        "PrivacyModelConfigurationError",
        "UnknownDatasetError",
        "UnknownSessionError",
    } <= set(dir(errors))


@pytest.mark.parametrize("request_model,request_fields", REQUEST_CASES)
@pytest.mark.parametrize(
    "epsilon",
    [0.0, -1.0, float("nan"), float("inf"), float("-inf"), 10.0001],
)
def test_query_requests_reject_invalid_epsilon(
    request_model: type[BaseModel],
    request_fields: dict[str, str],
    epsilon: float,
) -> None:
    with pytest.raises(ValidationError):
        request_model(epsilon=epsilon, **request_fields)


@pytest.mark.parametrize("request_model,request_fields", REQUEST_CASES)
@pytest.mark.parametrize("epsilon", [True, "0.5"])
def test_query_requests_reject_coercive_epsilon(
    request_model: type[BaseModel],
    request_fields: dict[str, str],
    epsilon: object,
) -> None:
    with pytest.raises(ValidationError):
        request_model(epsilon=epsilon, **request_fields)


@pytest.mark.parametrize("epsilon", [10, 1e-12])
def test_query_requests_accept_positive_epsilon_boundaries(epsilon: float) -> None:
    request = MeanRequest(field="age", epsilon=epsilon)

    assert request.epsilon == epsilon


def test_query_request_discriminator_parses_each_supported_type() -> None:
    adapter = TypeAdapter(QueryRequest)

    count = adapter.validate_python(
        {
            "query_type": "COUNT_CATEGORY",
            "field": "group",
            "category": "a",
            "epsilon": 0.1,
        }
    )
    mean = adapter.validate_python(
        {"query_type": "MEAN", "field": "age", "epsilon": 0.25}
    )
    histogram = adapter.validate_python(
        {"query_type": "HISTOGRAM", "field": "age", "epsilon": 1.0}
    )

    assert isinstance(count, CountCategoryRequest)
    assert isinstance(mean, MeanRequest)
    assert isinstance(histogram, HistogramRequest)


def test_query_requests_require_nonempty_public_names() -> None:
    with pytest.raises(ValidationError):
        CountCategoryRequest(field="", category="a", epsilon=0.1)
    with pytest.raises(ValidationError):
        CountCategoryRequest(field="group", category="", epsilon=0.1)


def test_query_requests_are_frozen_and_forbid_extra_fields() -> None:
    request = MeanRequest(field="age", epsilon=0.1)

    with pytest.raises(ValidationError):
        request.field = "income"
    with pytest.raises(ValidationError):
        MeanRequest(field="age", epsilon=0.1, raw_records=[])


def result_metadata(**changes: Any) -> QueryResultMetadata:
    values: dict[str, Any] = {
        "query_id": "query-1",
        "query_type": QueryType.MEAN,
        "dataset_id": "demo",
        "epsilon_charged": 0.5,
        "epsilon_remaining": 1.5,
        "sensitivity": 0.12,
        "mechanism_name": MechanismName.LAPLACE,
        "mechanism_scale": 0.24,
        "timestamp": datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
    }
    values.update(changes)
    return QueryResultMetadata(**values)


def test_query_result_metadata_serializes_release_metadata_only() -> None:
    metadata = result_metadata()

    assert metadata.model_dump(mode="json") == {
        "query_id": "query-1",
        "query_type": "MEAN",
        "dataset_id": "demo",
        "epsilon_charged": 0.5,
        "epsilon_remaining": 1.5,
        "sensitivity": 0.12,
        "mechanism_name": "laplace",
        "mechanism_scale": 0.24,
        "timestamp": "2026-08-15T12:00:00Z",
    }
    assert "noisy_result" not in QueryResultMetadata.model_fields
    assert "true_result" not in QueryResultMetadata.model_fields


def test_query_result_metadata_is_frozen_and_forbids_extra_fields() -> None:
    metadata = result_metadata()

    with pytest.raises(ValidationError):
        metadata.dataset_id = "changed"
    with pytest.raises(ValidationError):
        result_metadata(raw_records=[])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("epsilon_charged", 0.0),
        ("epsilon_charged", -1.0),
        ("epsilon_charged", float("nan")),
        ("epsilon_charged", float("inf")),
        ("epsilon_remaining", -1.0),
        ("epsilon_remaining", float("nan")),
        ("epsilon_remaining", float("inf")),
        ("sensitivity", -1.0),
        ("sensitivity", float("nan")),
        ("sensitivity", float("inf")),
        ("mechanism_scale", -1.0),
        ("mechanism_scale", float("nan")),
        ("mechanism_scale", float("inf")),
        ("epsilon_charged", True),
        ("epsilon_remaining", "1.5"),
        ("sensitivity", True),
        ("mechanism_scale", "0.24"),
    ],
)
def test_query_result_metadata_rejects_invalid_numeric_metadata(
    field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        result_metadata(**{field: value})


def test_budget_exceeded_error_has_stable_safe_payload() -> None:
    error = BudgetExceededError(requested_epsilon=0.5, remaining_epsilon=0.25)

    assert error.code is ErrorCode.BUDGET_EXCEEDED
    assert str(error) == "Requested epsilon exceeds the remaining privacy budget."
    assert error.details == {
        "requested_epsilon": 0.5,
        "remaining_epsilon": 0.25,
    }


@pytest.mark.parametrize(
    ("error_factory", "code", "details"),
    [
        (
            lambda: InvalidQueryError(details={"field": "missing"}),
            ErrorCode.INVALID_QUERY,
            {"field": "missing"},
        ),
        (lambda: InvalidEpsilonError(), ErrorCode.INVALID_EPSILON, {}),
        (
            lambda: UnknownDatasetError("dataset-404"),
            ErrorCode.UNKNOWN_DATASET,
            {"dataset_id": "dataset-404"},
        ),
        (
            lambda: UnknownSessionError("session-404"),
            ErrorCode.UNKNOWN_SESSION,
            {"session_id": "session-404"},
        ),
        (
            lambda: PrivacyModelConfigurationError("Bounds are missing."),
            ErrorCode.PRIVACY_MODEL_CONFIGURATION_ERROR,
            {},
        ),
    ],
)
def test_domain_errors_have_stable_codes_and_details(
    error_factory: Callable[[], DomainError],
    code: ErrorCode,
    details: dict[str, object],
) -> None:
    error = error_factory()

    assert error.code is code
    assert error.details == details
