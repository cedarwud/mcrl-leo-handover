# Design audit: the four numbers

`DIAGNOSTIC_NOT_CLAIM` — 2026-09-09

This is an audit of existing statistical machinery and existing on-disk evaluation artefacts. It is not an experiment, and none of the pilot values below is claim evidence.

## Q1. Was the measured coverage marginal or simultaneous?

**Answer: marginal.** More precisely, the reported 0.863–0.920 is the pooled average of the three contrasts' individual interval-coverage indicators. It is not the probability that all three intervals cover simultaneously. Therefore `0.95^3 = 0.857` is not the relevant benchmark: the reported values are genuine average marginal undercoverage against 0.95. The calibration output does not retain three separate arm-specific coverage rates, so this audit cannot say whether the undercoverage is equal across contrasts.

The reported values are in `/home/sat/mcrl-v025-pilot-ws/V025-STAGES-6-8-CONTRACT-v1.1-AMENDMENT-2026-09-09.md:3-12`. The lines that decide the coverage quantity are `/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/acceptance.py:155-165`:

```python
for arm in DROP_ARMS:
    interval = contrasts[arm]["bootstrap"][
        "central_95_percentile_intervals"
    ]["ee_relative"]
    covered += int(
        interval is not None and interval[0] <= 0.02 <= interval[1]
    )
...
"interval_coverage": _binomial_uncertainty(covered, repetitions * 3),
"conjunction_power": _binomial_uncertainty(
    conjunction_successes, repetitions
),
```

Each interval is counted separately and the denominator is `3 * repetitions`. By contrast, simultaneous success is used only for power at `/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/acceptance.py:149-154`:

```python
claim = merged["claim"]
passed = tuple(
    bool(claim["per_contrast"][arm]) for arm in DROP_ARMS
)
conjunction_successes += int(all(passed))
```

**“95% lower bound” means the lower endpoint of an equal-tailed two-sided 95% percentile interval, with a 2.5% lower-tail allowance.** It is not a one-sided 95% bound with a 5% lower tail. The interval is defined at `/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/merge.py:215-221`:

```python
lower, upper = np.quantile(
    np.asarray(values, dtype=np.float64), [0.025, 0.975], method="linear"
)
return float(lower), float(upper)
```

The decision then uses that lower endpoint at `/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/merge.py:439-452`:

```python
intervals = primary["central_95_percentile_intervals"]
...
ee = intervals["ee_relative"]
...
and ee[0] > EE_MARGIN_RELATIVE
```

The later v1.2 amendment asks T3 to additionally report the one-sided bound's coverage (`V025-STAGES-6-8-CONTRACT-v1.2-AMENDMENT-2026-09-09.md:8`), but the generating code audited here contains no 5th-percentile decision bound or corresponding one-sided calibration result.

## Q2. Is the “5% date standard deviation” raw efficiency or the paired contrast?

**Answer: it is the paired log contrast.** The simulation draws a separate date effect for each of the three contrasts, then adds it directly to

`log(1 + true relative gain) + date effect + learner-seed effect`.

It is not a 5% date-to-date SD of raw EE that might cancel after pairing. At `/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/acceptance.py:99-125`:

```python
for date_sd in (0.05, 0.03):
    ...
    date_effect = rng.normal(0.0, date_sd, (3, 160))
    seed_effect = rng.normal(0.0, 0.01, (3, seed_count))
    ...
    energy = (0.75, 1.25)[world] * (
        1.0 + 0.05 * ((date_index + seed_index) % 3)
    )
    endpoints = {"FULL": (100.0 * energy, energy)}
    for contrast_index, arm in enumerate(DROP_ARMS):
        log_effect = (
            math.log1p(0.02)
            + date_effect[contrast_index, date_index]
            + seed_effect[contrast_index, seed_index]
        )
        endpoints[arm] = (
            100.0 * energy / math.exp(log_effect),
            energy,
        )
```

These endpoints make `EE_FULL = 100` and `EE_DROP = 100 / exp(log_effect)`, so `log(EE_FULL) - log(EE_DROP) = log_effect`. Thus `date_sd=0.05` is exactly an SD of 0.05 log units in the paired contrast (approximately a 5% multiplicative SD). It is also contrast-specific: the `(3, 160)` draw does not impose one common date shock across all three contrasts.

**Actual paired-date SD: not estimable from the real evaluation artefacts on disk.** The only completed real evaluation and the later epoch-trend diagnostic both use `V025_PROBE/world/3`, hence one date. The minimal report states at `/home/sat/mcrl-v025-pilot-ws/V025-PILOT-MIN-REPORT-2026-09-09.md:7`:

```text
Evaluation worlds ['V025_PROBE/world/3']; 5 anchor steps x nearest-eligible
carrier only; learner seeds ['V025_LEARNER/seed/1',
'V025_LEARNER/seed/2'] (2)
```

The later diagnostic confirms that it reused the same world, anchors and two seeds (`/home/sat/mcrl-v025-pilot-ws/EPOCH-TREND-2026-09-09.md:47-52`). A sample SD across one date is undefined. The observed one-date pooled log contrast at epoch 200 is 0.37596 under `P-a0` and 0.37814 under `P-u`; the epoch-2000 diagnostic gives -0.29095 and -0.30655, respectively. Those values show checkpoint sensitivity on the same date and cannot estimate date-to-date variance. Consequently there is no measured value to compare numerically with the assumed 0.05: **we never measured the paired log-contrast SD across dates.**

## Q3. How many independent date blocks do we actually have?

**Answer: one completed real evaluation date block.** It is `2025-11-16`, containing one distinct world, `V025_PROBE/world/3`. Anchors, the two learner seeds, the two catalogue anchors and repeated checkpoint evaluations do not create additional date blocks.

The production definition of the cluster date is explicit at `/home/sat/mcrl-v025-pilot-ws/src/mcrl/physics_v025/provider_legacy.py:387-389`:

```python
def cluster_identity(self, *, world_seed: int) -> tuple[str, int]:
    world = self._ensure(world_seed)
    return world.start_utc.date().isoformat(), world.training_seed
```

The merger clusters on date × learner seed, not world or anchor, at `/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/merge.py:798-803`:

```python
cluster = clusters.setdefault((unit.tle_date, unit.learner_seed), {})
for arm in POLICY_ORDER:
    arm_rows = sorted(
        (row for row in steps if row.get("arm") == arm),
        key=lambda row: int(row["step_index"]),
    )
```

The completed pilot emitter records the fields used for this census at `/home/sat/mcrl-v025-pilot-ws/scripts/run_v025_pilot_c3.py:1734-1749`:

```python
records.append(
    {
        "world_id": domain,
        "world_seed": tape.seed,
        ...
        "catalogue_anchor": variant,
        "learner_seed": seed,
        "arm": arm,
        ...
        "bits": profile.bits,
        "joules": profile.joules,
    }
)
```

The pilot receipts unfortunately omit `tle_date`, unlike the production step serializer (`src/mcrl/stagec_v025/evaluation.py:536-548`). I therefore reconstructed `2025-11-16` from the deterministic provider using an isolated copy of the clean source at Git commit `857b4bd1c1cc05f5bca0f883af9e028ff825d6df` and the required Python interpreter. This date is reproducible from the world seed, but it is not directly attested in the pilot JSONL. The evaluated raw receipt file is `/home/sat/mcrl-v025-pilot-ws/artifacts/v025-pilot-min-20260909-PILOT_NOT_CLAIM/evaluation/PILOT_NOT_CLAIM-raw-receipts.jsonl`, SHA-256 `372b1f168c901470b9d3aafd457abbdbd0d5033e0f59966b15166a328d428612`.

### Energy shares

The following recomputation uses the completed minimal evaluation (epoch 200), grouping its 100 raw receipts by catalogue anchor, arm and learner seed and summing `joules`. Each catalogue anchor is shown separately so duplicated comparator evaluations are not silently double-counted. Seed 1 is integer seed `6407676579069309528`; seed 2 is `925030429265975792`.

| Catalogue | Arm | Total J | Date 2025-11-16 | Seed 1 | Seed 2 | Effective dates `1 / sum(w_date^2)` |
|---|---|---:|---:|---:|---:|---:|
| P-a0 | FULL | 39,153.8356 | 100.000% | 50.000% | 50.000% | 1.000 |
| P-a0 | DROP_C3 | 52,519.7162 | 100.000% | 61.780% | 38.220% | 1.000 |
| P-a0 | BASELINE | 66,931.2858 | 100.000% | 50.000% | 50.000% | 1.000 |
| P-a0 | S0 | 65,498.6001 | 100.000% | 50.000% | 50.000% | 1.000 |
| P-a0 | S_UNI | 66,931.2858 | 100.000% | 50.000% | 50.000% | 1.000 |
| P-u | FULL | 39,153.8356 | 100.000% | 50.000% | 50.000% | 1.000 |
| P-u | DROP_C3 | 52,566.4979 | 100.000% | 61.744% | 38.256% | 1.000 |
| P-u | BASELINE | 66,931.2858 | 100.000% | 50.000% | 50.000% | 1.000 |
| P-u | S0 | 65,498.6001 | 100.000% | 50.000% | 50.000% | 1.000 |
| P-u | S_UNI | 66,931.2858 | 100.000% | 50.000% | 50.000% | 1.000 |

There are no completed real evaluation receipts for `DROP_C1`, `DROP_C2` or `ALL_NEUTRAL_CONTROL`; the report says those arms were skipped at `V025-PILOT-MIN-REPORT-2026-09-09.md:114-115`. Their date/seed energy weights therefore do not exist. The planned panel of “approximately 160 claim dates” in the design contract is a plan, not an observed panel (`V025-STAGES-6-8-CONTRACT-v1.1-AMENDMENT-2026-09-09.md:14`). Likewise, T3's `D000`–`D159` are synthetic effect labels, not 160 observed ephemeris dates. No claim-panel evaluation artefact was found.

## Q4. Does the power plateau exceed simulation noise?

**Answer: no.** `N = 200` Monte Carlo repetitions per date-SD × seed-count cell, not 1,000. The reported 16- and 24-seed estimates are both exactly 0.675 before rounding to 0.68 (`V025-STAGES-6-8-CONTRACT-v1.1-AMENDMENT-2026-09-09.md:3,9-10`). With `p = 0.675` and `N = 200`,

`MCSE = sqrt(0.675 * 0.325 / 200) = 0.03312`, or 3.31 percentage points.

The corresponding normal 95% half-width is 6.49 points, which is the reported ±0.065. The observed difference is zero. Treating the sequential, disjoint simulation batches as independent gives `SE(difference) = sqrt(2) * 0.03312 = 0.04684` and an approximate 95% interval for the difference of ±9.18 percentage points. The estimates are not distinguishable, and the equality does not establish a power ceiling.

The repetition count and loop are at `/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/acceptance.py:84-105`:

```python
def crossed_inference_calibration(
    *,
    repetitions: int = 200,
    bootstrap_draws: int = 99,
    rng_seed: int = 20260908,
) -> dict[str, object]:
    ...
    if repetitions < 200:
        raise ValueError("T3 calibration requires at least 200 Monte Carlo replications")
    ...
    for seed_count in (5, 12, 16, 24):
        conjunction_successes = 0
        covered = 0
        for repetition in range(repetitions):
```

The uncertainty calculation is at `acceptance.py:15-23`:

```python
rate = successes / trials
half_width = 1.96 * math.sqrt(max(rate * (1.0 - rate), 0.25 / trials) / trials)
```

No calibration JSON or named `V025-STAGEC-BUILD3-REPORT-2026-09-08.md` was found in either permitted source workspace. Therefore the exact `135/200` successes is uniquely implied by `N=200` and the reported exact estimate 0.675, but is not directly serialized in an available output artefact.

**The code defines the conjunction as the complete success event: all three efficiency conditions and all three QoS non-inferiority conditions.** At `/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/merge.py:439-455`:

```python
ee = intervals["ee_relative"]
availability = intervals["availability_difference"]
handover = intervals["handover_relative"]
phi = intervals["phi_cost_relative"]
per_contrast[arm] = bool(
    ee is not None
    and availability is not None
    and handover is not None
    and phi is not None
    and not any(undefined.values())
    and ee[0] > EE_MARGIN_RELATIVE
    and availability[0] > AVAILABILITY_MARGIN
    and handover[1] < HANDOVER_RELATIVE_MARGIN
    and phi[1] < PHI_COST_RELATIVE_MARGIN
)
```

But the T3 generator makes QoS perfect and identical across arms. `/home/sat/mcrl-v025-pilot-ws/src/mcrl/stagec_v025/evaluation.py:699-720` constructs the shared template with:

```python
full_outcome = StepOutcome(
    ...
    complete_service=(True,),
    decoding_user_seconds=1.0,
    useful_user_seconds=1.0,
    opportunity_user_seconds=1.0,
    jointly_legal=True,
    ...
)
production_template = _step_payload(...)
```

Then `evaluation.py:722-741` clones that template to every arm and changes only bits, joules, the energy ledger and an attribution flag. So the complete claim path is exercised syntactically, but only efficiency is stochastic and capable of failure. Numerically, 0.675 is efficiency-conjunction power under perfect QoS; it is an optimistic upper bound on complete-claim power whenever real QoS can fail.

## Audit provenance and workspace limitation

The research workflow kept every substantive conclusion tied to primary on-disk code or receipts. The settling source files were clean relative to pilot-workspace commit `857b4bd1c1cc05f5bca0f883af9e028ff825d6df` when inspected; the relevant source SHA-256 values were `acceptance.py` `61e1e0840fb0341a2735b3dd449824ee6bfa4b244d5c13909124832e479b249b`, `merge.py` `07e3b753be102ec4e7fc71679ec6bb1654cb5162535acbed6171f21bad4b77ad`, `evaluation.py` `40c24c1818ed059faef4b1f68fe9bbfe4eea0334c926395a7df2ee0da9654c0c`, and `run_v025_pilot_c3.py` `95103bb96caaa130659fa0d509f19409574b406798a173e278a7d9dac12b7435`. All source workspaces were read-only, and code/data needed for computation was copied before execution. The requested empty initialization commit could not be created: the design workspace arrived with `.git` mounted read-only by the sandbox, and `git init` failed while trying to lock `.git/config`. This report itself was still writable in the workspace root.

**Bottom line.** The audit does not support seed count as the diagnosed problem: the 16-versus-24 equality is well inside Monte Carlo noise. It does establish a calibration problem (marginal undercoverage), an evidence/date-block problem (the assumed paired-date SD has never been measured and the completed real evaluation has one effective date), and a claim-structure problem (the quoted power makes QoS deterministic, so it is an upper bound for the real conjunction). Of those, the empirical bottleneck is the date structure, while calibration and full-claim power must also be repaired or honestly qualified; no sample-size recommendation is made here.
