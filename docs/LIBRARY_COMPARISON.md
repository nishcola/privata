# OpenDP validation comparison

This document records a validation-only comparison between Privata and
[OpenDP 0.15.1](https://pypi.org/project/opendp/0.15.1/). It does not replace
any Privata implementation. OpenDP is a backend development dependency used
only by `experiments/library_comparison.py` and its tests; `backend/app/dp`
does not import it.

Run the comparison from the repository root after installing backend development
dependencies:

```powershell
.\backend\.venv\Scripts\python.exe experiments\library_comparison.py --output-dir experiments\output --trials 100000
```

The command writes `library_comparison.json` and `library_comparison.png`.
They retain public configuration and aggregate scale estimates, not records or
trial-level releases.

## What is aligned

| Topic | Privata | OpenDP comparison configuration |
| --- | --- | --- |
| Privacy unit | One row, with one person contributing one row | One changed microdata record via `unit_of(changes=1)` |
| Adjacency | Fixed-size replacement: at most one row changes | `ChangeOneDistance` with distance 1 |
| Public inputs | Schema, bounds, domains, bins, and dataset size | Sensitivities supplied from the same public configuration |
| Privacy definition | Pure epsilon-DP | `MaxDivergence` Laplace measurement |
| Scalar aggregate metric | Absolute distance | OpenDP `absolute_distance(float)` |
| Histogram aggregate metric | Vector L1 distance | OpenDP `l1_distance(float)` |

OpenDP distinguishes its bounded `ChangeOneDistance` metric from its usual
unbounded `SymmetricDistance` metric. The latter expresses additions/removals,
not Privata's fixed-size replacement model. Results using `SymmetricDistance`
are therefore not equivalent to this comparison and must not be substituted
for it. OpenDP documents that bounded metrics count changed rows and that one
edit can correspond to two additions/removals under the unbounded metric.
([OpenDP bounded metrics](https://docs.opendp.org/en/stable/api/user-guide/transformations/index.html))

## Sensitivity and calibration

The comparison has no private dataset input. It gets the following values from
Privata's existing sensitivity and `laplace_scale` functions, then constructs
OpenDP measurements over aggregate values with the matching metric and scale.

| Query configuration | Public sensitivity | Epsilon | Expected scale |
| --- | ---: | ---: | ---: |
| Declared-category count | 1 | 1 | 1 |
| Bounded mean, `[20000, 200000]`, `n = 500` | 360 | 1 | 360 |
| One-bin-per-row histogram | L1 = 2 | 1 | 2 |

Both calculations use `scale = sensitivity / epsilon`. For each row, the
harness asks OpenDP's privacy map for the epsilon produced by the specified
sensitivity and checks that it is 1. OpenDP describes this map as
`epsilon = sensitivity / scale` for its Laplace measurement.
([OpenDP Laplace mechanism](https://docs.opendp.org/en/stable/theory/dp-with-opendp.html))

This is not an independent OpenDP implementation of Privata's clipping,
category validation, histogram partitioning, or budget accounting. Those are
already covered by Privata's own tests. The external check validates the
calibrated scalar and vector Laplace releases once the public sensitivity has
been established.

## Empirical output scale

For each query configuration and each library, the script draws 100,000 noisy
releases centred at zero. It estimates scale using:

$$
\hat b = \frac{\operatorname{median}(|\text{noise}|)}{\ln 2}.
$$

The run fails when either estimate differs from the theoretical scale by more
than 10%. This is a broad Monte Carlo check, not a proof of differential
privacy. The proof still depends on Privata's documented adjacency and
sensitivity argument. The JSON reports estimates and relative errors only;
it does not persist sampled releases.

Privata samples floating-point noise with its standard-library implementation.
OpenDP's floating-point Laplace mechanism has its own numeric granularity and
sampling implementation. Independent random draws and those implementation
details mean individual releases and empirical estimates are not expected to
match exactly. OpenDP's additive-noise documentation describes the supported
aggregate domains and metrics.
([OpenDP additive noise mechanisms](https://docs.opendp.org/en/stable/api/user-guide/measurements/additive-noise-mechanisms.html))

## API ergonomics

Privata exposes a narrow application-level interface: a typed query request,
public schema validation, a session epsilon budget, and safe response metadata.
The caller chooses one of three supported aggregate queries; the engine applies
the documented model.

OpenDP exposes lower-level compositional primitives. A caller explicitly builds
domains, dataset and aggregate metrics, transformations, measurements, and
privacy-map checks. This gives OpenDP the flexibility to express other privacy
models, but requires the caller to configure the metric and stability path
correctly. The comparison uses OpenDP's explicit bounded metric only to align
the adjacency statement, and its scalar/vector Laplace measurements only to
check calibration. It does not make a claim that the two application APIs, or
their complete implementations, are identical.
