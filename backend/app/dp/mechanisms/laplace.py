"""Pure-epsilon Laplace mechanism primitives."""

import math
import secrets
from collections.abc import Callable
from numbers import Real

from app.errors import InvalidEpsilonError

UniformSampler = Callable[[], float]


def laplace_scale(*, sensitivity: float, epsilon: float) -> float:
    """Return the Laplace scale for a finite sensitivity and epsilon."""
    numeric_epsilon = _positive_epsilon(epsilon)
    numeric_sensitivity = _nonnegative_sensitivity(sensitivity)
    scale = numeric_sensitivity / numeric_epsilon
    if not math.isfinite(scale):
        raise ValueError("Laplace scale must be finite")
    return scale


def laplace_release(
    *,
    value: float,
    sensitivity: float,
    epsilon: float,
    uniform_sampler: UniformSampler | None = None,
) -> float:
    """Release a value with Laplace noise from an OS-backed default sampler."""
    numeric_value = _finite_real(value, "value")
    scale = laplace_scale(sensitivity=sensitivity, epsilon=epsilon)
    sampler = uniform_sampler or secrets.SystemRandom().random
    sample = _uniform_sample(sampler())
    if sample == 0.0:
        sample = math.nextafter(0.0, 1.0)
    centered = sample - 0.5
    if centered == 0.0:
        return numeric_value
    magnitude = -scale * math.log1p(-2.0 * abs(centered))
    noise = math.copysign(magnitude, centered)
    return numeric_value + noise


def _positive_epsilon(epsilon: float) -> float:
    if isinstance(epsilon, bool) or not isinstance(epsilon, Real):
        raise InvalidEpsilonError()
    numeric_epsilon = float(epsilon)
    if not math.isfinite(numeric_epsilon) or numeric_epsilon <= 0.0:
        raise InvalidEpsilonError()
    return numeric_epsilon


def _nonnegative_sensitivity(sensitivity: float) -> float:
    return _finite_real(sensitivity, "sensitivity", nonnegative=True)


def _uniform_sample(sample: float) -> float:
    numeric_sample = _finite_real(sample, "uniform sampler result")
    if not 0.0 <= numeric_sample < 1.0:
        raise ValueError("uniform sampler result must be in [0.0, 1.0)")
    return numeric_sample


def _finite_real(value: float, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"{name} must be a finite real number")
    if nonnegative and numeric_value < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return numeric_value
