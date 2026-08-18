# Privata Development and Experiment Guide

## Development philosophy

Prefer correctness, explicit assumptions, and testability over feature count.

The DP engine should be understandable line by line.

## Backend tooling

Target:

- Python 3.11+
- FastAPI
- Pydantic
- pytest
- Ruff

Suggested commands:

```bash
cd backend
python -m pytest -q
ruff check .
```

If a type checker is configured:

```bash
mypy app
```

Adapt commands to the actual `pyproject.toml`.

## Frontend tooling

Target:

- React
- TypeScript
- Vite
- ESLint

Suggested commands:

```bash
cd frontend
npm test
npm run lint
npm run typecheck
npm run build
```

Do not add a frontend test framework unless component behavior justifies it.

## Numeric rules

Validate that epsilon and bounds are finite.

Reject:

- NaN
- infinity
- nonpositive epsilon
- upper bound below lower bound
- malformed or unordered histogram edges

Use a documented floating-point tolerance of `1e-12` in privacy-budget comparisons so floating-point accumulation does not produce meaningless negative remaining epsilon.

## Test strategy

### Unit tests

Cover:

- clipping
- sensitivity formulas
- epsilon validation
- Laplace scale
- injected deterministic noise
- accountant state transitions
- query result shapes
- ground-truth visibility policy

### Invariant tests

Examples:

- clipped numeric outputs stay within bounds
- mean sensitivity is nonnegative
- remaining epsilon never increases after a successful release
- rejected queries leave spent epsilon unchanged
- strict responses never contain true values

### Statistical tests

Avoid exact distribution assertions.

Prefer deterministic sampler injection for mechanism unit tests.

If a statistical sanity test is used, use broad tolerances and enough samples to avoid flakiness.

### Integration tests

Cover:

- create session
- each query type
- history update
- budget rejection
- strict-mode response
- safe demo-mode response
- unknown resource errors
- absence of raw-data endpoints

## Logging

Do not log:

- raw records
- unclipped private values
- strict-mode true results
- mechanism seeds/samples

Logging query type, epsilon, session id, and error category is acceptable.

## Dependency policy

Before adding a dependency:

1. explain why existing dependencies are insufficient
2. prefer small focused packages
3. do not add an external DP library to implement MVP privacy behavior

NumPy and Matplotlib belong in experiment/dev dependencies, not the core DP engine.

---

# Experiments

All experiments must import the same DP engine used by the backend.

Synthetic data generation must use explicit recorded seeds.

Application DP randomness remains OS-backed and unseeded.

Experiment scripts may offer a separate `--mechanism-seed` for reproducible Monte Carlo runs. That seed must never affect application behavior.

Write:

- compact JSON summaries to `experiments/output/`
- PNG plots to `experiments/output/`

Do not store huge trial-level arrays by default.

## Experiment 1: Privacy vs. utility

Question:

How does query error change as epsilon changes?

Default epsilon grid:

```text
0.05
0.1
0.25
0.5
1.0
2.0
5.0
```

Run at least:

- bounded mean
- category count
- histogram error

Reference run target:

- at least 5,000 trials per scalar query/epsilon

Metrics:

- mean absolute error
- RMSE
- median absolute error
- empirical bias
- histogram mean $L_1$ error
- histogram mean per-bin absolute error

Expected qualitative result:

Error generally decreases as epsilon increases.

Do not enforce strict monotonicity on a finite Monte Carlo sample.

## Experiment 2: Dataset size vs. mean utility

Question:

For fixed epsilon and fixed bounds, how does bounded-mean error change with dataset size?

Default sizes:

```text
50
100
250
500
1000
2500
5000
10000
```

Default epsilon:

```text
0.5
```

Because:

$$
\Delta_{\text{mean}}=(U-L)/n
$$

the Laplace scale shrinks as $n$ grows.

Report MAE and RMSE.

## Experiment 3: Sequential composition

Question:

How does repeated access consume a fixed privacy budget?

Example:

```text
epsilon_total = 2.0
queries = [0.1, 0.25, 0.5, 0.5, 0.75]
```

Output:

- query index
- requested epsilon
- accepted/rejected
- spent before
- spent after
- remaining after

The final trace should include an over-budget rejection.

## Experiment 4: Neighboring-dataset distributions

Question:

How do mechanism output distributions for adjacent datasets change with epsilon?

Create fixed-size datasets `D` and `D'` that differ in exactly one row.

Use a query whose true result changes across the pair.

Default epsilon grid:

```text
0.1
0.5
1.0
2.0
```

Reference run target:

- at least 10,000 trials per dataset/epsilon

Produce overlaid output distributions.

Important:

Empirical overlap illustrates mechanism behavior. It does not prove differential privacy. The guarantee comes from the mechanism and sensitivity proof.

## Experiment CLI

Each script should support:

```bash
python experiments/<name>.py --output-dir experiments/output
```

Useful flags:

```text
--trials
--dataset-seed
--mechanism-seed
```

## Portfolio-ready artifacts

The finished MVP should be able to show:

1. one privacy-vs-utility plot
2. one dataset-size plot
3. one neighboring-distributions plot
4. one privacy-budget composition trace

These are enough for the MVP.

---

# Agent implementation workflow

Build in these phases:

1. backend foundation and domain contracts
2. synthetic dataset layer
3. core DP primitives
4. DP queries
5. privacy accountant
6. API/service integration
7. experiments
8. frontend
9. correctness/privacy audit
10. portfolio documentation

Each phase should:

- begin by running existing relevant tests
- add tests for behavior changes
- stop at the phase boundary
- summarize commands run and failures
- avoid unrelated refactors

## Definition of done

A phase is done when:

- its prompt acceptance criteria are met
- targeted tests pass
- relevant full-suite checks pass
- no undocumented privacy-model change was made
- documentation still matches behavior
