# Privata

Privata is a local-first educational system for releasing a small set of aggregate statistics with record-level differential privacy. It is built to trace one release from its privacy unit and adjacency assumption, through sensitivity and Laplace noise calibration, to privacy budget accounting.

## Privacy model

The privacy unit is exactly one dataset row. Privata assumes that one person contributes one row.

Privata uses fixed-size replacement adjacency. Datasets $D$ and $D'$ are neighbors when they have the same number of rows and differ in at most one row. This is not add/remove adjacency. The public configuration is the schema, numeric bounds, categorical domains, histogram edges, dataset size, session epsilon, and query epsilon. Bounds are never learned from records.

Numeric values are clipped before a numeric query:

$$
\operatorname{clip}(x)=\min(U,\max(L,x))
$$

The mechanism is pure $\epsilon$-DP Laplace noise:

$$
b=\frac{\Delta f}{\epsilon},\qquad M(D)=f(D)+\operatorname{Laplace}(0,b)
$$

Application releases use OS-backed randomness. Tests and offline experiments may inject deterministic sampling; their seeds do not enter the application release path.

### Supported queries and sensitivities

| Query | Public inputs | Statistic | Sensitivity under replacement adjacency |
| --- | --- | --- | --- |
| `COUNT_CATEGORY` | Declared field and category | $\sum_i \mathbf{1}[x_i=c]$ | $1$ |
| `MEAN` | Numeric field with declared $[L,U]$ and fixed $n$ | $\frac{1}{n}\sum_i \operatorname{clip}(x_i)$ | $(U-L)/n$ |
| `HISTOGRAM` | Field's declared public partition | One count per bin/category | vector $L_1$ sensitivity $2$ |

A replacement can move one record from one histogram bin to another, changing two coordinates by one. Privata adds independent Laplace noise to each bin with scale $2/\epsilon$ and deliberately does not clamp negative noisy counts in the core mechanism. Numeric bins are `[lower, upper)`, except the final bin includes its upper edge; declared edges cover the full public numeric range. A bare row count is excluded because $n$ is fixed and public.

## Architecture

```text
public schema, bounds, domains, bins, row count
                  │
                  ▼
synthetic dataset registry ── trusted records ──► analysis service
                                                    │ validate schema and budget
                                                    ▼
                                              framework-free DP engine
                                  clipping → sensitivity → Laplace query result
                                                    │ successful release only
                                                    ▼
                                               session accountant
                                                    │ safe response/history metadata
                         FastAPI routes ◄───────────┴───────────► React frontend
```

The dataset layer owns synthetic records and public metadata. The DP engine owns clipping, sensitivity, mechanisms, queries, and accountant types. It has no FastAPI, React, pandas, NumPy, or external DP-library dependency. The service validates the request and budget, executes the query, then charges a successful release once. API routes serialize that result; the frontend uses the backend as the source of truth and does not implement privacy formulas.

## Privacy budget and release policy

Sessions use simple sequential composition:

$$
\epsilon_{\mathrm{spent}}=\sum_i\epsilon_i,\qquad
\epsilon_{\mathrm{remaining}}=\epsilon_{\mathrm{total}}-\epsilon_{\mathrm{spent}}
$$

Each query has finite, positive epsilon no greater than the public per-query maximum of 10. A request that exceeds the remaining budget is rejected before the mechanism runs and is not charged. The accountant uses a $10^{-12}$ tolerance only to normalize floating-point residue at exhaustion.

Strict sessions return noisy results and release metadata but never a true aggregate, raw records, unclipped values, or sampling seeds. Demo sessions return a true aggregate only for a dataset explicitly marked `safe_for_demo`; the response labels it `true_result_is_demo: true`. That value is not a private release.

## Local setup and validation

The backend requires Python 3.11 or later. The frontend declares pnpm 10.6.5. The following Windows PowerShell commands are the repository setup and validation path.

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp
.\.venv\Scripts\python.exe -m ruff check .
```

```powershell
Set-Location frontend
pnpm install --frozen-lockfile
pnpm test
pnpm run lint
pnpm run typecheck
pnpm run build
```

The HTTP demo command used in this repository is below. Uvicorn is available, but it is not currently declared in `backend/pyproject.toml`; install or provide an ASGI runner before relying on this command in a fresh environment.

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, start the UI with `pnpm dev` from `frontend/`. It calls `http://127.0.0.1:8000` by default.

## Reproducible experiments

From the repository root, after the backend editable install, run:

```powershell
.\backend\.venv\Scripts\python.exe experiments\privacy_utility.py --output-dir experiments\output --mechanism-seed 20260818
.\backend\.venv\Scripts\python.exe experiments\dataset_size.py --output-dir experiments\output --mechanism-seed 20260818
.\backend\.venv\Scripts\python.exe experiments\composition.py --output-dir experiments\output
.\backend\.venv\Scripts\python.exe experiments\neighboring_datasets.py --output-dir experiments\output --mechanism-seed 20260818
```

Each script imports the same DP query or accounting code as the application. It writes a compact JSON summary and PNG plot to `experiments/output/`. The two seeded Monte Carlo scripts default to 5,000 trials per configuration; the neighboring-dataset script defaults to 10,000 trials per dataset and epsilon.

### Findings from the recorded Phase 10 run

The commands above were run with synthetic dataset seed `20260815` and, where applicable, mechanism seed `20260818`.

| Experiment | Recorded result |
| --- | --- |
| Privacy versus utility, 5,000 trials | From $\epsilon=0.05$ to $5$, mean MAE fell from 7,134.97 to 71.90; category-count MAE from 19.84 to 0.21; histogram mean $L_1$ error from 199.89 to 2.02. |
| Dataset size versus mean utility, 5,000 trials at $\epsilon=0.5$ | From $n=50$ to $10,000$, mean sensitivity fell from 3,600 to 18, Laplace scale from 7,200 to 36, and MAE from 7,131.00 to 35.27. |
| Sequential composition | With total $\epsilon=2$, requests 0.1, 0.25, 0.5, and 0.5 were accepted. The 0.75 request was rejected with 0.65 remaining; spent epsilon stayed 1.35. |
| Neighboring distributions, 10,000 releases per dataset/epsilon | The adjacent datasets had true Engineering counts 89 and 88. Recorded Laplace scales were 10, 2, 1, and 0.5 for $\epsilon$ 0.1, 0.5, 1, and 2 respectively. |

The neighboring-distribution plot is an illustration of sampled outputs, not a proof of differential privacy. The guarantee follows from the adjacency definition, sensitivity proof, and Laplace calibration.

## Limitations and threat model

Privata demonstrates record-level DP only for these three aggregates and only under its stated public metadata and one-row-per-person assumption. It does not protect against malicious server operators, compromised hosts, side channels, multi-row contributions by one person, linkage attacks outside the DP release model, or disclosure through public schema, bounds, bins, or dataset size.

Privata also does not provide access control, encrypted storage, secure deletion, network security, distributed privacy accounting, add/remove adjacency, arbitrary filters or SQL, Gaussian mechanisms, or advanced accountants. Sessions are in-memory. There is no HTTP route for raw dataset records.

## Engineering choices

- The core engine is framework-independent and uses the standard library for its privacy calculations; experiment code reuses that engine rather than copying formulas.
- The built-in 500-row workforce dataset is deterministic and synthetic, with public bounds, categories, and histogram edges. Its `safe_for_demo` marker gates demo-only truth disclosure.
- Query execution is serialized by the analysis service. Validation, budget rejection, and mechanism failures leave the accountant unchanged; successful releases are charged and appended to safe history once.
- API discovery exposes public dataset metadata and schemas only. Strict-mode history stores query type, charged epsilon, remaining epsilon, timestamp, and query identifier, not true answers or records.

## Demo

Follow the 2-4 minute flow in [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).