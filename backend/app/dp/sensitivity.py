"""Sensitivity formulas for fixed-size replacement adjacency."""

from app.dp.clipping import validate_numeric_bounds


def count_category_sensitivity() -> float:
    """Return the sensitivity of a declared-category count."""
    return 1.0


def mean_sensitivity(*, lower_bound: float, upper_bound: float, n: int) -> float:
    """Return bounded-mean sensitivity for a fixed dataset size."""
    lower, upper = validate_numeric_bounds(lower_bound, upper_bound)
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")
    return (upper - lower) / n


def histogram_sensitivity() -> float:
    """Return vector L1 sensitivity for a one-bin-per-row histogram."""
    return 2.0
