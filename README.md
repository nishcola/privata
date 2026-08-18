# Privata

Privata is a local-first educational differential privacy analytics system.

It demonstrates how aggregate statistics can be released from a dataset while limiting the influence of any one record. The MVP implements its own core privacy machinery so the mathematical assumptions remain inspectable.

## MVP

Privata supports:

- a built-in synthetic dataset with public schema, bounds, categories, and histogram bins
- fixed-size replacement adjacency
- one row as one privacy unit
- `COUNT_CATEGORY`, bounded `MEAN`, and `HISTOGRAM`
- the Laplace mechanism
- pure-$\epsilon$ sequential composition
- per-session privacy-budget accounting
- strict mode that never returns true answers
- educational/demo mode for explicitly safe datasets
- reproducible experiments for:
  - privacy vs. utility
  - dataset size vs. utility
  - sequential composition
  - neighboring-dataset output distributions
- a FastAPI backend
- a React + TypeScript frontend

## Core privacy model

Two datasets are neighbors when they have the same number of rows and differ in at most one row.

For a numeric field bounded to $[L,U]$ and dataset size $n$:

- category-count sensitivity: $1$
- bounded-mean sensitivity: $(U-L)/n$
- histogram vector $L_1$ sensitivity: $2$

The Laplace mechanism uses:

$$
b = \frac{\Delta f}{\epsilon}
$$

Sequential composition tracks:

$$
\epsilon_{\text{spent}} = \sum_i \epsilon_i
$$

A query is rejected before execution if it would exceed the remaining budget.

## Repository docs

- [`AGENTS.md`](AGENTS.md): coding-agent operating rules and non-negotiable invariants
- [`SPEC.md`](SPEC.md): product scope, architecture, privacy model, API, and acceptance criteria
- [`DEVELOPMENT.md`](DEVELOPMENT.md): testing, experiments, commands, and implementation workflow
- [`AGENT_PROMPTS.md`](AGENT_PROMPTS.md): staged prompts for building the MVP

## Reproducible experiments

From the repository root, install the backend development dependencies in the
active Python environment, then run the experiments with explicit mechanism
seeds when a reproducible Monte Carlo result is needed:

```bash
cd backend
python -m pip install -e ".[dev]"
cd ..

python experiments/privacy_utility.py --output-dir experiments/output --mechanism-seed 20260818
python experiments/dataset_size.py --output-dir experiments/output --mechanism-seed 20260818
python experiments/composition.py --output-dir experiments/output
python experiments/neighboring_datasets.py --output-dir experiments/output --mechanism-seed 20260818
```

The default stochastic runs use 5,000 trials, except the neighboring-dataset
experiment, which uses 10,000. Its distribution overlap is illustrative and
does not prove differential privacy; the proof rests on the documented Laplace
mechanism and sensitivity analysis.

## Intended stack

Backend:

- Python 3.11+
- FastAPI
- Pydantic
- pytest
- Ruff

Frontend:

- React
- TypeScript
- Vite

Experiments:

- NumPy
- Matplotlib

The core DP engine must remain independent from FastAPI, React, pandas, NumPy, and external differential-privacy libraries.

## Non-goals for the MVP

Do not add:

- authentication
- cloud-hosted sensitive datasets
- arbitrary SQL or predicates
- filtered means
- Gaussian mechanisms
- $(\epsilon,\delta)$-DP accounting
- Rényi DP
- DP-SGD
- federated learning
- LLM features
- production-security or compliance claims

## Positioning

Privata is an educational implementation, not production privacy infrastructure.

Its value is in making this reasoning visible:

`adjacency -> sensitivity -> calibrated noise -> composition -> released result`
