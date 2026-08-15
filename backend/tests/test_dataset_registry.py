from collections.abc import Mapping

import pytest

from app.datasets.models import (
    CategoricalFieldSchema,
    DatasetMetadata,
    DatasetSchema,
    NumericFieldSchema,
    NumericValueType,
)
from app.datasets.registry import DatasetRecord, DatasetRegistry, RegisteredDataset
from app.datasets.synthetic import (
    SYNTHETIC_WORKFORCE_ROW_COUNT,
    SYNTHETIC_WORKFORCE_SEED,
    create_builtin_registry,
    generate_synthetic_workforce,
)
from app.errors import ErrorCode, PrivacyModelConfigurationError, UnknownDatasetError


def test_same_seed_produces_same_synthetic_records() -> None:
    first = generate_synthetic_workforce(seed=31415, row_count=25)
    second = generate_synthetic_workforce(seed=31415, row_count=25)

    assert first == second


def test_builtin_records_match_declared_public_schema() -> None:
    registry = create_builtin_registry()
    metadata = registry.list_metadata()[0]
    records = registry.get_records(metadata.dataset_id)
    fields = {field.name: field for field in metadata.dataset_schema.fields}

    assert len(records) == SYNTHETIC_WORKFORCE_ROW_COUNT == metadata.row_count == 500
    assert SYNTHETIC_WORKFORCE_SEED == 20260815

    age = fields["age"]
    income = fields["annual_income"]
    department = fields["department"]
    assert isinstance(age, NumericFieldSchema)
    assert isinstance(income, NumericFieldSchema)
    assert isinstance(department, CategoricalFieldSchema)

    for record in records:
        assert set(record) == {"age", "annual_income", "department"}
        assert type(record["age"]) is int
        assert age.lower_bound <= record["age"] <= age.upper_bound
        assert type(record["annual_income"]) is int
        assert income.lower_bound <= record["annual_income"] <= income.upper_bound
        assert record["department"] in department.categories


def test_builtin_registry_returns_public_metadata_and_schema() -> None:
    registry = create_builtin_registry()

    metadata = registry.list_metadata()

    assert len(metadata) == 1
    assert metadata[0].dataset_id == "synthetic-workforce"
    assert metadata[0].name == "Synthetic Workforce"
    assert metadata[0].safe_for_demo is True
    assert registry.get_schema("synthetic-workforce") is metadata[0].dataset_schema
    assert "records" not in metadata[0].model_dump(mode="json")


def test_registry_records_are_read_only_copies() -> None:
    source_record: dict[str, int | float | str] = {
        "age": 30,
        "annual_income": 80_000,
        "department": "Engineering",
    }
    registry = DatasetRegistry((_registered_dataset(records=(source_record,)),))

    source_record["age"] = 31
    records = registry.get_records("test")

    assert records[0]["age"] == 30
    with pytest.raises(TypeError):
        records[0]["age"] = 32  # type: ignore[index]


def test_unknown_dataset_lookup_has_stable_domain_error() -> None:
    registry = create_builtin_registry()

    with pytest.raises(UnknownDatasetError) as raised:
        registry.get_schema("missing")

    assert raised.value.code is ErrorCode.UNKNOWN_DATASET
    assert raised.value.details == {"dataset_id": "missing"}


def test_registry_rejects_duplicate_dataset_ids() -> None:
    dataset = _registered_dataset()

    with pytest.raises(PrivacyModelConfigurationError):
        DatasetRegistry((dataset, dataset))


@pytest.mark.parametrize(
    "records",
    [
        (),
        ({"age": 30, "annual_income": 80_000},),
        ({"age": True, "annual_income": 80_000, "department": "Engineering"},),
        ({"age": 81, "annual_income": 80_000, "department": "Engineering"},),
        ({"age": 30, "annual_income": 80_000.5, "department": "Engineering"},),
        ({"age": 30, "annual_income": 80_000, "department": "Unknown"},),
    ],
)
def test_registry_rejects_records_that_violate_public_schema(
    records: tuple[Mapping[str, int | float | str], ...],
) -> None:
    with pytest.raises(PrivacyModelConfigurationError) as raised:
        DatasetRegistry((_registered_dataset(records=records),))

    assert "record" not in raised.value.details
    assert "value" not in raised.value.details


def _registered_dataset(
    *,
    records: tuple[Mapping[str, int | float | str], ...] | None = None,
) -> RegisteredDataset:
    schema = DatasetSchema(
        fields=(
            NumericFieldSchema(
                name="age",
                value_type=NumericValueType.INTEGER,
                lower_bound=18,
                upper_bound=80,
            ),
            NumericFieldSchema(
                name="annual_income",
                value_type=NumericValueType.INTEGER,
                lower_bound=20_000,
                upper_bound=200_000,
            ),
            CategoricalFieldSchema(
                name="department",
                categories=("Engineering", "Sales"),
            ),
        )
    )
    metadata = DatasetMetadata(
        dataset_id="test",
        name="Test",
        row_count=1,
        safe_for_demo=True,
        schema=schema,
    )
    default_records: tuple[DatasetRecord, ...] = (
        {"age": 30, "annual_income": 80_000, "department": "Engineering"},
    )
    selected_records = default_records if records is None else records
    return RegisteredDataset(metadata=metadata, records=selected_records)
