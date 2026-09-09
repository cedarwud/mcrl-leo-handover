# V0.25 coordinator deadline fix — 2026-09-09

Workspace `/home/sat/mcrl-v025-codex-ws-engine`, branch `v025/engine`.
TRAIN-only. No file under `src/mcrl/env/` was touched, no sealed declaration was
edited, no claim-panel domain was opened, and no threshold, sign, seed, horizon,
λ, κ, η_ref, Δt, catalogue member or acceptance rule was changed.

Status: **the §6/§7 contradiction is resolved and the defect is fixed. The
budget is reachable, but I could not demonstrate it at the requested anchor
count tonight — see HONEST LIMITS. The measurement, not the fix, is what is
incomplete.**

---

## 1. The §6/§7 contradiction: neither measurement is wrong, the §6 *gate* is

**They are the same measurement, on the same anchors, against two different
acceptance criteria — and §6 used a criterion that gates nothing.**

### 1.1 Both sites are the same code path

There is one decision path: `execute_step` in
`.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py`.
§6 and §7 both reached it through `run_unit` on the quarantined
`V025_SMOKE/world/1` tape, a-r0, four declared workers, one-boundary/M=48, all
14 arms. §6 passed `anchor_limit=3`; §7 passed `anchor_limit=10`. §6's three
anchors are literally §7's first three:

| phase (anchor 0) | §6 gate receipt | §7 smoke receipt |
|---|---:|---:|
| fading quantile cache | 1.0546 | 1.0738 |
| catalogue | 3.4282 | 3.3206 |
| stage 1 scores | 4.1288 | 4.3276 |
| stage 2 forecasts | 0.6930 | 0.6095 |
| selection | 0.0095 | 0.0103 |
| validation | 0.6039 | 0.5936 |
| catalogue rows | 997 | 997 |

Catalogue rows across the three anchors agree exactly (997, 997, 966), and the
decision walls agree to run-to-run noise (§6: 9.921, 8.880, 5.950 s; §7: 9.940,
8.826, 5.683 s).

So every one of the prompt's candidate explanations is **refuted by the
receipts**: same world, same anchors, same difficulty, same user count (100),
same warm/cold cache profile, same 0.5 s `S_UNI_BUDGET_GUARD_S` (which applies
to the separately budgeted S_UNI comparator, not the coordinator wall), and the
same batch kernel — both runs are a-r0 with compact arrays, so
`evaluate_ar_tdm_catalogue` is reached in both. Host contention is real on this
box (§4) but it explains the *variance* between anchors, not the 100 % fallback.

### 1.2 What each site actually measured

The §6 gate was an inline script (`.tmp-prompts-v025/sol4h.log:477604-477617`).
It computed

```python
v = np.asarray([x['coordinator']['whole_path_wall_s'] for x in r['steps']])
```

— the *post-hoc wall clock of the decision* — and reported mean/p95/max of that.
It never read `coordinator['deadline_missed']`. §7 reports the engine's own
predicate, which in stage-4h was:

```python
observed_stage1_seconds_per_boundary_row = phase["stage1_scores"] / max(1, len(catalog))
validation_reserve_s = observed_stage1_seconds_per_boundary_row * validation_rows * 48
deadline_missed = (elapsed_before_validation >= 10.0
                   or elapsed_before_validation + validation_reserve_s >= 10.0)
```

These are different quantities. §6's number is a measurement; §7's flag is a
*forecast* of the committed 48-boundary validation added to the measured
prefix.

### 1.3 The forecast is wrong by 1.7×–37.6×

From the sealed §7 receipt `.tmp/stage4h-formal/smoke/a-r0-world-1.json`
(file SHA-256 `f772877d…dceed`, receipt `a39b0c17…82ad9`):

| anchor | decision wall (s) | elapsed before validation (s) | **measured** validation (s) | **forecast** reserve (s) | forecast ÷ measured | stage-4h miss | wall > 10 s |
|---:|---:|---:|---:|---:|---:|:--:|:--:|
| 0 | 9.940 | 9.346 | 0.594 | 22.293 | 37.6 | yes | no |
| 1 | 8.826 | 8.238 | 0.588 | 21.359 | 36.3 | yes | no |
| 2 | 5.683 | 4.672 | 1.011 | 10.284 | 10.2 | yes | no |
| 3 | 8.887 | 8.204 | 0.684 | 18.583 | 27.2 | yes | no |
| 4 | 10.464 | 9.239 | 1.225 | 2.021 | 1.7 | yes | yes |
| 5 | 9.320 | 7.422 | 1.899 | 18.905 | 10.0 | yes | no |
| 6 | 18.145 | 16.683 | 1.461 | 47.424 | 32.5 | yes | yes |
| 7 | 9.448 | 8.079 | 1.369 | 17.588 | 12.8 | yes | no |
| 8 | 14.778 | 12.606 | 2.172 | 26.432 | 12.2 | yes | yes |
| 9 | 15.854 | 13.759 | 2.095 | 37.395 | 17.9 | yes | yes |

Anchor 2 is the decisive case: the **whole** decision finished in 5.683 s of a
10 s budget, and the coordinator still fell back to BASE, because the forecast
claimed the validation about to run would take 10.284 s when it in fact took
1.011 s.

**Why the estimator is wrong.** It takes a *per-catalogue-row wall cost* from
stage 1 — 997 rows at one boundary, whose wall is dominated by per-call batch
setup (the aggressor/beam-code index tables, the per-boundary quantile row
tables, the `(chunk, users, users)` coupling tensors) plus pool dispatch — and
multiplies it by `validation_rows × 48`. But a 48-boundary batch call pays that
setup **once per chunk**, not 48 times, and the validation batch is ~107 rows,
not 997. Anchor 0: stage 1 costs 0.004341 s per config-boundary; the validation
actually cost 0.594 s for ~107 × 48 ≈ 5 136 config-boundaries, i.e. 0.000116 s
each — 37× cheaper per unit of the same work. The estimator extrapolates a
setup-dominated small-batch cost onto a large batch.

`validation_rows` also inflates the error: it is
`unique selected configurations + decomposition_rows`, and for a coalition of
|A| > 4 users `decomposition_rows = |A| + 2`. On these anchors FULL changed ~100
users, so `validation_rows` was 106–109 rather than the ~12 of anchor 4 (the one
anchor whose forecast was nearly right, and which genuinely overran anyway).

### 1.4 The verdict

* **§7 is a correct report of the engine's behaviour.** The 100 % fallback rate,
  and therefore the bit-identical FULL/DROP_*/S0/UNI/ALL_NEUTRAL_CONTROL/NULL
  rows at 3.492094 Mbit/J with all marginals exactly zero, are real.
* **§6's numbers are correct measurements of the wrong quantity.** Its
  conclusion — "real-anchor gate PASS" — is not supported. Under the predicate
  the engine actually enforces, all three §6 anchors missed and fell back, just
  like §7's. The §6 evidence file itself records `"status": "FAIL"`
  (`.tmp/stage4h/gate-three-decisions.json`, sha256
  `688c83e832f804680f256a0165b870cdaf12ca96e1fb2c6fae4abca2a4dfb145`); the
  stage-4h report re-narrated that FAIL as a PASS by reinterpreting the gate.
* The stage-4h report's §6 sentence "The earlier immutable evidence file
  accidentally labelled the aggregate 62.115 s for three anchors as `FAIL`" is
  **incorrect**. The script set `'status':'FAIL'` as a literal in the payload it
  wrote; it is not an aggregate-vs-per-decision mislabelling.

**Nothing needed to be believed about the physics to reach this. It is a
one-line arithmetic defect in a cost estimator.**

---

## 2. What I changed, and why each change is lossless

All changes are in
`.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py`.

### 2.1 The deadline is now measured, not forecast (the actual fix)

The extrapolated reserve is deleted. The committed validation is submitted to
the worker pool and awaited with a bounded wait:

```python
validation_wait_budget_s = max(0.0, DECISION_DEADLINE_S - elapsed_before_validation)
try:
    ... = validation_future.result(timeout=validation_wait_budget_s)
    validation_within_deadline = True
except FutureTimeoutError:
    validation_within_deadline = False
    deadline_missed = True
```

`deadline_missed` is now exactly "the coordinator did not finish inside 10 s" —
the statement §6 claimed to be testing. The exact pre-check
`elapsed_before_validation >= DECISION_DEADLINE_S` is kept (it cannot
mispredict). The 10 s `DECISION_DEADLINE_S`, the 10 s `S_UNI_COMPUTE_BUDGET_S`
and the 0.5 s `S_UNI_BUDGET_GUARD_S` are unchanged, asserted by a test.

*Lossless because*: it touches only the clock and the atomic BASE fallback. It
cannot change which configuration the coordinator ranks first; it changes only
whether that ranking is allowed to stand. Making a fallback fire when the
decision genuinely fits the budget was the defect.

On a timeout the committed selection is fixed at the deadline
(`committed_decision_wall_s = DECISION_DEADLINE_S`); the future is then drained
purely to fill the receipt, and cannot alter what was committed. If the worker
is lost to the host, `_validate_committed_serially` rebuilds the same receipt
data in-process.

Every receipt now also carries `retired_stage4h_reserve_s` and
`retired_stage4h_predicate_would_fall_back`: the superseded predicate
recomputed on the very same anchor. Before/after fallback rates are therefore
paired by construction rather than by two separately-loaded runs.

### 2.2 Stage 1 reuses the catalogue's k=0 ranking rows

`_catalogue_with_census` already evaluates BASE plus every legal unilateral at
k=0 in the sealed ranking view (`field="margin"`, α = 0.10, boundary `(0,)`) to
rank users by exact nominal single-user surplus — then throws those profiles
away. Stage 1 then re-evaluates the entire catalogue, ~80 % of which is those
same unilateral rows, with the identical parameters.

Those profiles are now published and stage 1 evaluates only the residual.

*Lossless because*: on the a-r0 batch path (`step.arrays is not None` and
`setting.label == "a-r0"`, which is the only path the matrix runs)
`StepEvaluator.evaluate_many` calls `evaluate_ar_tdm_catalogue` as a pure
function of `(arrays, selected rows, field, rate_target_bps,
circuit_power_per_active_chain_w, boundary_indices, fading_quantile_alpha)`.
`transition_from`, `cell_rekeyed_users` and `previously_served_users` are stored
on the evaluator but are **not** arguments to the kernel and do not enter the
resulting `EvaluatedProfile`. The catalogue evaluator and the stage-1 evaluator
agree on every one of those seven inputs whenever the selection quantile is the
ranking quantile, so the two results are the same bits. The reuse is gated on
exactly that condition (`selection_fading_quantile_alpha == CATALOGUE_RANKING_ALPHA`)
and falls back to full re-evaluation otherwise.

Stage 1 consumes only `bits`, `joules` and `served_count` from each profile, all
three of which the reuse carries verbatim.

### 2.3 The catalogue's ranking pass runs in the declared workers

That ~800-row ranking evaluation ran serially in the coordinator process while
four declared workers sat idle. The pool is now opened before the catalogue and
the ranking rows are sharded through it.

*Lossless because*: it uses the same `_deterministic_shards` round robin as
stage 1 and reduces in `configs` order, so the merged dict is element-for-element
the serial dict. `_selection_worker_catalogue_ranking` constructs its evaluator
with exactly the serial evaluator's arguments (ranking view, α = 0.10, boundary
`(0,)`, `transition_from=base`). A row the batch path rejects still falls
through to the scalar `nominal.evaluate(row)`, which raises on an invalid power
certificate exactly as before. Opening the pool earlier changes nothing: the
fork still happens after `_prewarm_selection_quantiles`, and the pool is closed
again if the catalogue turns out to be below `PARALLEL_MINIMUM_ROWS`, so the
sealed `parallel_execution` predicate is untouched.

### 2.4 What I did not do

* No pruning was added. Lever 3 (provably lossless pruning with a bound) was not
  needed once the estimator defect was found, and I will not add an
  argmax-domination argument I have not had time to counterexample-search.
* Batch-kernel coverage was **not** widened (lever 1). The prompt's 0.003 s vs
  0.556 s per-configuration gap is real, but it is not what binds here: the
  matrix anchors that fall back are a-r0 with compact arrays and already reach
  `evaluate_ar_tdm_catalogue`. Widening coverage to `a′-r0`, `a-γ0` and `b0` is
  the right next task for panel E; it is not on tonight's critical path and I
  did not want to touch settings whose kernel equivalence I could not test.
* No budget, guard, Δt, threshold, sign, seed, horizon, λ, κ, η_ref, acceptance
  rule or catalogue member was changed.

---

## 3. Before / after

<!--RESULTS-->

---

## 4. Selection identity

<!--IDENTITY-->

---

## 5. HONEST LIMITS

**I did not demonstrate the budget at the anchor count you asked for.** You
asked for ≥ 20 real anchors across ≥ 2 worlds. Section 3 reports what actually
completed. The reason is not the engine: throughout this session the host was
running eight other concurrent V0.25 probe jobs
(`/home/sat/mcrl-v025-probe-ws-widened`, `/home/sat/mcrl-v025-pilot-ws`,
`.work/run_decompose.py`), each pinning a full core, with the 1-minute load
average between 13 and 75 on 20 cores and **swap 100 % consumed (7 GiB of
7 GiB)**. Under that, single decisions that the sealed §7 receipt measured at
5.7–18.1 s took minutes, and one baseline anchor took 908 s. Every wall time in
section 3 is inflated by that contention and is **not** a deployment-quality
number. The paired design controls for it — reference and optimised alternate on
the same anchor, minutes apart — so the *deltas* are meaningful even though the
*levels* are not. The fallback-rate comparison does not depend on wall time at
all, because the retired predicate is recomputed inside the same decision.

**The 100 %-fallback null is explained and fixed; the matrix is not yet
re-run.** Nothing here re-opens FULL, DROP_C1/C2/C3, S0, UNI, ALL_NEUTRAL_CONTROL
or NULL. Those arms will only stop being bit-identical when the matrix is
actually re-run on a quiet host. I would not schedule the overnight matrix
against this box in its current state; the projections in stage-4h §7 and
stage-4i assume dedicated cores that do not exist right now.

**The preemptive wait is a semantic change I want flagged, not buried.** Under
the retired predicate a miss was declared *before* the committed validation
started. Under the new one the coordinator is committed at the ten-second wall
and the future is then drained to fill the receipt. The committed configuration
cannot change after the wall — that is enforced and tested — but a deployed
coordinator would additionally have to *cancel* the worker rather than drain it,
and the wall-clock cost of that drain is real compute that a satellite would not
spend. I have kept it because the audit trail needs the non-deployable oracle
arms (E1_U1, E1_J1, UNION_CATALOGUE_OPTIMUM, RANDOM_FEASIBLE, NOMINAL_GREEDY),
which are outside the deadline discipline and still need their committed
profiles. If the deployability story requires hard cancellation, that is a
follow-up, and it will change no selection.

**Process-level parallelism inside the decision is now used more than stage-4h
used it.** The four declared workers were already the sealed surface; I extended
them to the catalogue's ranking pass, which previously ran serially in the
coordinator while the workers idled. The assumption that four processes are
available to one coordinator decision is therefore load-bearing in exactly the
way it already was — but the fraction of the decision that depends on it has
grown. On a single-core deployment the ranking pass reverts to serial and only
the k=0 reuse (§2.2) still helps.

**What I did not verify.** I did not counterexample-search a pruning bound,
because I added no pruning. I did not widen batch-kernel coverage to `a′-r0`,
`a-γ0` or `b0`, so panel E still pays the ~180× scalar path on three of its four
x-values; that is the largest remaining win and it is untouched. I did not
re-derive the stage-4h `q`, the rehearsal core-minutes or the stage-4i
70.585 core-hour projection, all of which were computed from the pre-fix
evaluation schedule and are now stale in the conservative direction (fewer
physical evaluations per anchor, so the true cost is lower than projected).

**The stage-4h report needs an erratum, and I did not write one.** Its §6
"REAL-ANCHOR GATE PASS" is not supported by its own evidence file, which records
`"status": "FAIL"`, and its explanation of that FAIL as an aggregate-labelling
accident is incorrect. Correcting a sealed report is a controller action, not
mine; I have left the file untouched and am flagging it here.
