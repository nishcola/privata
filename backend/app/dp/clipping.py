"""Numeric clipping utilities for bounded private queries."""

import math
from numbers import Real


def validate_numeric_bounds(
    lower_bound: float, upper_bound: float
) -> tuple[float, float]:
    """Return finite public bounds after validating their ordering."""
    lower = _finite_real(lower_bound, "lower_bound")
    upper = _finite_real(upper_bound, "upper_bound")
    if upper < lower:
        raise ValueError("upper_bound must be greater than or equal to lower_bound")
    return lower, upper


def clip_numeric_value(
    value: float, *, lower_bound: float, upper_bound: float
) -> float:
    """Clip a finite numeric value to inclusive public bounds."""
    lower, upper = validate_numeric_bounds(lower_bound, upper_bound)
    numeric_value = _finite_real(value, "value")
    return min(upper, max(lower, numeric_value))


def _finite_real(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"{name} must be a finite real number")
    return numeric_value
