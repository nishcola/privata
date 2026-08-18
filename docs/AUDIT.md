# Phase 9 Correctness and Privacy Audit

## Checks performed

- Read `AGENTS.md`, `SPEC.md`, and `DEVELOPMENT.md`, then traced each
  privacy requirement through the backend DP engine, dataset registry,
  service layer, API routes, frontend, experiments, and tests.
- Confirmed the implementation uses one row per privacy unit and fixed-size
  replacement adjacency. The sensitivity module returns `1` for category
  counts, `(U-L)/n` for bounded means, and vector L1 sensitivity `2` for
  histograms.
- Confirmed numeric query values are clipped to public bounds before mean and
  numeric-histogram aggregation. Histogram releases independently apply
  Laplace noise with scale `2/epsilon`; negative noisy bins are preserved.
- Confirmed epsilon contracts, accountant validation, and the Laplace
  mechanism reject non-finite and nonpositive epsilon values. Validation,
  budget, and mechanism failures leave accounting unchanged; a successful
  release is charged once and appended once to safe history metadata.
- Confirmed strict-mode responses and history omit true results. Demo truth is
  returned only for a non-strict session whose dataset is `safe_for_demo`.
- Confirmed the OpenAPI route set contains no raw-record endpoint. Dataset
  routes expose public metadata/schema only.
- Confirmed application mechanism sampling defaults to
  `secrets.SystemRandom().random` and has no application seed. Deterministic
  samplers are injected only by tests and experiment scripts.
- Confirmed all experiment scripts invoke the application DP query/accounting
  code rather than duplicating sensitivity or noise formulas. The neighboring
  experiment constructs equal-size datasets differing in exactly one record.
- Confirmed application source contains no logging calls that could expose raw
  records or true results. Expected privacy-model configuration errors are
  serialized without their internal details.
- Confirmed numeric-bin behavior is tested: bins are left-inclusive and
  right-exclusive except the final bin includes its upper edge. Public edges
  now must cover the entire declared numeric range.

## Issues found

Numeric histogram schemas previously validated only that their edges were
finite and strictly increasing. A field declared with bounds `[0, 10]` could
therefore use edges `(0, 5)`. Such a public partition does not assign every
possible clipped value to one bin, which breaks the histogram model before any
private data is queried.

## Fixes

- `NumericFieldSchema` now rejects histogram edges whose first edge is above
  the lower bound or whose last edge is below the upper bound.
- Added a regression test for both uncovered lower and upper bounds, and moved
  the prior runtime configuration-error test to schema-validation coverage.
- Documented the numeric histogram boundary convention and coverage invariant
  in `README.md`.

## Remaining limitations

This audit does not change Privata's documented threat-model boundaries. It is
an educational, local-first implementation of record-level DP for the three
supported aggregates under fixed-size replacement adjacency. It does not
address malicious operators, compromised hosts, side channels, multi-row
contributions, distributed accounting, access control, encrypted storage, or
network security.

## Validation commands and results

Initial baseline command:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Result: 214 passed and 7 errors because pytest could not access the default
Windows temp directory. Re-running with a workspace-local base temp directory
removed that environment-only failure.

Final validation:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp
# 223 passed in 18.72s

.\.venv\Scripts\python.exe -m ruff check .
# All checks passed!

cd ..\frontend
.\node_modules\.bin\vitest.cmd run --reporter=verbose
# 1 test file passed; 7 tests passed

.\node_modules\.bin\eslint.cmd .
# exit 0

.\node_modules\.bin\tsc.cmd -b --pretty false
# exit 0

.\node_modules\.bin\vite.cmd build
# exit 0; production build completed
```

The frontend commands required elevated filesystem access because the sandbox
could not read the existing `node_modules` files (`EPERM`).
