import math

import pytest

from app.dp.clipping import clip_numeric_value
from app.dp.mechanisms import laplace_release, laplace_scale
from app.dp.sensitivity import (
    count_category_sensitivity,
    histogram_sensitivity,
    mean_sensitivity,
)
from app.errors import InvalidEpsilonError


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-5.0, 0.0),
        (4.5, 4.5),
        (12.0, 10.0),
    ],
)
def test_clip_numeric_value_enforces_public_bounds(
    value: float, expected: float
) -> None:
    assert clip_numeric_value(value, lower_bound=0.0, upper_bound=10.0) == expected


def test_clip_numeric_value_supports_equal_public_bounds() -> None:
    assert clip_numeric_value(99.0, lower_bound=4.0, upper_bound=4.0) == 4.0


@pytest.mark.parametrize(
    ("lower_bound", "upper_bound"),
    [
        (2.0, 1.0),
        (float("nan"), 1.0),
        (0.0, float("nan")),
        (float("inf"), 1.0),
        (0.0, float("-inf")),
    ],
)
def test_clip_numeric_value_rejects_invalid_public_bounds(
    lower_bound: float, upper_bound: float
) -> None:
    with pytest.raises(ValueError):
        clip_numeric_value(1.0, lower_bound=lower_bound, upper_bound=upper_bound)


def test_fixed_replacement_sensitivities_are_exact() -> None:
    assert count_category_sensitivity() == 1.0
    assert mean_sensitivity(lower_bound=10.0, upper_bound=70.0, n=24) == 2.5
    assert histogram_sensitivity() == 2.0


@pytest.mark.parametrize("n", [0, -1])
def test_mean_sensitivity_rejects_nonpositive_dataset_size(n: int) -> None:
    with pytest.raises(ValueError):
        mean_sensitivity(lower_bound=0.0, upper_bound=100.0, n=n)


@pytest.mark.parametrize(
    "epsilon", [0.0, -1.0, float("nan"), float("inf"), float("-inf")]
)
def test_laplace_scale_rejects_invalid_epsilon(epsilon: float) -> None:
    with pytest.raises(InvalidEpsilonError):
        laplace_scale(sensitivity=2.0, epsilon=epsilon)


@pytest.mark.parametrize("sensitivity", [-1.0, float("nan"), float("inf")])
def test_laplace_scale_rejects_invalid_sensitivity(sensitivity: float) -> None:
    with pytest.raises(ValueError):
        laplace_scale(sensitivity=sensitivity, epsilon=1.0)


def test_laplace_scale_uses_sensitivity_over_epsilon() -> None:
    assert laplace_scale(sensitivity=3.0, epsilon=0.5) == 6.0


def test_laplace_release_uses_injected_uniform_sample() -> None:
    result = laplace_release(
        value=10.0,
        sensitivity=2.0,
        epsilon=1.0,
        uniform_sampler=lambda: 0.75,
    )

    assert result == pytest.approx(10.0 + 2.0 * math.log(2.0))


def test_laplace_release_returns_the_value_for_a_median_uniform_sample() -> None:
    assert (
        laplace_release(
            value=-3.5,
            sensitivity=2.0,
            epsilon=1.0,
            uniform_sampler=lambda: 0.5,
        )
        == -3.5
    )


@pytest.mark.parametrize("sample", [float("nan"), float("inf"), -0.1, 1.0])
def test_laplace_release_rejects_invalid_injected_uniform_samples(
    sample: float,
) -> None:
    with pytest.raises(ValueError):
        laplace_release(
            value=0.0,
            sensitivity=1.0,
            epsilon=1.0,
            uniform_sampler=lambda: sample,
        )
