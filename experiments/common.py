"""Shared CLI, randomness, and artifact helpers for offline experiments."""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from app.datasets.synthetic import SYNTHETIC_WORKFORCE_SEED
from app.dp.mechanisms.laplace import UniformSampler

DEFAULT_OUTPUT_DIRECTORY = Path("experiments/output")


def stochastic_parser(
    description: str, *, default_trials: int
) -> argparse.ArgumentParser:
    """Create a parser for a Monte Carlo experiment."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Directory for the JSON summary and PNG plot.",
    )
    parser.add_argument(
        "--trials",
        type=positive_integer,
        default=default_trials,
        help=f"Monte Carlo trials per configuration (default: {default_trials}).",
    )
    parser.add_argument(
        "--dataset-seed",
        type=int,
        default=SYNTHETIC_WORKFORCE_SEED,
        help="Seed used to generate the synthetic input records.",
    )
    parser.add_argument(
        "--mechanism-seed",
        type=int,
        default=None,
        help="Optional seed for experiment-only injected mechanism sampling.",
    )
    return parser


def positive_integer(value: str) -> int:
    """Parse a strictly positive CLI integer."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def experiment_sampler(mechanism_seed: int | None) -> UniformSampler | None:
    """Return an injected deterministic sampler only when explicitly requested."""
    if mechanism_seed is None:
        return None
    generator = random.Random(mechanism_seed)
    return generator.random


def ensure_output_directory(output_dir: Path) -> Path:
    """Create and return the requested artifact directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_summary(output_dir: Path, filename: str, summary: Mapping[str, Any]) -> Path:
    """Write a stable, compact JSON experiment summary."""
    path = ensure_output_directory(output_dir) / filename
    path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def scalar_error_metrics(errors: np.ndarray) -> dict[str, float]:
    """Return aggregate scalar-release error metrics without retaining trials."""
    absolute_errors = np.abs(errors)
    return {
        "mae": float(np.mean(absolute_errors)),
        "rmse": float(np.sqrt(np.mean(np.square(errors)))),
        "median_absolute_error": float(np.median(absolute_errors)),
        "empirical_bias": float(np.mean(errors)),
    }


def metadata(
    *,
    dataset_seed: int | None = None,
    mechanism_seed: int | None = None,
    trials: int | None = None,
) -> dict[str, int | None | str]:
    """Return common, non-sensitive run metadata."""
    result: dict[str, int | None | str] = {
        "adjacency": "fixed-size replacement",
        "mechanism": "Laplace",
    }
    if dataset_seed is not None:
        result["dataset_seed"] = dataset_seed
    if mechanism_seed is not None:
        result["mechanism_seed"] = mechanism_seed
    if trials is not None:
        result["trials"] = trials
    return result
