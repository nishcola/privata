"""Validation-only comparison of Privata's Laplace calibration with OpenDP."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.dp.mechanisms import laplace_release, laplace_scale
from app.dp.sensitivity import (
    count_category_sensitivity,
    histogram_sensitivity,
    mean_sensitivity,
)

EPSILON = 1.0
MEAN_LOWER_BOUND = 20_000.0
MEAN_UPPER_BOUND = 200_000.0
MEAN_DATASET_SIZE = 500
DEFAULT_TRIALS = 100_000
MINIMUM_TRIALS = 10_000
EMPIRICAL_SCALE_TOLERANCE = 0.10


@dataclass(frozen=True, slots=True)
class ComparisonSpec:
    """One public aggregate sensitivity and its intended Laplace scale."""

    name: str
    sensitivity: float
    scale: float
    is_vector: bool


def comparison_specs() -> tuple[ComparisonSpec, ...]:
    """Return the public query configurations used by the comparison."""
    sensitivities = (
        ("count_category", count_category_sensitivity(), False),
        (
            "mean",
            mean_sensitivity(
                lower_bound=MEAN_LOWER_BOUND,
                upper_bound=MEAN_UPPER_BOUND,
                n=MEAN_DATASET_SIZE,
            ),
            False,
        ),
        ("histogram", histogram_sensitivity(), True),
    )
    return tuple(
        ComparisonSpec(
            name=name,
            sensitivity=sensitivity,
            scale=laplace_scale(sensitivity=sensitivity, epsilon=EPSILON),
            is_vector=is_vector,
        )
        for name, sensitivity, is_vector in sensitivities
    )


def run(*, output_dir: Path, trials: int) -> dict[str, Any]:
    """Compare public Laplace calibration with OpenDP without using private data."""
    if trials < MINIMUM_TRIALS:
        raise ValueError(f"trials must be at least {MINIMUM_TRIALS}")

    import opendp.prelude as dp

    dp.enable_features("contrib")
    adjacency_metric, adjacency_distance = dp.unit_of(changes=1)
    adjacency_metric_name = dp.metric_type(adjacency_metric)
    if adjacency_metric_name != "ChangeOneDistance" or adjacency_distance != 1:
        raise RuntimeError("OpenDP bounded adjacency configuration is not available")

    rows = [_comparison_row(dp=dp, spec=spec, trials=trials) for spec in comparison_specs()]
    destination = _ensure_output_directory(output_dir)
    summary = {
        "experiment": "library_comparison",
        "metadata": {
            "comparison_library": "OpenDP",
            "opendp_version": dp.__version__,
            "epsilon": EPSILON,
            "trials": trials,
            "scale_estimator": "median absolute noise divided by ln(2)",
            "empirical_scale_tolerance": EMPIRICAL_SCALE_TOLERANCE,
        },
        "adjacency": {
            "privata": "fixed-size replacement",
            "opendp_metric": adjacency_metric_name,
            "opendp_distance": adjacency_distance,
            "alignment": "bounded one-row change",
        },
        "results": rows,
    }
    _write_summary(destination / "library_comparison.json", summary)
    _plot(destination / "library_comparison.png", rows)
    return summary


def _comparison_row(*, dp: Any, spec: ComparisonSpec, trials: int) -> dict[str, Any]:
    measurement = _opendp_measurement(dp=dp, spec=spec)
    opendp_epsilon = float(measurement.map(d_in=spec.sensitivity))
    if not math.isclose(opendp_epsilon, EPSILON, rel_tol=1e-12, abs_tol=1e-12):
        raise RuntimeError(
            f"OpenDP privacy map returned {opendp_epsilon} for {spec.name}, "
            f"expected {EPSILON}"
        )

    privata_scale = _empirical_scale(
        np.fromiter(
            (
                laplace_release(
                    value=0.0, sensitivity=spec.sensitivity, epsilon=EPSILON
                )
                for _ in range(trials)
            ),
            dtype=float,
            count=trials,
        )
    )
    opendp_scale = _empirical_scale(
        np.fromiter(
            (_opendp_release(measurement, spec.is_vector) for _ in range(trials)),
            dtype=float,
            count=trials,
        )
    )
    _validate_empirical_scale("Privata", spec, privata_scale)
    _validate_empirical_scale("OpenDP", spec, opendp_scale)
    return {
        "query": spec.name,
        "aggregate_metric": "l1" if spec.is_vector else "absolute",
        "sensitivity": spec.sensitivity,
        "theoretical_scale": spec.scale,
        "opendp_privacy_map_epsilon": opendp_epsilon,
        "privata_empirical_scale": privata_scale,
        "opendp_empirical_scale": opendp_scale,
        "privata_relative_error": _relative_error(privata_scale, spec.scale),
        "opendp_relative_error": _relative_error(opendp_scale, spec.scale),
    }


def _opendp_measurement(*, dp: Any, spec: ComparisonSpec) -> Any:
    if spec.is_vector:
        input_domain = dp.vector_domain(dp.atom_domain(T=float, nan=False))
        input_metric = dp.l1_distance(T=float)
    else:
        input_domain = dp.atom_domain(T=float, nan=False)
        input_metric = dp.absolute_distance(T=float)
    return dp.m.make_laplace(input_domain, input_metric, scale=spec.scale)


def _opendp_release(measurement: Any, is_vector: bool) -> float:
    if is_vector:
        return float(measurement([0.0])[0])
    return float(measurement(0.0))


def _empirical_scale(noise: np.ndarray) -> float:
    return float(np.median(np.abs(noise)) / math.log(2.0))


def _relative_error(observed: float, expected: float) -> float:
    return abs(observed - expected) / expected


def _validate_empirical_scale(
    library: str, spec: ComparisonSpec, observed_scale: float
) -> None:
    if _relative_error(observed_scale, spec.scale) > EMPIRICAL_SCALE_TOLERANCE:
        raise RuntimeError(
            f"{library} empirical scale for {spec.name} exceeds the "
            f"{EMPIRICAL_SCALE_TOLERANCE:.0%} tolerance"
        )


def _ensure_output_directory(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _write_summary(path: Path, summary: dict[str, Any]) -> None:
    import json

    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _plot(path: Path, rows: list[dict[str, Any]]) -> None:
    labels = [str(row["query"]) for row in rows]
    locations = np.arange(len(rows))
    width = 0.25
    figure, axis = plt.subplots(figsize=(9, 4.5))
    axis.bar(
        locations - width,
        [float(row["theoretical_scale"]) for row in rows],
        width,
        label="Theoretical",
    )
    axis.bar(
        locations,
        [float(row["privata_empirical_scale"]) for row in rows],
        width,
        label="Privata empirical",
    )
    axis.bar(
        locations + width,
        [float(row["opendp_empirical_scale"]) for row in rows],
        width,
        label="OpenDP empirical",
    )
    axis.set(
        title="Laplace scale validation at epsilon = 1",
        xlabel="Query configuration",
        ylabel="Scale",
        xticks=locations,
        xticklabels=labels,
    )
    axis.set_yscale("log")
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Privata's public Laplace calibration against OpenDP."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/output"),
        help="Directory for the JSON summary and PNG plot.",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=DEFAULT_TRIALS,
        help=f"Independent releases per library and query (default: {DEFAULT_TRIALS}).",
    )
    arguments = parser.parse_args()
    run(output_dir=arguments.output_dir, trials=arguments.trials)


if __name__ == "__main__":
    main()
