# AGENTS.md

This is the primary operating context for any coding agent working on **Privata**.

Read this file before changing code.

## Purpose

Privata is an educational, local-first differential privacy analytics system.

A reviewer should be able to trace:

`privacy unit -> adjacency -> sensitivity -> noise calibration -> privacy accounting -> release`

Prefer correctness and inspectability over feature count.

## Source of truth

Priority order:

1. `AGENTS.md`
2. `SPEC.md`
3. `DEVELOPMENT.md`
4. `AGENT_PROMPTS.md`

If documents appear inconsistent, stop and surface the conflict instead of guessing.

## Non-negotiable privacy invariants

### Privacy unit and adjacency

- One row is one privacy unit.
- The MVP uses **fixed-size replacement adjacency**.
- Neighboring datasets have the same number of rows and differ in at most one row.

Do not silently switch to add/remove adjacency.

### Public metadata

Treat these as public configuration:

- schema
- numeric lower/upper bounds
- categorical domains
- histogram bin edges
- dataset size
- total session epsilon
- per-query epsilon

Do not infer numeric bounds from private records.

### Supported query sensitivities

Under the MVP adjacency definition:

- `COUNT_CATEGORY`: sensitivity $1$
- bounded `MEAN`: sensitivity $(U-L)/n$
- `HISTOGRAM`: vector $L_1$ sensitivity $2$

Do not substitute formulas from a source using a different adjacency model.

### Mechanism

The MVP uses pure $\epsilon$-DP with the Laplace mechanism:

$$
\text{scale} = \frac{\Delta f}{\epsilon}
$$

### Composition

Use simple sequential composition:

$$
\epsilon_{\text{spent}} = \sum_i \epsilon_i
$$

Reject a query before execution if it would exceed the remaining budget.

Do not charge epsilon when validation fails or execution is rejected.

### Ground truth

- Strict mode must never return the unnoised statistic.
- Demo mode may reveal ground truth only when the dataset is explicitly `safe_for_demo: true`.
- Never describe demo-mode ground truth as privately protected.

### Raw data

Do not add an HTTP endpoint that returns raw dataset rows.

## Architecture rules

The core DP engine must not depend on:

- FastAPI
- React
- pandas
- NumPy
- external DP libraries

The API may call the DP engine. The DP engine must never call the API layer.

Experiment code may use NumPy/Matplotlib and must reuse the same DP engine as the application.

Never duplicate privacy formulas in the frontend.

## Randomness

Default application mechanism sampling must use an OS-backed random source.

Tests may inject deterministic randomness.

Do not seed application DP randomness.

Experiments may use explicit pseudorandom seeds for synthetic-data generation and reproducible Monte Carlo runs, but those seeds must stay out of the application mechanism path.

## Scope control

Do not add features merely because they seem useful.

Unless explicitly requested, do not add:

- authentication
- user accounts
- databases for raw sensitive data
- arbitrary SQL
- arbitrary filters
- Gaussian mechanisms
- advanced accountants
- DP machine learning
- federated learning
- LLM features
- cloud deployment

Prefer a smaller mathematically defensible system.

## Agent workflow

For every phase:

1. Read `AGENTS.md`.
2. Read the relevant sections of `SPEC.md` and `DEVELOPMENT.md`.
3. Inspect the current repository.
4. Run existing relevant tests before editing.
5. Add or update tests when behavior changes.
6. Implement only the requested phase.
7. Run targeted tests.
8. Run the relevant full validation suite.
9. Summarize:
   - files changed
   - tests/commands run
   - design decisions
   - unresolved failures or uncertainties
10. Stop at the phase boundary.

Do not claim success if required checks were not run.

## Testing expectations

Tests must cover mathematical invariants, not only HTTP status codes.

Minimum coverage:

- clipping
- sensitivity formulas
- epsilon validation
- Laplace scale
- deterministic injected noise
- budget rejection
- charge-on-success only
- strict-mode ground-truth suppression
- histogram dimensions and boundaries
- neighboring-dataset experiment artifact generation

Avoid flaky distribution tests with small samples.

## Security language

Do not claim Privata is:

- unhackable
- perfectly anonymous
- production-grade privacy infrastructure
- HIPAA compliant
- GDPR compliant

The MVP demonstrates differential privacy only under its documented assumptions.

## Design discipline

Prefer focused modules.

Do not perform unrelated refactors during a feature phase.

If a source file grows beyond roughly 300-400 lines, check whether it has multiple responsibilities before adding more.

## Completion rule

A phase is complete only when:

- its acceptance criteria are satisfied
- required tests pass
- affected docs still match implementation
- no unreviewed privacy-model change was made

When privacy correctness is uncertain, stop and explain the issue rather than improvising.
