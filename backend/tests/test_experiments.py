"""Fast end-to-end checks for the offline experiment entry points."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))


@pytest.mark.parametrize(
    ("script_name", "summary_name", "plot_name", "extra_args"),
    (
        (
            "privacy_utility.py",
            "privacy_utility.json",
            "privacy_utility.png",
            ("--trials", "3", "--dataset-seed", "7", "--mechanism-seed", "11"),
        ),
        (
            "dataset_size.py",
            "dataset_size.json",
            "dataset_size.png",
            ("--trials", "3", "--dataset-seed", "7", "--mechanism-seed", "11"),
        ),
        ("composition.py", "composition.json", "composition.png", ()),
        (
            "neighboring_datasets.py",
            "neighboring_datasets.json",
            "neighboring_datasets.png",
            ("--trials", "3", "--dataset-seed", "7", "--mechanism-seed", "11"),
        ),
    ),
)
def test_experiment_script_writes_compact_summary_and_plot(
    tmp_path: Path,
    script_name: str,
    summary_name: str,
    plot_name: str,
    extra_args: tuple[str, ...],
) -> None:
    """A missing output artifact or persisted trials must fail this smoke test."""
    result = subprocess.run(
        [
            sys.executable,
            f"experiments/{script_name}",
            "--output-dir",
            str(tmp_path),
            *extra_args,
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    summary_path = tmp_path / summary_name
    plot_path = tmp_path / plot_name
    assert summary_path.is_file()
    assert plot_path.is_file()
    assert plot_path.stat().st_size > 0
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["metadata"]
    assert "samples" not in json.dumps(summary)


def test_neighboring_datasets_differ_in_exactly_one_row() -> None:
    """Changing the construction must not silently use add/remove adjacency."""
    from experiments.neighboring_datasets import build_neighboring_datasets

    dataset, neighbor = build_neighboring_datasets(dataset_seed=7)

    assert len(dataset) == len(neighbor) == 500
    changed_rows = sum(
        left != right for left, right in zip(dataset, neighbor, strict=True)
    )
    assert changed_rows == 1


def test_neighboring_distribution_bins_include_every_release(tmp_path: Path) -> None:
    """Histogram summaries must account for every simulated noisy release."""
    from experiments.neighboring_datasets import run

    summary = run(
        output_dir=tmp_path,
        trials=10_000,
        dataset_seed=7,
        mechanism_seed=11,
    )

    for row in summary["results"]:
        assert sum(row["d_bin_counts"]) == 10_000
        assert sum(row["d_prime_bin_counts"]) == 10_000


def test_seeded_privacy_utility_summary_is_reproducible(tmp_path: Path) -> None:
    """Changing seeded sampling must not make repeat experiment summaries diverge."""
    from experiments.privacy_utility import run

    first = run(
        output_dir=tmp_path / "first",
        trials=3,
        dataset_seed=7,
        mechanism_seed=11,
    )
    second = run(
        output_dir=tmp_path / "second",
        trials=3,
        dataset_seed=7,
        mechanism_seed=11,
    )

    assert first == second
    assert (tmp_path / "first" / "privacy_utility.json").read_text(
        encoding="utf-8"
    ) == (tmp_path / "second" / "privacy_utility.json").read_text(encoding="utf-8")


def test_composition_summary_records_uncharged_over_budget_rejection(
    tmp_path: Path,
) -> None:
    """A rejected composition request must preserve the already spent budget."""
    result = subprocess.run(
        [
            sys.executable,
            "experiments/composition.py",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    trace = json.loads(
        (tmp_path / "composition.json").read_text(encoding="utf-8")
    )["trace"]
    rejected = trace[-1]
    assert rejected["accepted"] is False
    assert rejected["spent_before"] == rejected["spent_after"]
    assert rejected["remaining_after"] == pytest.approx(0.65)
