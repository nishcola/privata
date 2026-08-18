"""Measure bounded-mean utility as fixed public dataset size grows."""

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
    SYNTHETIC_WORKFORCE_SCHEMA,
    generate_synthetic_workforce,
)
from app.dp.queries import execute_mean
from app.dp.queries.models import MeanRequest
from experiments.common import (
    ensure_output_directory,
    experiment_sampler,
    metadata,
    scalar_error_metrics,
    stochastic_parser,
    write_summary,
)

DATASET_SIZES = (50, 100, 250, 500, 1_000, 2_500, 5_000, 10_000)
EPSILON = 0.5
DEFAULT_TRIALS = 5_000


def run(
    *, output_dir: Path, trials: int, dataset_seed: int, mechanism_seed: int | None
) -> dict[str, Any]:
    """Create dataset-size utility artifacts through the existing mean executor."""
    sampler = experiment_sampler(mechanism_seed)
    request = MeanRequest(field="annual_income", epsilon=EPSILON)
    rows: list[dict[str, Any]] = []
    for row_count in DATASET_SIZES:
        records = generate_synthetic_workforce(seed=dataset_seed, row_count=row_count)
        errors = np.empty(trials)
        sensitivity = 0.0
        scale = 0.0
        for trial in range(trials):
            result = execute_mean(
                request=request,
                schema=SYNTHETIC_WORKFORCE_SCHEMA,
                records=records,
                uniform_sampler=sampler,
            )
            errors[trial] = result.noisy_result - result.true_result
            sensitivity = result.sensitivity
            scale = result.scale
        metrics = scalar_error_metrics(errors)
        rows.append(
            {
                "dataset_size": row_count,
                "sensitivity": sensitivity,
                "scale": scale,
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
            }
        )
    summary = {
        "experiment": "dataset_size",
        "metadata": metadata(
            dataset_seed=dataset_seed,
            mechanism_seed=mechanism_seed,
            trials=trials,
        ),
        "epsilon": EPSILON,
        "query_configuration": {"mean_field": "annual_income"},
        "results": rows,
    }
    destination = ensure_output_directory(output_dir)
    write_summary(destination, "dataset_size.json", summary)
    _plot(destination / "dataset_size.png", rows)
    return summary


def _plot(path: Path, rows: list[dict[str, Any]]) -> None:
    sizes = [row["dataset_size"] for row in rows]
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot(sizes, [row["mae"] for row in rows], marker="o", label="MAE")
    axis.plot(sizes, [row["rmse"] for row in rows], marker="o", label="RMSE")
    axis.set_xscale("log")
    axis.set(
        title="Privata: mean utility by dataset size",
        xlabel="Dataset size",
        ylabel="Error",
    )
    axis.grid(alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main() -> None:
    parser = stochastic_parser(
        "Measure bounded-mean utility as dataset size changes.",
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
