"""Tests for the offline OpenDP comparison harness."""

import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))


def test_comparison_specs_match_public_replacement_sensitivities() -> None:
    """The validation harness must use Privata's documented public model."""
    from experiments.library_comparison import comparison_specs

    specs = comparison_specs()

    assert [spec.name for spec in specs] == ["count_category", "mean", "histogram"]
    assert [spec.sensitivity for spec in specs] == pytest.approx((1.0, 360.0, 2.0))
    assert [spec.scale for spec in specs] == pytest.approx((1.0, 360.0, 2.0))


def test_comparison_run_writes_compact_summary_and_plot(tmp_path: Path) -> None:
    """The offline comparison emits inspectable artifacts without raw samples."""
    from experiments.library_comparison import run

    summary = run(output_dir=tmp_path, trials=10_000)

    assert summary["adjacency"]["opendp_metric"] == "ChangeOneDistance"
    assert [row["query"] for row in summary["results"]] == [
        "count_category",
        "mean",
        "histogram",
    ]
    assert [row["opendp_privacy_map_epsilon"] for row in summary["results"]] == (
        pytest.approx((1.0, 1.0, 1.0))
    )
    assert all(
        row["privata_relative_error"] <= 0.10
        and row["opendp_relative_error"] <= 0.10
        for row in summary["results"]
    )
    assert (tmp_path / "library_comparison.json").is_file()
    assert (tmp_path / "library_comparison.png").is_file()
    assert "samples" not in (tmp_path / "library_comparison.json").read_text(
        encoding="utf-8"
    )


def test_comparison_rejects_too_few_trials(tmp_path: Path) -> None:
    """Small Monte Carlo samples would make the broad scale check unreliable."""
    from experiments.library_comparison import run

    with pytest.raises(ValueError, match="at least 10000"):
        run(output_dir=tmp_path, trials=9_999)


def test_core_dp_engine_does_not_import_opendp() -> None:
    """OpenDP remains an offline validation dependency, never an engine dependency."""
    core_directory = REPOSITORY_ROOT / "backend" / "app" / "dp"

    for source_path in core_directory.rglob("*.py"):
        assert "opendp" not in source_path.read_text(encoding="utf-8").lower()
