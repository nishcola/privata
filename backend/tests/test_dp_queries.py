"""Behavioral tests for framework-independent private query execution."""

from importlib import import_module

import pytest

from app.datasets.models import (
    CategoricalFieldSchema,
    DatasetSchema,
    NumericFieldSchema,
    NumericHistogramBins,
    NumericValueType,
)
from app.dp.models import MechanismName
from app.dp.queries.models import (
    CountCategoryRequest,
    HistogramRequest,
    MeanRequest,
)
from app.errors import InvalidQueryError, PrivacyModelConfigurationError

queries = import_module("app.dp.queries")
def schema() -> DatasetSchema:
    return DatasetSchema(
        fields=(
            CategoricalFieldSchema(name="group", categories=("b", "a", "c")),
            NumericFieldSchema(
                name="value",
                value_type=NumericValueType.FLOAT,
                lower_bound=0.0,
                upper_bound=10.0,
                histogram_bins=NumericHistogramBins(edges=(0.0, 5.0, 10.0)),
            ),
            NumericFieldSchema(
                name="unbinned",
                value_type=NumericValueType.FLOAT,
                lower_bound=0.0,
                upper_bound=10.0,
            ),
        )
    )


def zero_noise_sampler() -> float:
    return 0.5


def test_count_category_returns_true_and_zero_noise_release_metadata() -> None:
    execute = queries.execute_count_category

    result = execute(
        request=CountCategoryRequest(field="group", category="a", epsilon=0.5),
        schema=schema(),
        records=(
            {"group": "a", "value": 1.0, "unbinned": 1.0},
            {"group": "b", "value": 2.0, "unbinned": 2.0},
            {"group": "a", "value": 3.0, "unbinned": 3.0},
        ),
        uniform_sampler=zero_noise_sampler,
    )

    assert result.noisy_result == result.true_result == 2
    assert result.sensitivity == 1.0
    assert result.mechanism is MechanismName.LAPLACE
    assert result.scale == 2.0


def test_count_category_rejects_category_outside_declared_domain() -> None:
    execute = queries.execute_count_category

    with pytest.raises(InvalidQueryError):
        execute(
            request=CountCategoryRequest(
                field="group", category="unknown", epsilon=1.0
            ),
            schema=schema(),
            records=(),
        )


def test_count_category_rejects_non_categorical_field() -> None:
    execute = queries.execute_count_category

    with pytest.raises(InvalidQueryError):
        execute(
            request=CountCategoryRequest(field="value", category="a", epsilon=1.0),
            schema=schema(),
            records=(),
        )


def test_mean_clips_every_value_before_averaging() -> None:
    execute = queries.execute_mean

    result = execute(
        request=MeanRequest(field="value", epsilon=0.5),
        schema=schema(),
        records=(
            {"group": "a", "value": -5.0, "unbinned": 0.0},
            {"group": "b", "value": 5.0, "unbinned": 0.0},
            {"group": "c", "value": 25.0, "unbinned": 0.0},
        ),
        uniform_sampler=zero_noise_sampler,
    )

    assert result.noisy_result == result.true_result == 5.0
    assert result.sensitivity == pytest.approx(10.0 / 3.0)
    assert result.scale == pytest.approx(20.0 / 3.0)


def test_mean_rejects_empty_records() -> None:
    execute = queries.execute_mean

    with pytest.raises(ValueError, match="positive integer"):
        execute(
            request=MeanRequest(field="value", epsilon=1.0),
            schema=schema(),
            records=(),
        )


def test_mean_rejects_non_numeric_field() -> None:
    execute = queries.execute_mean

    with pytest.raises(InvalidQueryError):
        execute(
            request=MeanRequest(field="group", epsilon=1.0),
            schema=schema(),
            records=(),
        )


def test_categorical_histogram_uses_declared_category_order() -> None:
    execute = queries.execute_histogram

    result = execute(
        request=HistogramRequest(field="group", epsilon=2.0),
        schema=schema(),
        records=(
            {"group": "a", "value": 0.0, "unbinned": 0.0},
            {"group": "b", "value": 0.0, "unbinned": 0.0},
            {"group": "a", "value": 0.0, "unbinned": 0.0},
        ),
        uniform_sampler=zero_noise_sampler,
    )

    assert result.true_result == (1, 2, 0)
    assert result.noisy_result == (1.0, 2.0, 0.0)
    assert result.sensitivity == 2.0
    assert result.mechanism is MechanismName.LAPLACE
    assert result.scale == 1.0


def test_numeric_histogram_assigns_boundary_values_once() -> None:
    execute = queries.execute_histogram

    result = execute(
        request=HistogramRequest(field="value", epsilon=1.0),
        schema=schema(),
        records=(
            {"group": "a", "value": 0.0, "unbinned": 0.0},
            {"group": "b", "value": 4.999, "unbinned": 0.0},
            {"group": "c", "value": 5.0, "unbinned": 0.0},
            {"group": "a", "value": 10.0, "unbinned": 0.0},
        ),
        uniform_sampler=zero_noise_sampler,
    )

    assert result.true_result == (2, 2)
    assert result.noisy_result == (2.0, 2.0)
    assert result.scale == 2.0


def test_numeric_histogram_clips_values_before_binning() -> None:
    execute = queries.execute_histogram

    result = execute(
        request=HistogramRequest(field="value", epsilon=1.0),
        schema=schema(),
        records=(
            {"group": "a", "value": -1.0, "unbinned": 0.0},
            {"group": "b", "value": 11.0, "unbinned": 0.0},
        ),
        uniform_sampler=zero_noise_sampler,
    )

    assert result.true_result == (1, 1)
    assert result.noisy_result == (1.0, 1.0)


def test_numeric_histogram_rejects_field_without_public_bins() -> None:
    execute = queries.execute_histogram

    with pytest.raises(InvalidQueryError):
        execute(
            request=HistogramRequest(field="unbinned", epsilon=1.0),
            schema=schema(),
            records=(),
        )


def test_numeric_histogram_rejects_public_bins_that_do_not_cover_a_value() -> None:
    execute = queries.execute_histogram
    incomplete_schema = DatasetSchema(
        fields=(
            NumericFieldSchema(
                name="value",
                value_type=NumericValueType.FLOAT,
                lower_bound=0.0,
                upper_bound=10.0,
                histogram_bins=NumericHistogramBins(edges=(0.0, 5.0)),
            ),
        )
    )

    with pytest.raises(PrivacyModelConfigurationError):
        execute(
            request=HistogramRequest(field="value", epsilon=1.0),
            schema=incomplete_schema,
            records=({"value": 10.0},),
        )


def test_histogram_samples_each_bin_and_preserves_negative_counts() -> None:
    execute = queries.execute_histogram
    samples = iter((0.25, 0.5, 0.75))
    calls = 0

    def sampler() -> float:
        nonlocal calls
        calls += 1
        return next(samples)

    result = execute(
        request=HistogramRequest(field="group", epsilon=1.0),
        schema=schema(),
        records=({"group": "a", "value": 0.0, "unbinned": 0.0},),
        uniform_sampler=sampler,
    )

    assert calls == 3
    assert result.true_result == (0, 1, 0)
    assert result.noisy_result[0] < 0.0
    assert result.scale == 2.0
