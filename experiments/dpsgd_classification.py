"""Reproducible, offline DP-SGD experiment on fully synthetic tabular data.

This is intentionally separate from Privata's Laplace-query model.  It uses
sample-level add/remove adjacency, Gaussian DP-SGD, Poisson sampling, and a
PRV accountant.  It does not expose a training API or persist trained models.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

SYNTHETIC_DPSGD_SEED = 20260819
SYNTHETIC_DPSGD_ROW_COUNT = 10_000
TRAIN_ROW_COUNT = 8_000
TEST_ROW_COUNT = SYNTHETIC_DPSGD_ROW_COUNT - TRAIN_ROW_COUNT
DEPARTMENTS = ("Engineering", "Sales", "Operations", "Finance", "People")
TARGET_EPSILONS = (0.5, 1.0, 2.0, 4.0, 8.0)
DELTA = 1e-5
CLIPPING_NORM = 1.0
BATCH_SIZE = 256
EPOCHS = 20
LEARNING_RATE = 0.05
DEFAULT_RUNS = 5

_DEPARTMENT_LOGIT_OFFSETS = {
    "Engineering": 0.45,
    "Sales": -0.35,
    "Operations": 0.10,
    "Finance": 0.30,
    "People": -0.20,
}


@dataclass(frozen=True, slots=True)
class SyntheticRetentionRecord:
    """One fully synthetic privacy unit for the research training task."""

    age: int
    annual_income: int
    department: str
    retention_outcome: int


@dataclass(frozen=True, slots=True)
class PreparedDataset:
    """Fixed train/test arrays encoded only from public bounds and categories."""

    train_features: np.ndarray
    train_labels: np.ndarray
    test_features: np.ndarray
    test_labels: np.ndarray


def generate_synthetic_retention_dataset(
    *, seed: int = SYNTHETIC_DPSGD_SEED
) -> tuple[SyntheticRetentionRecord, ...]:
    """Generate a public, deterministic benchmark with a nontrivial signal."""
    generator = random.Random(seed)
    records: list[SyntheticRetentionRecord] = []
    for _ in range(SYNTHETIC_DPSGD_ROW_COUNT):
        age = generator.randint(18, 80)
        annual_income = generator.randint(20_000, 200_000)
        department = generator.choice(DEPARTMENTS)
        age_scaled = (age - 18) / (80 - 18)
        income_scaled = (annual_income - 20_000) / (200_000 - 20_000)
        logit = (
            -1.15
            + 1.2 * age_scaled
            + 1.4 * income_scaled
            + _DEPARTMENT_LOGIT_OFFSETS[department]
        )
        retention_probability = 1.0 / (1.0 + math.exp(-logit))
        records.append(
            SyntheticRetentionRecord(
                age=age,
                annual_income=annual_income,
                department=department,
                retention_outcome=int(generator.random() < retention_probability),
            )
        )
    return tuple(records)


def prepare_dataset(*, seed: int = SYNTHETIC_DPSGD_SEED) -> PreparedDataset:
    """Encode public features and make the documented fixed split."""
    records = generate_synthetic_retention_dataset(seed=seed)
    features = np.asarray(
        [
            (
                (record.age - 18) / (80 - 18),
                (record.annual_income - 20_000) / (200_000 - 20_000),
                *(float(record.department == department) for department in DEPARTMENTS),
            )
            for record in records
        ],
        dtype=np.float32,
    )
    labels = np.asarray(
        [record.retention_outcome for record in records], dtype=np.float32
    )
    return PreparedDataset(
        train_features=features[:TRAIN_ROW_COUNT],
        train_labels=labels[:TRAIN_ROW_COUNT],
        test_features=features[TRAIN_ROW_COUNT:],
        test_labels=labels[TRAIN_ROW_COUNT:],
    )


def _metric_summary(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    predictions = probabilities >= 0.5
    accuracy = float(np.mean(predictions == labels))
    clipped_probabilities = np.clip(probabilities, 1e-7, 1.0 - 1e-7)
    log_loss = float(
        -np.mean(
            labels * np.log(clipped_probabilities)
            + (1.0 - labels) * np.log(1.0 - clipped_probabilities)
        )
    )
    positives = probabilities[labels == 1]
    negatives = probabilities[labels == 0]
    roc_auc = float(
        (
            sum(float(positive > negative) for positive in positives for negative in negatives)
            + 0.5
            * sum(float(positive == negative) for positive in positives for negative in negatives)
        )
        / (len(positives) * len(negatives))
    )
    return {"accuracy": accuracy, "roc_auc": roc_auc, "log_loss": log_loss}


def _summary_metrics(metric_rows: list[dict[str, float]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for name in ("accuracy", "roc_auc", "log_loss"):
        values = [row[name] for row in metric_rows]
        result[f"{name}_mean"] = mean(values)
        result[f"{name}_stddev"] = stdev(values) if len(values) > 1 else 0.0
    return result


def _configure_torch(seed: int) -> tuple[Any, Any, Any]:
    """Load the experiment-only stack and configure reproducible CPU execution."""
    try:
        import torch
        from opacus import PrivacyEngine
    except ImportError as error:  # pragma: no cover - exercised by installation docs
        raise RuntimeError(
            "DP-SGD experiments require the backend development dependencies "
            "including torch and opacus."
        ) from error

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed)
    return torch, PrivacyEngine, torch.nn


def _evaluate(model: Any, features: Any, labels: np.ndarray, torch: Any) -> dict[str, float]:
    model.eval()
    with torch.no_grad():
        probabilities = torch.sigmoid(model(features).squeeze(1)).cpu().numpy()
    return _metric_summary(labels, probabilities)


def _base_components(dataset: PreparedDataset, seed: int) -> tuple[Any, Any, Any, Any, Any]:
    torch, _, nn = _configure_torch(seed)
    train_features = torch.from_numpy(dataset.train_features)
    train_labels = torch.from_numpy(dataset.train_labels)
    test_features = torch.from_numpy(dataset.test_features)
    model = nn.Linear(dataset.train_features.shape[1], 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=LEARNING_RATE, momentum=0.0)
    return torch, model, optimizer, train_features, train_labels, test_features


def _train_non_private(dataset: PreparedDataset, *, seed: int, epochs: int) -> dict[str, float]:
    torch, model, optimizer, train_features, train_labels, test_features = _base_components(
        dataset, seed
    )
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(train_features, train_labels),
        batch_size=BATCH_SIZE,
        shuffle=True,
    )
    loss_function = torch.nn.BCEWithLogitsLoss()
    model.train()
    for _ in range(epochs):
        for features, labels in loader:
            optimizer.zero_grad()
            loss_function(model(features).squeeze(1), labels).backward()
            optimizer.step()
    return _evaluate(model, test_features, dataset.test_labels, torch)


def _train_clipped_noiseless(
    dataset: PreparedDataset, *, seed: int, epochs: int
) -> dict[str, float]:
    torch, PrivacyEngine, _, = _configure_torch(seed)
    _, model, optimizer, train_features, train_labels, test_features = _base_components(
        dataset, seed
    )
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(train_features, train_labels),
        batch_size=BATCH_SIZE,
        shuffle=True,
    )
    privacy_engine = PrivacyEngine(accountant="prv", secure_mode=False)
    model, optimizer, private_loader = privacy_engine.make_private(
        module=model,
        optimizer=optimizer,
        data_loader=loader,
        noise_multiplier=0.0,
        max_grad_norm=CLIPPING_NORM,
        poisson_sampling=True,
        clipping="flat",
        grad_sample_mode="functorch",
    )
    loss_function = torch.nn.BCEWithLogitsLoss()
    model.train()
    for _ in range(epochs):
        for features, labels in private_loader:
            optimizer.zero_grad()
            features = features.requires_grad_(True)
            logits = model(features).squeeze(1)
            if labels.numel() == 0:
                (logits.sum() * 0.0).backward()
            else:
                loss_function(logits, labels).backward()
            optimizer.step()
    return _evaluate(model, test_features, dataset.test_labels, torch)


def _train_private(
    dataset: PreparedDataset, *, target_epsilon: float, seed: int, epochs: int
) -> tuple[dict[str, float], float, float, int]:
    torch, PrivacyEngine, _, = _configure_torch(seed)
    _, model, optimizer, train_features, train_labels, test_features = _base_components(
        dataset, seed
    )
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(train_features, train_labels),
        batch_size=BATCH_SIZE,
        shuffle=True,
    )
    privacy_engine = PrivacyEngine(accountant="prv", secure_mode=False)
    model, optimizer, private_loader = privacy_engine.make_private_with_epsilon(
        module=model,
        optimizer=optimizer,
        data_loader=loader,
        target_epsilon=target_epsilon,
        target_delta=DELTA,
        epochs=epochs,
        max_grad_norm=CLIPPING_NORM,
        poisson_sampling=True,
        clipping="flat",
        grad_sample_mode="functorch",
    )
    loss_function = torch.nn.BCEWithLogitsLoss()
    steps = 0
    model.train()
    for _ in range(epochs):
        for features, labels in private_loader:
            optimizer.zero_grad()
            features = features.requires_grad_(True)
            logits = model(features).squeeze(1)
            if labels.numel() == 0:
                (logits.sum() * 0.0).backward()
            else:
                loss_function(logits, labels).backward()
            optimizer.step()
            steps += 1
    actual_epsilon = float(privacy_engine.get_epsilon(DELTA))
    return (
        _evaluate(model, test_features, dataset.test_labels, torch),
        actual_epsilon,
        float(optimizer.noise_multiplier),
        steps,
    )


def _plot(
    *, output_dir: Path, private_results: list[dict[str, Any],], baselines: dict[str, Any]
) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    epsilons = [row["actual_epsilon_mean"] for row in private_results]
    accuracies = [row["accuracy_mean"] for row in private_results]
    errors = [row["accuracy_stddev"] for row in private_results]
    axis.errorbar(epsilons, accuracies, yerr=errors, marker="o", capsize=4, label="DP-SGD")
    for name, result in baselines.items():
        axis.axhline(result["accuracy_mean"], linestyle="--", label=name.replace("_", " "))
    axis.set_xscale("log")
    axis.set_xlabel("Actual epsilon (delta = 1e-5)")
    axis.set_ylabel("Test accuracy")
    axis.set_title("DP-SGD privacy versus accuracy on synthetic retention data")
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_dir / "dpsgd_classification.png", dpi=150)
    plt.close(figure)


def run(
    *,
    output_dir: Path,
    target_epsilons: tuple[float, ...] = TARGET_EPSILONS,
    epochs: int = EPOCHS,
    runs: int = DEFAULT_RUNS,
    dataset_seed: int = SYNTHETIC_DPSGD_SEED,
    training_seed: int = 20260820,
) -> dict[str, Any]:
    """Run baselines and private configurations, retaining only compact summaries."""
    if not target_epsilons or any(
        not math.isfinite(epsilon) or epsilon <= 0.0 for epsilon in target_epsilons
    ):
        raise ValueError("target_epsilons must contain only finite positive values")
    if epochs <= 0 or runs <= 0:
        raise ValueError("epochs and runs must be positive")

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = prepare_dataset(seed=dataset_seed)
    training_seeds = tuple(training_seed + index for index in range(runs))
    majority_probability = float(np.mean(dataset.train_labels))
    majority_predictions = np.full(TEST_ROW_COUNT, majority_probability >= 0.5)
    majority_result = _metric_summary(
        dataset.test_labels, majority_predictions.astype(np.float32)
    )
    baselines: dict[str, Any] = {
        "majority_class": {f"{name}_mean": value for name, value in majority_result.items()}
    }
    for name, trainer in (
        ("non_private", _train_non_private),
        ("clipped_noiseless", _train_clipped_noiseless),
    ):
        metrics = [trainer(dataset, seed=seed, epochs=epochs) for seed in training_seeds]
        baselines[name] = _summary_metrics(metrics)

    private_results: list[dict[str, Any]] = []
    for target_epsilon in target_epsilons:
        metric_rows: list[dict[str, float]] = []
        actual_epsilons: list[float] = []
        noise_multipliers: list[float] = []
        step_counts: list[int] = []
        for seed in training_seeds:
            metrics, actual_epsilon, noise_multiplier, steps = _train_private(
                dataset,
                target_epsilon=target_epsilon,
                seed=seed,
                epochs=epochs,
            )
            metric_rows.append(metrics)
            actual_epsilons.append(actual_epsilon)
            noise_multipliers.append(noise_multiplier)
            step_counts.append(steps)
        private_results.append(
            {
                "target_epsilon": target_epsilon,
                **_summary_metrics(metric_rows),
                "actual_epsilon_mean": mean(actual_epsilons),
                "actual_epsilon_stddev": stdev(actual_epsilons) if runs > 1 else 0.0,
                "noise_multiplier": mean(noise_multipliers),
                "steps_per_run": step_counts[0],
            }
        )

    summary: dict[str, Any] = {
        "metadata": {
            "privacy_model": "DP-SGD sample-level add/remove",
            "mechanism": "Gaussian DP-SGD",
            "accountant": "PRV",
            "delta": DELTA,
            "clipping_norm": CLIPPING_NORM,
            "sampling_rate": BATCH_SIZE / TRAIN_ROW_COUNT,
            "expected_batch_size": BATCH_SIZE,
            "epochs": epochs,
            "dataset_seed": dataset_seed,
            "training_seeds": training_seeds,
            "secure_mode": False,
            "reproducible_research_only": True,
        },
        "baselines": baselines,
        "private_results": private_results,
    }
    (output_dir / "dpsgd_classification.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _plot(output_dir=output_dir, private_results=private_results, baselines=baselines)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/output"))
    parser.add_argument("--dataset-seed", type=int, default=SYNTHETIC_DPSGD_SEED)
    parser.add_argument("--training-seed", type=int, default=20260820)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    return parser


def main() -> None:
    args = _parser().parse_args()
    summary = run(
        output_dir=args.output_dir,
        epochs=args.epochs,
        runs=args.runs,
        dataset_seed=args.dataset_seed,
        training_seed=args.training_seed,
    )
    print(json.dumps({"private_configurations": len(summary["private_results"])}, indent=2))


if __name__ == "__main__":
    main()
