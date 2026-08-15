from importlib import import_module

import pytest
from pydantic import ValidationError

from app.datasets.models import (
    CategoricalFieldSchema,
    DatasetMetadata,
    DatasetSchema,
    NumericFieldSchema,
    NumericHistogramBins,
    NumericValueType,
)


def numeric_field(**changes: object) -> NumericFieldSchema:
    values: dict[str, object] = {
        "name": "age",
        "value_type": NumericValueType.INTEGER,
        "lower_bound": 0,
        "upper_bound": 120,
    }
    values.update(changes)
    return NumericFieldSchema(**values)


def test_dataset_models_expose_phase_one_contracts() -> None:
    models = import_module("app.datasets.models")

    expected_names = {
        "CategoricalFieldSchema",
        "DatasetMetadata",
        "DatasetSchema",
        "NumericFieldSchema",
        "NumericHistogramBins",
        "NumericValueType",
    }

    assert expected_names <= set(dir(models))


@pytest.mark.parametrize(
    ("lower_bound", "upper_bound"),
    [
        (2.0, 1.0),
        (float("nan"), 1.0),
        (0.0, float("nan")),
        (float("inf"), 1.0),
        (0.0, float("inf")),
        (float("-inf"), 1.0),
        (0.0, float("-inf")),
    ],
)
def test_numeric_field_rejects_invalid_bounds(
    lower_bound: float, upper_bound: float
) -> None:
    with pytest.raises(ValidationError):
        numeric_field(lower_bound=lower_bound, upper_bound=upper_bound)


def test_numeric_field_accepts_equal_bounds() -> None:
    field = numeric_field(lower_bound=4.0, upper_bound=4.0)

    assert field.lower_bound == field.upper_bound == 4.0


@pytest.mark.parametrize("invalid_bound", [True, "0"])
def test_numeric_field_rejects_coercive_bounds(invalid_bound: object) -> None:
    with pytest.raises(ValidationError):
        numeric_field(lower_bound=invalid_bound)


@pytest.mark.parametrize("categories", [(), ("a", "a"), ("",)])
def test_categorical_field_rejects_invalid_categories(
    categories: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError):
        CategoricalFieldSchema(name="group", categories=categories)


@pytest.mark.parametrize(
    "edges",
    [
        (),
        (0.0,),
        (0.0, 0.0),
        (1.0, 0.0),
        (0.0, float("nan")),
        (0.0, float("inf")),
        (float("-inf"), 0.0),
    ],
)
def test_numeric_histogram_rejects_invalid_edges(edges: tuple[float, ...]) -> None:
    with pytest.raises(ValidationError):
        NumericHistogramBins(edges=edges)


@pytest.mark.parametrize("row_count", [0, -1])
def test_dataset_metadata_requires_positive_row_count(row_count: int) -> None:
    with pytest.raises(ValidationError):
        DatasetMetadata(
            dataset_id="demo",
            name="Demo",
            row_count=row_count,
            safe_for_demo=True,
            schema=DatasetSchema(fields=(numeric_field(),)),
        )


@pytest.mark.parametrize("row_count", [True, "1", 1.0])
def test_dataset_metadata_rejects_coercive_row_counts(row_count: object) -> None:
    with pytest.raises(ValidationError):
        DatasetMetadata(
            dataset_id="demo",
            name="Demo",
            row_count=row_count,
            safe_for_demo=True,
            schema=DatasetSchema(fields=(numeric_field(),)),
        )


@pytest.mark.parametrize("safe_for_demo", [1, "true", "yes"])
def test_dataset_metadata_requires_a_boolean_demo_flag(
    safe_for_demo: object,
) -> None:
    with pytest.raises(ValidationError):
        DatasetMetadata(
            dataset_id="demo",
            name="Demo",
            row_count=1,
            safe_for_demo=safe_for_demo,
            schema=DatasetSchema(fields=(numeric_field(),)),
        )


def test_dataset_schema_rejects_duplicate_field_names() -> None:
    with pytest.raises(ValidationError):
        DatasetSchema(
            fields=(
                numeric_field(name="value"),
                CategoricalFieldSchema(name="value", categories=("a", "b")),
            )
        )


def test_dataset_schema_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError):
        DatasetSchema(fields=())


@pytest.mark.parametrize(("dataset_id", "name"), [("", "Demo"), ("demo", "")])
def test_dataset_metadata_requires_nonempty_identifiers(
    dataset_id: str, name: str
) -> None:
    with pytest.raises(ValidationError):
        DatasetMetadata(
            dataset_id=dataset_id,
            name=name,
            row_count=1,
            safe_for_demo=True,
            schema=DatasetSchema(fields=(numeric_field(),)),
        )


def test_dataset_contracts_serialize_public_metadata_without_records() -> None:
    metadata = DatasetMetadata(
        dataset_id="demo",
        name="Demo dataset",
        row_count=2,
        safe_for_demo=True,
        schema=DatasetSchema(
            fields=(
                numeric_field(
                    histogram_bins=NumericHistogramBins(edges=(0, 60, 120))
                ),
                CategoricalFieldSchema(name="group", categories=("a", "b")),
            )
        ),
    )

    assert metadata.model_dump(mode="json") == {
        "dataset_id": "demo",
        "name": "Demo dataset",
        "row_count": 2,
        "safe_for_demo": True,
        "schema": {
            "fields": [
                {
                    "name": "age",
                    "field_type": "numeric",
                    "value_type": "integer",
                    "lower_bound": 0.0,
                    "upper_bound": 120.0,
                    "histogram_bins": {"edges": [0.0, 60.0, 120.0]},
                },
                {
                    "name": "group",
                    "field_type": "categorical",
                    "categories": ["a", "b"],
                },
            ]
        },
    }
    assert "records" not in DatasetMetadata.model_fields


def test_dataset_contracts_are_frozen_and_forbid_extra_fields() -> None:
    field = numeric_field()

    with pytest.raises(ValidationError):
        field.name = "changed"
    with pytest.raises(ValidationError):
        NumericFieldSchema(
            name="age",
            value_type="integer",
            lower_bound=0,
            upper_bound=120,
            private_value=10,
        )
