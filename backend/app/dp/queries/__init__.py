"""Typed private-query request contracts and execution functions."""

from importlib import import_module

__all__ = [
    "HistogramQueryResult",
    "ScalarQueryResult",
    "execute_count_category",
    "execute_histogram",
    "execute_mean",
]

_EXECUTION_EXPORTS = frozenset(__all__)


def __getattr__(name: str) -> object:
    """Load execution exports lazily to avoid the query-model import cycle."""
    if name not in _EXECUTION_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    execution = import_module("app.dp.queries.execution")
    return getattr(execution, name)
