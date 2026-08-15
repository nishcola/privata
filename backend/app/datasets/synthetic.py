"""Deterministic built-in synthetic datasets."""

import random

from app.datasets.models import (
    CategoricalFieldSchema,
    DatasetMetadata,
    DatasetSchema,
    NumericFieldSchema,
    NumericHistogramBins,
    NumericValueType,
)
from app.datasets.registry import DatasetRecord, DatasetRegistry, RegisteredDataset

SYNTHETIC_WORKFORCE_DATASET_ID = "synthetic-workforce"
SYNTHETIC_WORKFORCE_SEED = 20260815
SYNTHETIC_WORKFORCE_ROW_COUNT = 500
SYNTHETIC_WORKFORCE_DEPARTMENTS = (
    "Engineering",
    "Sales",
    "Operations",
    "Finance",
    "People",
)

SYNTHETIC_WORKFORCE_SCHEMA = DatasetSchema(
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
            histogram_bins=NumericHistogramBins(
                edges=(20_000, 50_000, 80_000, 110_000, 140_000, 170_000, 200_000)
            ),
        ),
        CategoricalFieldSchema(
            name="department",
            categories=SYNTHETIC_WORKFORCE_DEPARTMENTS,
        ),
    )
)


def generate_synthetic_workforce(
    *, seed: int, row_count: int
) -> tuple[DatasetRecord, ...]:
    """Generate bounded workforce records from an explicit local seed."""
    generator = random.Random(seed)
    return tuple(
        {
            "age": generator.randint(18, 80),
            "annual_income": generator.randint(20_000, 200_000),
            "department": generator.choice(SYNTHETIC_WORKFORCE_DEPARTMENTS),
        }
        for _ in range(row_count)
    )


def create_builtin_registry() -> DatasetRegistry:
    """Create the registry containing Privata's safe synthetic demo dataset."""
    metadata = DatasetMetadata(
        dataset_id=SYNTHETIC_WORKFORCE_DATASET_ID,
        name="Synthetic Workforce",
        row_count=SYNTHETIC_WORKFORCE_ROW_COUNT,
        safe_for_demo=True,
        schema=SYNTHETIC_WORKFORCE_SCHEMA,
    )
    records = generate_synthetic_workforce(
        seed=SYNTHETIC_WORKFORCE_SEED,
        row_count=SYNTHETIC_WORKFORCE_ROW_COUNT,
    )
    return DatasetRegistry((RegisteredDataset(metadata=metadata, records=records),))
