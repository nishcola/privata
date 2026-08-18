"""Illustrate output distributions for one fixed-size adjacent dataset pair."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.datasets.registry import DatasetRecord
from app.datasets.synthetic import (
    SYNTHETIC_WORKFORCE_ROW_COUNT,
    SYNTHETIC_WORKFORCE_SCHEMA,
    generate_synthetic_workforce,
)
from app.dp.queries import execute_count_category
from app.dp.queries.models import CountCategoryRequest
from experiments.common import (
    ensure_output_directory,
    experiment_sampler,
    metadata,
    stochastic_parser,
    write_summary,
)

EPSILON_GRID = (0.1, 0.5, 1.0, 2.0)
DEFAULT_TRIALS = 10_000
TARGET_CATEGORY = "Engineering"
REPLACEMENT_CATEGORY = "Sales"


def build_neighboring_datasets(
    *, dataset_seed: int
) -> tuple[tuple[DatasetRecord, ...], tuple[DatasetRecord, ...]]:
    """Build D and D' with equal size and exactly one changed record."""
    dataset = list(
        generate_synthetic_workforce(
            seed=dataset_seed, row_count=SYNTHETIC_WORKFORCE_ROW_COUNT
        )
    )
    changed_for_dataset = dict(dataset[0])
    changed_for_dataset["department"] = TARGET_CATEGORY
    changed_for_neighbor = dict(changed_for_dataset)
    changed_for_neighbor["department"] = REPLACEMENT_CATEGORY
    dataset[0] = changed_for_dataset
    neighbor = list(dataset)
    neighbor[0] = changed_for_neighbor
    return tuple(dataset), tuple(neighbor)


def run(
    *, output_dir: Path, trials: int, dataset_seed: int, mechanism_seed: int | None
) -> dict[str, Any]:
    """Create aggregate distribution artifacts for a fixed adjacent pair."""
    dataset, neighbor = build_neighboring_datasets(dataset_seed=dataset_seed)
    sampler = experiment_sampler(mechanism_seed)
    rows: list[dict[str, Any]] = []
    for epsilon in EPSILON_GRID:
        request = CountCategoryRequest(
            field="department", category=TARGET_CATEGORY, epsilon=epsilon
        )
        dataset_releases = np.empty(trials)
        neighbor_releases = np.empty(trials)
        true_dataset = 0
        true_neighbor = 0
        scale = 0.0
        for trial in range(trials):
            dataset_result = execute_count_category(
                request=request,
                schema=SYNTHETIC_WORKFORCE_SCHEMA,
                records=dataset,
                uniform_sampler=sampler,
            )
            neighbor_result = execute_count_category(
                request=request,
                schema=SYNTHETIC_WORKFORCE_SCHEMA,
                records=neighbor,
                uniform_sampler=sampler,
            )
            dataset_releases[trial] = dataset_result.noisy_result
            neighbor_releases[trial] = neighbor_result.noisy_result
            true_dataset = dataset_result.true_result
            true_neighbor = neighbor_result.true_result
            scale = dataset_result.scale
        lower_edge = float(min(np.min(dataset_releases), np.min(neighbor_releases)))
        upper_edge = float(max(np.max(dataset_releases), np.max(neighbor_releases)))
        if lower_edge == upper_edge:
            lower_edge -= 0.5
            upper_edge += 0.5
        bin_edges = np.linspace(lower_edge, upper_edge, 61)
        dataset_counts, _ = np.histogram(dataset_releases, bins=bin_edges)
        neighbor_counts, _ = np.histogram(neighbor_releases, bins=bin_edges)
        rows.append(
            {
                "epsilon": epsilon,
                "true_result_d": true_dataset,
                "true_result_d_prime": true_neighbor,
                "scale": scale,
                "bin_edges": bin_edges.tolist(),
                "d_bin_counts": dataset_counts.tolist(),
                "d_prime_bin_counts": neighbor_counts.tolist(),
            }
        )
    summary = {
        "experiment": "neighboring_datasets",
        "metadata": metadata(
            dataset_seed=dataset_seed,
            mechanism_seed=mechanism_seed,
            trials=trials,
        ),
        "illustrative_only": True,
        "note": (
            "Empirical overlap illustrates behavior; it does not prove "
            "differential privacy."
        ),
        "query_configuration": {
            "field": "department",
            "category": TARGET_CATEGORY,
            "replacement_category": REPLACEMENT_CATEGORY,
        },
        "results": rows,
    }
    destination = ensure_output_directory(output_dir)
    write_summary(destination, "neighboring_datasets.json", summary)
    _plot(destination / "neighboring_datasets.png", rows)
    return summary


def _plot(path: Path, rows: list[dict[str, Any]]) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(11, 7))
    for axis, row in zip(axes.flat, rows, strict=True):
        edges = np.asarray(row["bin_edges"])
        axis.stairs(row["d_bin_counts"], edges, label="D")
        axis.stairs(row["d_prime_bin_counts"], edges, label="D'", linestyle="--")
        axis.set(title=f"Epsilon = {row['epsilon']}", xlabel="Noisy Engineering count")
        axis.grid(alpha=0.3)
        axis.legend()
    figure.suptitle("Adjacent output distributions (illustrative, not a DP proof)")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main() -> None:
    parser = stochastic_parser(
        "Illustrate noisy outputs for one fixed-size neighboring dataset pair.",
        default_trials=DEFAULT_TRIALS,
    )
    arguments = parser.parse_args()
    run(
        output_dir=arguments.output_dir,
        trials=arguments.trials,
        dataset_seed=arguments.dataset_seed,
        mechanism_seed=arguments.mechanism_seed,
    )


if __name__ == "__main__":
    main()
