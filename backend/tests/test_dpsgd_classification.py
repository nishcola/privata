"""Tests for the isolated DP-SGD research experiment."""

import json
import sys
import warnings
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))


def test_synthetic_dataset_is_deterministic_bounded_and_has_both_labels() -> None:
    """The research dataset is synthetic, repeatable, and has a learnable target."""
    from experiments.dpsgd_classification import (
        SYNTHETIC_DPSGD_ROW_COUNT,
        generate_synthetic_retention_dataset,
    )

    first = generate_synthetic_retention_dataset(seed=20260819)
    second = generate_synthetic_retention_dataset(seed=20260819)

    assert first == second
    assert len(first) == SYNTHETIC_DPSGD_ROW_COUNT == 10_000
    assert {record.retention_outcome for record in first} == {0, 1}
    assert all(18 <= record.age <= 80 for record in first)
    assert all(20_000 <= record.annual_income <= 200_000 for record in first)


def test_public_feature_encoding_uses_fixed_public_split() -> None:
    """Features use only declared bounds and domains, then split 8,000/2,000."""
    from experiments.dpsgd_classification import (
        DEPARTMENTS,
        prepare_dataset,
    )

    prepared = prepare_dataset(seed=20260819)

    assert prepared.train_features.shape == (8_000, 2 + len(DEPARTMENTS))
    assert prepared.test_features.shape == (2_000, 2 + len(DEPARTMENTS))
    assert prepared.train_labels.shape == (8_000,)
    assert prepared.test_labels.shape == (2_000,)
    assert float(prepared.train_features.min()) >= 0.0
    assert float(prepared.train_features.max()) <= 1.0


def test_dpsgd_run_writes_safe_privacy_and_accuracy_artifacts(tmp_path: Path) -> None:
    """A small private run records its separate privacy model without raw data."""
    pytest.importorskip("opacus")
    from experiments.dpsgd_classification import run

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        summary = run(
            output_dir=tmp_path,
            target_epsilons=(8.0,),
            epochs=1,
            runs=1,
            dataset_seed=20260819,
            training_seed=20260820,
        )

    metadata = summary["metadata"]
    result = summary["private_results"][0]
    serialized = json.dumps(summary)
    assert metadata["privacy_model"] == "DP-SGD sample-level add/remove"
    assert metadata["mechanism"] == "Gaussian DP-SGD"
    assert metadata["accountant"] == "PRV"
    assert metadata["delta"] == pytest.approx(1e-5)
    assert metadata["clipping_norm"] == pytest.approx(1.0)
    assert metadata["sampling_rate"] == pytest.approx(256 / 8_000)
    assert result["noise_multiplier"] > 0.0
    assert result["actual_epsilon_mean"] <= result["target_epsilon"] + 1e-6
    assert (tmp_path / "dpsgd_classification.json").is_file()
    assert (tmp_path / "dpsgd_classification.png").is_file()
    assert all(
        term not in serialized for term in ("raw_records", "predictions", "gradients")
    )
    assert all(
        "Full backward hook is firing" not in str(warning.message)
        for warning in captured_warnings
    )


def test_application_dp_engine_remains_free_of_training_libraries() -> None:
    """The offline research stack must not leak into the Laplace query engine."""
    core_directory = REPOSITORY_ROOT / "backend" / "app" / "dp"

    for source_path in core_directory.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8").lower()
        assert "opacus" not in source
        assert "torch" not in source


@pytest.mark.parametrize("target_epsilon", (float("nan"), float("inf"), float("-inf")))
def test_dpsgd_run_rejects_non_finite_privacy_targets(
    tmp_path: Path, target_epsilon: float
) -> None:
    """A reported privacy target must be a finite, positive number."""
    from experiments.dpsgd_classification import run

    with pytest.raises(ValueError, match="finite positive"):
        run(
            output_dir=tmp_path,
            target_epsilons=(target_epsilon,),
            epochs=1,
            runs=1,
        )
