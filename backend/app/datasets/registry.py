"""Trusted in-memory storage for datasets and their public configuration."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

from app.datasets.models import (
    CategoricalFieldSchema,
    DatasetMetadata,
    DatasetSchema,
    NumericFieldSchema,
    NumericValueType,
)
from app.errors import PrivacyModelConfigurationError, UnknownDatasetError

RecordValue: TypeAlias = int | float | str
DatasetRecord: TypeAlias = Mapping[str, RecordValue]


@dataclass(frozen=True, slots=True)
class RegisteredDataset:
    """Public metadata paired with records available only to trusted code."""

    metadata: DatasetMetadata
    records: tuple[DatasetRecord, ...]


class DatasetRegistry:
    """Read-only registry separating public metadata from private records."""

    def __init__(self, datasets: Iterable[RegisteredDataset]) -> None:
        registered: dict[str, RegisteredDataset] = {}
        for dataset in datasets:
            dataset_id = dataset.metadata.dataset_id
            if dataset_id in registered:
                raise PrivacyModelConfigurationError(
                    "Dataset identifiers must be unique.",
                    details={"dataset_id": dataset_id},
                )
            self._validate_dataset(dataset)
            frozen_records = tuple(
                MappingProxyType(dict(record)) for record in dataset.records
            )
            registered[dataset_id] = RegisteredDataset(
                metadata=dataset.metadata,
                records=frozen_records,
            )
        self._datasets: Mapping[str, RegisteredDataset] = MappingProxyType(
            registered
        )

    def list_metadata(self) -> tuple[DatasetMetadata, ...]:
        """Return public metadata for every registered dataset."""
        return tuple(dataset.metadata for dataset in self._datasets.values())

    def get_schema(self, dataset_id: str) -> DatasetSchema:
        """Return the public schema for a registered dataset."""
        return self._get_dataset(dataset_id).metadata.dataset_schema

    def get_records(self, dataset_id: str) -> tuple[DatasetRecord, ...]:
        """Return read-only records for trusted server-side callers only."""
        return self._get_dataset(dataset_id).records

    def _get_dataset(self, dataset_id: str) -> RegisteredDataset:
        try:
            return self._datasets[dataset_id]
        except KeyError as error:
            raise UnknownDatasetError(dataset_id) from error

    @classmethod
    def _validate_dataset(cls, dataset: RegisteredDataset) -> None:
        metadata = dataset.metadata
        if len(dataset.records) != metadata.row_count:
            cls._configuration_error(metadata.dataset_id)

        fields = {field.name: field for field in metadata.dataset_schema.fields}
        expected_names = set(fields)
        for record in dataset.records:
            if set(record) != expected_names:
                cls._configuration_error(metadata.dataset_id)
            for field_name, field in fields.items():
                value = record[field_name]
                if isinstance(field, NumericFieldSchema):
                    cls._validate_numeric_value(metadata.dataset_id, field, value)
                elif isinstance(field, CategoricalFieldSchema):
                    if type(value) is not str or value not in field.categories:
                        cls._configuration_error(metadata.dataset_id, field.name)

    @classmethod
    def _validate_numeric_value(
        cls,
        dataset_id: str,
        field: NumericFieldSchema,
        value: RecordValue,
    ) -> None:
        expected_type = (
            int if field.value_type is NumericValueType.INTEGER else float
        )
        if type(value) is not expected_type:
            cls._configuration_error(dataset_id, field.name)
        if not field.lower_bound <= value <= field.upper_bound:
            cls._configuration_error(dataset_id, field.name)

    @staticmethod
    def _configuration_error(dataset_id: str, field: str | None = None) -> None:
        details = {"dataset_id": dataset_id}
        if field is not None:
            details["field"] = field
        raise PrivacyModelConfigurationError(
            "Dataset records do not match public configuration.",
            details=details,
        )
