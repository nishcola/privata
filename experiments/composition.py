"""Illustrate Privata's sequential privacy-budget accounting trace."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.dp.accounting import PrivacySession
from app.dp.queries.models import QueryType
from app.errors import BudgetExceededError
from experiments.common import (
    DEFAULT_OUTPUT_DIRECTORY,
    ensure_output_directory,
    metadata,
    write_summary,
)

EPSILON_TOTAL = 2.0
REQUESTED_EPSILONS = (0.1, 0.25, 0.5, 0.5, 0.75)


def run(*, output_dir: Path) -> dict[str, Any]:
    """Create a composition trace using the application accountant directly."""
    session = PrivacySession(
        session_id="experiment-composition",
        dataset_id="synthetic-workforce",
        epsilon_total=EPSILON_TOTAL,
        strict_mode=True,
    )
    trace: list[dict[str, float | int | bool]] = []
    for index, requested_epsilon in enumerate(REQUESTED_EPSILONS, start=1):
        spent_before = session.epsilon_spent
        try:
            session.record_successful_query(
                query_id=f"experiment-query-{index}",
                query_type=QueryType.MEAN,
                epsilon=requested_epsilon,
            )
            accepted = True
        except BudgetExceededError:
            accepted = False
        trace.append(
            {
                "query_index": index,
                "requested_epsilon": requested_epsilon,
                "accepted": accepted,
                "spent_before": spent_before,
                "spent_after": session.epsilon_spent,
                "remaining_after": session.epsilon_remaining,
            }
        )
    summary = {
        "experiment": "composition",
        "metadata": metadata(),
        "epsilon_total": EPSILON_TOTAL,
        "trace": trace,
    }
    destination = ensure_output_directory(output_dir)
    write_summary(destination, "composition.json", summary)
    _plot(destination / "composition.png", trace)
    return summary


def _plot(path: Path, trace: list[dict[str, float | int | bool]]) -> None:
    indices = [int(entry["query_index"]) for entry in trace]
    spent_after = [float(entry["spent_after"]) for entry in trace]
    accepted = [bool(entry["accepted"]) for entry in trace]
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.step(indices, spent_after, where="post", label="Epsilon spent")
    axis.axhline(EPSILON_TOTAL, color="black", linestyle="--", label="Total budget")
    rejected_indices = [
        index for index, value in zip(indices, accepted, strict=True) if not value
    ]
    rejected_spent = [
        spent
        for spent, value in zip(spent_after, accepted, strict=True)
        if not value
    ]
    axis.scatter(rejected_indices, rejected_spent, color="red", label="Rejected query")
    axis.set(
        title="Privata: sequential composition trace",
        xlabel="Query index",
        ylabel="Epsilon spent",
        xticks=indices,
    )
    axis.grid(alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a sequential privacy-budget composition trace."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Directory for the JSON summary and PNG plot.",
    )
    arguments = parser.parse_args()
    run(output_dir=arguments.output_dir)


if __name__ == "__main__":
    main()
