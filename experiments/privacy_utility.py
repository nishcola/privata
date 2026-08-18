"""Measure how Privata query error changes over an epsilon grid."""

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

from app.datasets.synthetic import (
    SYNTHETIC_WORKFORCE_ROW_COUNT,
    SYNTHETIC_WORKFORCE_SCHEMA,
    generate_synthetic_workforce,
)
from app.dp.queries import execute_count_category, execute_histogram, execute_mean
from app.dp.queries.models import CountCategoryRequest, HistogramRequest, MeanRequest
from experiments.common import (
    ensure_output_directory,
    experiment_sampler,
    metadata,
    scalar_error_metrics,
    stochastic_parser,
    write_summary,
)

EPSILON_GRID = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
DEFAULT_TRIALS = 5_000


def run(
    *, output_dir: Path, trials: int, dataset_seed: int, mechanism_seed: int | None
) -> dict[str, Any]:
    """Create privacy-versus-utility artifacts from real DP query executions."""
    records = generate_synthetic_workforce(
        seed=dataset_seed, row_count=SYNTHETIC_WORKFORCE_ROW_COUNT
    )
    sampler = experiment_sampler(mechanism_seed)
    rows: list[dict[str, Any]] = []
    for epsilon in EPSILON_GRID:
        mean_request = MeanRequest(field="annual_income", epsilon=epsilon)
        count_request = CountCategoryRequest(
            field="department", category="Engineering", epsilon=epsilon
        )
        histogram_request = HistogramRequest(field="department", epsilon=epsilon)
        mean_errors = np.empty(trials)
        count_errors = np.empty(trials)
        histogram_l1_errors = np.empty(trials)
        histogram_per_bin_errors = np.empty(trials)
        for trial in range(trials):
            mean_result = execute_mean(
                request=mean_request,
                schema=SYNTHETIC_WORKFORCE_SCHEMA,
                records=records,
                uniform_sampler=sampler,
            )
            count_result = execute_count_category(
                request=count_request,
                schema=SYNTHETIC_WORKFORCE_SCHEMA,
                records=records,
                uniform_sampler=sampler,
            )
            histogram_result = execute_histogram(
                request=histogram_request,
                schema=SYNTHETIC_WORKFORCE_SCHEMA,
                records=records,
                uniform_sampler=sampler,
            )
            mean_errors[trial] = mean_result.noisy_result - mean_result.true_result
            count_errors[trial] = count_result.noisy_result - count_result.true_result
            histogram_errors = np.abs(
                np.asarray(histogram_result.noisy_result)
                - np.asarray(histogram_result.true_result)
            )
            histogram_l1_errors[trial] = float(np.sum(histogram_errors))
            histogram_per_bin_errors[trial] = float(np.mean(histogram_errors))
        rows.append(
            {
                "epsilon": epsilon,
                "mean": scalar_error_metrics(mean_errors),
                "count": scalar_error_metrics(count_errors),
                "histogram": {
                    "mean_l1_error": float(np.mean(histogram_l1_errors)),
                    "mean_per_bin_absolute_error": float(
                        np.mean(histogram_per_bin_errors)
                    ),
                },
            }
        )
    summary = {
        "experiment": "privacy_utility",
        "metadata": metadata(
            dataset_seed=dataset_seed,
            mechanism_seed=mechanism_seed,
            trials=trials,
        ),
        "epsilon_grid": list(EPSILON_GRID),
        "query_configuration": {
            "mean_field": "annual_income",
            "count_field": "department",
            "count_category": "Engineering",
            "histogram_field": "department",
        },
        "results": rows,
    }
    destination = ensure_output_directory(output_dir)
    write_summary(destination, "privacy_utility.json", summary)
    _plot(destination / "privacy_utility.png", rows)
    return summary


def _plot(path: Path, rows: list[dict[str, Any]]) -> None:
    epsilons = [row["epsilon"] for row in rows]
    figure, axes = plt.subplots(1, 3, figsize=(14, 4))
    axes[0].plot(epsilons, [row["mean"]["mae"] for row in rows], marker="o")
    axes[0].set(title="Bounded mean", xlabel="Epsilon", ylabel="MAE")
    axes[1].plot(epsilons, [row["count"]["mae"] for row in rows], marker="o")
    axes[1].set(title="Category count", xlabel="Epsilon", ylabel="MAE")
    axes[2].plot(
        epsilons,
        [row["histogram"]["mean_l1_error"] for row in rows],
        marker="o",
    )
    axes[2].set(title="Histogram", xlabel="Epsilon", ylabel="Mean L1 error")
    for axis in axes:
        axis.set_xscale("log")
        axis.grid(alpha=0.3)
    figure.suptitle("Privata: privacy versus utility")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main() -> None:
    parser = stochastic_parser(
        "Measure query utility over a public epsilon grid.",
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
