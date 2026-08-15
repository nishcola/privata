# Privata MVP Specification

## Goal

Build a small educational system that lets a user issue a limited set of aggregate queries against a local dataset and receive differentially private answers under an explicit privacy budget.

The system should make the privacy model understandable, testable, and visible in a portfolio.

## User flow

A user can:

1. select a safe built-in demo dataset
2. inspect its public schema and bounds
3. start an analysis session with a total epsilon budget
4. run `COUNT_CATEGORY`, bounded `MEAN`, and `HISTOGRAM`
5. see the noisy result and remaining budget
6. optionally see the true result only in demo mode on a safe dataset
7. inspect reproducible privacy/utility experiments

---

## Privacy model

### Privacy unit

One dataset row is one privacy unit.

The MVP assumes one person contributes exactly one row.

### Neighboring datasets

Use **fixed-size replacement adjacency**.

Datasets \(D\) and \(D'\) are adjacent if:

- \(|D| = |D'|\), and
- they differ in at most one row.

### Public configuration

The following are public:

- schema
- numeric bounds
- categorical domains
- histogram bin edges
- dataset size
- session epsilon total
- query epsilon

Bounds must never be learned from private records.

### Clipping

For numeric value \(x\) with bounds \([L,U]\):

\[
\operatorname{clip}(x)=\min(U,\max(L,x))
\]

All numeric private queries operate on clipped values.

### Category count

For declared public category \(c\):

\[
f(D)=\sum_i \mathbf{1}[x_i=c]
\]

Sensitivity:

\[
\Delta f = 1
\]

A bare total-row count is intentionally excluded because dataset size is fixed/public in this MVP.

### Bounded mean

For bounded numeric field \([L,U]\) and fixed dataset size \(n>0\):

\[
f(D)=\frac{1}{n}\sum_i \operatorname{clip}(x_i)
\]

Sensitivity:

\[
\Delta f=\frac{U-L}{n}
\]

### Histogram

Each row contributes to exactly one public bin/category.

Under replacement adjacency, one row replacement can decrement one bin and increment another, so:

\[
\Delta_1 f=2
\]

Each released bin receives independent Laplace noise using vector \(L_1\) sensitivity 2.

Do not silently clamp negative noisy counts to zero in the core mechanism.

### Laplace mechanism

For sensitivity \(\Delta f\) and \(\epsilon>0\):

\[
b=\frac{\Delta f}{\epsilon}
\]

Release:

\[
M(D)=f(D)+\operatorname{Laplace}(0,b)
\]

Application sampling must use OS-backed randomness.

### Sequential composition

\[
\epsilon_{\text{spent}}=\sum_i\epsilon_i
\]

\[
\epsilon_{\text{remaining}}=
\epsilon_{\text{total}}-\epsilon_{\text{spent}}
\]

A query that would exceed the remaining budget must be rejected before execution.

---

## Dataset model

A dataset has:

- `dataset_id`
- `name`
- `row_count`
- `safe_for_demo`
- public schema
- server-side-only records

Numeric fields define:

- name
- numeric type
- lower bound
- upper bound
- optional public histogram bin edges

Categorical fields define:

- name
- public allowed categories

The built-in MVP dataset must be synthetic and deterministic from a recorded seed.

---

## Privacy session

A session has:

- `session_id`
- `dataset_id`
- `epsilon_total`
- `epsilon_spent`
- `epsilon_remaining`
- `strict_mode`
- query-history metadata

Sessions may be held in memory for the MVP.

Query history must not contain raw records.

In strict mode it must not contain true answers.

---

## Query behavior

Each query specifies epsilon.

Validation:

- finite
- strictly greater than zero
- no greater than remaining budget
- default educational maximum per query: `10`

### Successful query response

Return:

- query id
- query type
- dataset id
- epsilon charged
- epsilon remaining
- sensitivity
- mechanism name
- mechanism scale
- noisy result
- optional true result only when allowed
- timestamp

### Rejected query

A rejected query:

- returns a structured validation error
- does not execute the private mechanism
- does not consume budget

### Strict mode

Strict mode never returns:

- raw records
- true aggregate values
- unclipped intermediates
- random seeds

### Demo mode

Ground truth may be returned only if:

- `strict_mode == false`
- `dataset.safe_for_demo == true`

---

## Architecture

Target structure:

```text
privata/
├── AGENTS.md
├── README.md
├── SPEC.md
├── DEVELOPMENT.md
├── AGENT_PROMPTS.md
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── datasets/
│   │   ├── dp/
│   │   │   ├── clipping.py
│   │   │   ├── sensitivity.py
│   │   │   ├── mechanisms/
│   │   │   ├── queries/
│   │   │   └── accounting/
│   │   ├── services/
│   │   └── api/
│   └── tests/
│
├── frontend/
└── experiments/
```

### Dataset layer

Owns:

- schema
- public bounds/categories
- deterministic synthetic generation
- dataset registry
- trusted internal record access

Does not own privacy accounting or HTTP behavior.

### DP engine

Owns:

- clipping
- sensitivity formulas
- Laplace mechanism
- private query implementations
- privacy-session accounting types

Must remain framework-independent.

### Query service

The orchestration order is:

1. load session
2. load dataset
3. validate query against public schema
4. check epsilon budget
5. execute DP query
6. charge epsilon only after success
7. apply true-value visibility policy
8. append safe history metadata
9. return safe response

### API layer

Only:

- parses HTTP requests
- calls services
- maps domain errors
- serializes results

No privacy formulas belong in API routes.

### Experiment layer

Imports the same DP engine.

It may access synthetic true values because experiments are offline and educational.

### Frontend

Consumes backend responses as source of truth.

It may explain formulas but must not enforce privacy accounting independently.

---

## API

Suggested endpoints:

- `GET /health`
- `GET /datasets`
- `GET /datasets/{dataset_id}/schema`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/queries`
- `GET /sessions/{session_id}/history`
- `GET /experiments`
- `GET /experiments/{experiment_id}`

There must be no raw-record endpoint.

Structured error example:

```json
{
  "error": {
    "code": "BUDGET_EXCEEDED",
    "message": "Requested epsilon exceeds the remaining privacy budget.",
    "details": {
      "requested_epsilon": 0.5,
      "remaining_epsilon": 0.25
    }
  }
}
```

Errors must not reveal private data.

---

## Frontend

### Setup page

Show:

- dataset description
- public schema/bounds/categories
- strict/demo mode
- total epsilon input
- create-session action

### Query page

Show:

- total/spent/remaining epsilon
- query type
- valid fields/categories/bins
- epsilon input
- noisy result
- sensitivity
- mechanism scale
- optional true result in demo mode
- query history

### Experiments page

Show:

- privacy vs. utility
- dataset size vs. utility
- neighboring-dataset distributions
- composition/budget trace

Precomputed result JSON generated by repository scripts is acceptable for MVP.

---

## Failure semantics

### Validation failure

Examples:

- unsupported query type
- unknown field/category
- missing bounds
- invalid epsilon

Result:

- no mechanism execution
- no budget charge
- structured error

### Budget failure

Result:

- no mechanism execution
- no charge
- error includes requested and remaining epsilon

### Mechanism/internal failure

Result:

- no budget charge
- no private intermediate state in the error

---

## Threat-model boundaries

Privata demonstrates record-level differential privacy for supported aggregate releases under the documented assumptions.

It does not address:

- malicious server operators
- compromised hosts
- side channels
- multi-row contributions per person
- linkage attacks outside the DP release model
- privacy of schema/bounds/dataset size
- encrypted storage
- access control
- secure deletion
- network security
- production accounting across distributed services

---

## Acceptance criteria

The MVP is complete when:

1. all three query types work
2. bounds/categories are enforced
3. epsilon accounting prevents overspending
4. rejected queries do not spend budget
5. strict mode never returns true values
6. demo ground truth requires a safe demo dataset
7. neighboring-dataset experiment is reproducible
8. privacy-vs-utility experiment is reproducible
9. backend tests pass
10. frontend lint/typecheck/build/tests pass as configured
11. README explains privacy assumptions and limitations
12. no raw-data HTTP route exists

## Explicitly deferred

- add/remove adjacency
- arbitrary filters
- filtered mean
- SQL
- Gaussian mechanism
- delta
- advanced composition
- Rényi DP
- privacy amplification
- DP-SGD
- federated learning
- authentication
- remote sensitive-data storage
