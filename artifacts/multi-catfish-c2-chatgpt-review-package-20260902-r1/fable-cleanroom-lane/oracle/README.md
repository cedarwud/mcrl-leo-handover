# V0.8 Stage-1b C2 formula/oracle interaction screen

Everything for this screen lives under

```
SCRATCH=/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/d47a2ac0-70e1-49ca-b412-995b22bcb231/scratchpad/oracle
```

Nothing inside `/home/u24/papers/mcrl-leo-handover` was created, edited, staged
or committed, and `~/demo/tle_data` was only read (hard-linked into a
`tempfile.TemporaryDirectory`, exactly as `screen._frozen_archive` does).

* Runner: `SCRATCH/run_v08_c2_oracle_screen.py`
* Smoke output: `SCRATCH/smoke-20260902/{result.json,rows.jsonl}` (log:
  `SCRATCH/smoke-20260902.log`)
* `run` shape check (2 worlds, so the bootstrap path executes):
  `SCRATCH/dev-run-bootstrap/{result.json,rows.jsonl}`
* Single-arm `run` check: `SCRATCH/dev-1arm/`

All line references below are into `run_v08_c2_oracle_screen.py`.

---

## 1. Commands

Always use the repo virtualenv interpreter.

```bash
PY=/home/u24/papers/mcrl-leo-handover/.venv/bin/python
cd $SCRATCH

# engineering smoke: seed 2026090299 only, lineage 2026092101 only, all 8 arms
$PY run_v08_c2_oracle_screen.py smoke \
    --output-dir $SCRATCH/smoke-20260902 \
    --contract-sha256 SMOKE_UNSEALED_20260902

# the real screen (controller freezes the contract first, then launches this)
$PY run_v08_c2_oracle_screen.py run \
    --seeds 2026090221 2026090222 2026090223 2026090224 2026090225 2026090226 \
    --lineages 2026092101 2026092102 2026092103 \
    --arms P1 P2 P3 P12 P13 P23 P123 MAIN \
    --output-dir $SCRATCH/<block-dir> \
    --contract-sha256 <frozen contract sha256>
```

`run` has NOT been executed on the preregistered block `2026090221..2026090226`.
It has only been exercised on engineering seeds (`2026090298`, `2026090299`),
once with a single arm and once with five arms (`P123 P13 P12 P23 MAIN`) over
two worlds — the latter to make the paired-world bootstrap, the per-world
contrasts and the per-lineage contrasts actually execute. Both completed with
exit 0. The `2026090299` rows of that `run` reproduce the smoke's numbers
exactly (P123 1.10870e+08, P13 9.82310e+07, P12 1.10988e+08, P23 1.09597e+08,
MAIN 9.03555e+07 bit/J), which is the cross-run determinism check and also
confirms the keyed field does not depend on the arm set.

Other flags (all optional, with the frozen defaults of the five-arm runner):
`--tle-root`, `--prereg`, `--gate-dir`, `--source-dir`, `--v03-root`,
`--main-dir`, `--source-closure {require,receipt-only}`.

`--contract-sha256` is embedded verbatim into `result.json` as
`contract_sha256`; it is never parsed.

Outputs written to `--output-dir`: `result.json` (pretty, sorted keys) and
`rows.jsonl` (one canonical JSON row per episode). `result.json` also carries
`code_file_sha256` — the sha256 of the runner file itself.

---

## 2. Arms and the one-argmax contract

`ROUTE_NAMES = ("Q1", "Q2S", "Q3")`, `ACTIVE_ROUTES` at L114-L122:

| arm | summed surfaces |
|---|---|
| `P1` | Q1 |
| `P2` | Q2* |
| `P3` | Q3 |
| `P12` | Q1 + Q2* |
| `P13` | Q1 + Q3  (the existing DROP_C2 arm) |
| `P23` | Q2* + Q3 |
| `P123` | Q1 + Q2* + Q3 |
| `MAIN` | frozen Main baseline, one row per world, no initialization axis |

`select_actions` (L262-L297) is a line-for-line mirror of
`five_arm.route_actions`: sum the active surfaces left-to-right in the declared
`ROUTE_NAMES` order, then one `argmax` over `np.where(legal, scores, -inf)`.
Illegal actions get `-inf` from the mask, not from the surface, so the surfaces
themselves stay finite (`Q2*` is set to `0.0` on illegal entries at L585).

Q1 and Q3 come from `trainer.q_values_by_route(states_v03, states_v04, masks)`
(L830-L832). **The learned Q2 is bound to `_q2_old` and immediately
discarded** — it never enters a score, a sum, or a diagnostic. `result.json`
records `learned_q2_used: false`.

---

## 3. The oracle target, exactly as implemented

`oracle_q2_star`, L441-L610. Everything is vectorised over `(U, 28)`; the only
Python loops are the per-user segment lookup (L502-L513) and the frozen-context
tally (`_frozen_context`, L373-L438).

Per decision step `t`, for user `u` and legal action `a` with physical pair
`(s_a, c_a)` from `observation.candidates.slot_tables[u]`:

**Current geometry (`k = 0`).** `theta_a(0)` is read from
`observation.candidates.off_axis_deg`, laid out into the 28-wide action order
exactly as `StepEnvironment._observe` does (`_theta0_deg`, L306-L317).
`G_a(0) = transmit_gain_linear(theta_a(0))`, masked to legal actions (L465-L466).
`slant0`/`elevation0` are the `(U, L)` candidate values repeated over the seven
beam slots (L468-L470), and
`path_a(t) = link_power_factor(slant0, elevation0, _RX_GAIN_MAX_LINEAR, shadow_fading_db=0.0)`
(L471-L480).

**I + N, frozen at decision time** (L482-L497):

```
I_a + N  =  p0 * G_a(0) * path_a(t) / observation.candidate_sinr[u, a]
```

with `p0 = SEGMENT_START_POWER_W = 0.825 W`. If `candidate_sinr[u,a] <= 0` for a
legal action, the entry falls back to `N = noise_power_w(BEAM_BANDWIDTH_HZ) =
5.5754e-13 W` and is counted in `oracle_diagnostics.nonpositive_candidate_sinr`
(0 in the smoke). Same guard if the quotient is non-finite or non-positive.

**Segment start gain** (L499-L513). `start_a = _segments[u].start_transmit_gain`
when the action continues the user's current segment — same `norad_id` and
`cell_id`, and `_previous_association[u] is not None`, the exact conjunction
`step.py:776-782` uses — else `start_a = G_a(0)`.

**Per offset `k = 1, 2, 3`** (L536-L584):

* `satellite_ecef_at(k)` -> `{norad: ecef_km}` (`_positions_for_offset`,
  L325-L336), gathered into `(U, 28, 3)` by NORAD id with a "tracked and
  finite" mask (`_gather_positions`, L338-L350).
* `_geometry` (L352-L370) mirrors `pointing.candidate_geometry`:
  `theta_a(t+k) = angle_between_deg(sat, cell_centre, user)`,
  `slant = |r_sat - r_user|`, elevation from the user's local up vector. Cell
  centres are `driver.grid.centers_ecef_km[cell_id]` (L528-L530).
* `G_a(k) = transmit_gain_linear(theta_a(t+k))`;
  `p_a(k) = p0 * start_a / G_a(k)` (L541-L552).
* `feasible_a(k) = usable and (G_a(k) > 0) and (p_a(k) <= 1.65)` (L553).
  **Censoring**: `alive &= feasible_k` (L554), so the first infeasible offset
  zeroes `R_a` and `P_a` for that `k` and every later `k`.
* `path_a(t+k) = link_power_factor(slant_k, elevation_k, _RX_GAIN_MAX_LINEAR,
  shadow_fading_db=0.0)` (L563-L571).
* Focal rate (L572-L575):
  `R_a(k) = (B^w / (n_a + 1)) * log2(1 + p0*start_a*path_a(t+k) / (I_a+N))`
  with `B^w = BEAM_BANDWIDTH_HZ = 1.6667e8 Hz`. There is no separate `G^T`
  factor in the numerator: inside a segment `p*G^T = p0*G(theta(tau)) =
  p0*start_a` is the telescoped identity of eq. (3.12).
* Focal frozen-context marginal power (L576-L582):
  `P_a(k) = Psup(max(m_a, p_a(k))) - Psup(m_a) + [n_a == 0] * (0.338 + [not sat_active_a] * 0.200)`
  where `Psup(p) = p / xi(p)` goes through the live
  `link_budget.pa_efficiency` + `supply_power_w` (`_supply_power_w`, L248-L258)
  and `Psup(0) = 0`. Numerically `Psup(p) = 6.5264*sqrt(p)` on this path — the
  helper returns `6.5264036` for `p = 1 W`.
* Accumulate (L583):
  `ZETA2*_a += dt * R_a(k) - lambda0 * dt * P_a(k)`, `dt = 30.08 s`
  (`DECISION_STEP_S`, read live from
  `driver.config.ephemeris.time_step_s`).

Finally `Q2*(s,a) = ZETA2*_a / kappa_bits` (L588), zeroed on illegal actions.

**Frozen non-focal context** (`_frozen_context`, L373-L438), read from the last
committed `StepOutcome` (`environment._last_outcome`):
`n_a` = number of **non-focal** users served last step on `(s_a, c_a)`;
`m_a` = the max `link_power_w` among them (0 when `n_a == 0`);
`sat_active_a` = whether `s_a` carried any non-focal served user. The focal
user's own contribution is removed from its own row via a top-1/top-2 tally, so
`m_a` is a genuine leave-one-out maximum. At `t = 0` there is no previous
outcome: every beam is treated as empty (`n = 0`, `m = 0`, satellite inactive)
and the step is counted in `oracle_diagnostics.step_zero_context_steps`.

**Sealed multipliers** (L160-L175, asserted at L1665-L1679):

| constant | value | hex | source |
|---|---|---|---|
| `lambda0` | 84994621.12635651 bit/J | `0x1.443a8f481639ap+26` | `.scratch/c3-v04/run_v04_c3_source.py:LAMBDA_BITS_PER_J` (L102) — cross-checked equal to `src/mcrl/runtime/ee_axis_v07_c2_d2.py:D2_LAMBDA_BITS_PER_J` (L70) |
| `kappa_bits` | 10097071012.757404 | `0x1.2cea89d260f2ap+33` | `.scratch/c3-v04/run_v04_c3_source.py:KAPPA_BITS` (L101) |

`lambda0` is never recomputed from new outcomes. `kappa_bits` is asserted equal
to the source-runner constant for both `gate._config_pair()[1].kappa_bits` and
every loaded `trainer.v04_config.kappa_bits`.

---

## 3b. The OPS-3 variant surface (Addendum A)

Frozen text: `../contracts/V08-C2-STAGE1B-ADDENDUM-OPS3-VARIANT-2026-09-02.md`
(sha256 `b538932006f7e597ee199fb0701a4473587afa81b4580ca76e1dff13f9ea7046`).
Implemented in the same `oracle_q2_star` (L483-L720), which now returns both
surfaces from one geometry pass.

    H_t      = min(3, 9 - t)                          (L591; Z = 0 when H_t = 0)
    chi_a(h) = 1[G_a(h) > 0] 1[p_a(h) <= 1.65] 1[elev_a(h) > 0 deg]   (L621)
    Z_a      = (1/H_t) sum_{h=1..H_t}
                 [ chi_a(h) dt (R_a(h) - lambda0 P_a(h))
                   - (1 - chi_a(h)) kappa ]           (L665, L674)
    Q2*_OPS3 = Z_a / kappa                            (L680)

`p_a(h)`, `R_a(h)`, `P_a(h)`, the frozen background, `lambda0`, `kappa`, `dt`
and the segment start gain are **the same arrays** H-A consumes: the per-offset
raw surplus `surplus_k` is computed once and the two routes differ only in how
they aggregate it (H-A multiplies by the running `alive` censor; OPS-3 selects
on `chi_k` and adds `-kappa` otherwise). That shared construction is what makes
the self-check below exact rather than approximate.

The four declared differences from H-A, all implemented and nothing else:
`1/H_t` averaging instead of a sum; an explicit `-kappa` per projected-outage
offset instead of censoring to zero; truncation of offsets past the episode
end; an above-horizon indicator inside `chi`.

The reference-row subtraction `Z_a - Z_{a^M}` is **not** applied to the
deployed surface — it is a per-state constant that cannot move an argmax. It is
reported as a diagnostic only (`_ops3_reference_delta`, L862-L901): the frozen
Main policy is queried through the authoritative read-only
`runtime.main_actions` seam to recover `a^M`, and its action is never committed.
For that diagnostic alone the Main checkpoint is loaded whenever an OPS-3 arm
runs; `result.json` records `main_loaded_for_ops3_reference_diagnostic`.

Arms: `O2 = Q2*_OPS3`, `O12 = Q1+Q2*_OPS3`, `O23 = Q2*_OPS3+Q3`,
`O123 = Q1+Q2*_OPS3+Q3`. `ROUTE_NAMES` is now
`("Q1", "Q2S", "Q2S_OPS3", "Q3")`; every arm still goes through the same single
masked argmax in `select_actions`.

**Self-check (Addendum A):** at anchors with `H_t = 3` where every `chi_a(h) = 1`
(so H-A is also uncensored), `Q2*_OPS3` must equal `Q2*_HA / 3`. Measured max
relative error **2.55e-16** over 54 601 legal actions in the development check
and reported per run as `ops3_ratio_self_check` in `result.json`.

**H-A regression check:** after the refactor, P123 and P13 on the smoke world
reproduce their pre-refactor values exactly (1.10870e+08 and 9.82310e+07
bit/J), so adding the second surface did not perturb the first.

---

## 4. Matched worlds and common randomness

`FIELD_COMPONENT = "V08_C2_ORACLE_SCREEN_V1"` (L96). The keyed fading root is
`KeyedFadingField.from_components(FIELD_COMPONENT, evaluation_seed)` — two
components only, with the initialization seed and the policy label **excluded**
(`_field_for_seed`, L232-L237; receipt at L239-L246). Every arm of one world
therefore shares one field, one `_evaluation_rngs(seed)` quadruple, one start
epoch and one initial state. Verified in the smoke: all 8 arms report identical
`fading_field_sha256`, `initial_world_sha256`, `initial_state_sha256`,
`initial_mask_sha256` and `start_epoch`.

---

## 5. No-training / no-TEST guarantees

* Environment built by `screen._make_environment(archive, users=100)` —
  `BlockAlternatingSplit` + `EpisodeStartSampler.for_archive(..., TRAIN)`. There
  is no TEST path in this file.
* Every route episode snapshots the hybrid with `five_arm._snapshot_hybrid`
  before and calls `five_arm._assert_hybrid_unchanged` after (L777, L928), and
  the whole screen re-asserts once more at the end (L1756-L1757).
  `five_arm._prepare_hybrid` is called for every trainer (Q1/Q2 frozen,
  rung-100 only, `.eval()`).
* Main is checked with `runtime.network_snapshot` / `networks_equal` and
  `replay_size` before and after every episode (L969-L970, L1045-L1050) and
  once for the whole screen.
* All inference is under `torch.no_grad()`. No optimizer step, no replay write,
  no coordinator, no auction.
* `result.json` carries `test_split_opened: false`, `episode_training: false`,
  `evaluation_split: "TRAIN"`.

---

## 6. Recorded outputs

`result.json`:

* `rows` (also `rows.jsonl`) — per episode: the five-arm row fields
  (`evaluation_seed`, `initialization_seed`, `policy_label`, `total_bits`,
  `total_energy_j`, `ratio_of_sums_ee_bits_per_j`, `served_fraction`,
  `served_user_steps`, `outage_fraction`, `steps`, `action_trace_sha256`,
  `initial_world_sha256`, `initial_state_sha256`, `initial_mask_sha256`,
  `fading_field_sha256`, `start_epoch`) plus the new
  `hold_decisions` / `hold_fraction`, `infeasible_hold_count`,
  `infeasible_on_incumbent_count`, `per_step_total_power_w`, `per_step_bits`,
  `per_step_served_users`, `oracle_diagnostics`, `elapsed_s`.
* `summaries.pooled_by_arm`, `.pooled_by_arm_and_initialization`,
  `.pooled_by_arm_and_world` — ratio of sums throughout. MAIN has no
  initialization axis, so `pooled_by_arm_and_initialization["MAIN"][L]` repeats
  MAIN's world-pooled row set for every lineage `L`; that is exactly what makes
  the per-lineage `P123 - MAIN` contrast a like-for-like comparison over the
  same worlds.
* `summaries.contrasts_pooled`, `.contrasts_by_initialization`,
  `.contrasts_by_world` — all 28 lattice pairs. The 8 named ones carry a
  `role`; the rest are `diagnostic_lattice_pair`. Every contrast reports
  `delta_ee_bits_per_j`, `relative_delta_ee`, `delta_served_fraction` and
  `delta_hold_fraction`.
* `summaries.paired_world_bootstrap` — 2000 replicates,
  `np.random.default_rng(2026090299)`, resampling **worlds** with replacement
  and recomputing each arm's pooled ratio of sums; the three primary contrasts
  only. Marked `decision_input: false`.
* `checkpoint_sha256` — Main checkpoint, the three selected hybrid checkpoint
  files and their paths, and the two frozen V0.3 head lineages per
  initialization.
* `physics_code_sha256` — the 19 live modules the oracle mirrors (see §8).
* `oracle` — lambda0 (value + hex + both sources), kappa (value + hex +
  source), p0, p_max, B^w, N, circuit/baseband power, RX gain, horizon offsets,
  field component, and the two approximation notes.
* `contract_sha256`, `code_file_sha256`, `started_utc`/`finished_utc`,
  `elapsed_s`, `timings` (per episode), `keyed_fields` per seed,
  `gate_authority_sha256`, `source_closure_mode`/`source_closure_note`.

Definitions worth pinning down:

* `hold_fraction` = (decisions where the chosen `(norad, cell)` equals the
  user's incumbent association from the previous committed step) / (steps ×
  users). Read from `_previous_association` **before** the step (`_incumbent_pairs`, L752-L757;
  used at L860 and L1008). A step-0 decision can never be a hold.
* `infeasible_hold_count` = user-steps where the selected link was infeasible
  because `p > p_max` — i.e. `sum(resolution.outage_infeasible)` over the
  episode (L910 and L1034). `infeasible_on_incumbent_count` is the subset that were
  also holds, reported alongside it because the field name is ambiguous.

---

## 7. Approximations and deviations, stated

1. **Current user position for future geometry.** `theta_a(t+k)`,
   `slant_a(t+k)` and `elevation_a(t+k)` use `driver.user_ecef_km()` at `t`.
   Users move ~250 m per 30.08 s step; the satellites are propagated exactly
   (SGP4 via `satellite_ecef_at(k)`). This is the accepted approximation named
   in the work order, and self-check (ii) measures its size directly: median
   0.42 % / p95 1.35 % relative error on the realised link power one step
   ahead.
2. **Expected-value channel.** `path` is evaluated with `shadow_fading_db=0.0`
   and no Rician fade. Because `I_a+N` is obtained by *inverting* the
   observation's gamma block under the same convention, both random terms
   cancel between the numerator and the denominator of `R_a(k)`; what survives
   is `candidate_sinr[u,a] * (start_a / G_a(0)) * path(t+k)/path(t)`, i.e. the
   deterministic geometry ratio. This is a property of the formula as
   specified, not an extra assumption on top of it.
3. **Frozen non-focal context.** `n_a`, `m_a` and `sat_active_a` are the
   previous committed step's, held fixed across all three offsets. Other users
   will move; the oracle does not model that.
4. **Step-0 warm start.** The environment warm-starts step-0 segments at a
   historical `G^T(theta(tau))` drawn from
   `StepPhysics.segment_warm_start = "uniform-episode-length"` (`step.py:137`,
   `_warm_start_gain` at `step.py:749-761`). A decision-time oracle has no such
   segment (`_segments[u] is None`), so at `t = 0` it uses `start_a = G_a(0)`
   for every action, exactly as the work order specifies. Self-check (ii)
   buckets step-0-origin predictions separately to quantify this: median 8.0 %
   / p95 41.3 % over 16 samples, versus 0.42 % / 1.35 % for `t >= 1`. Only 1 of
   10 steps per episode is affected, and it affects all Q2*-using arms
   identically on a matched world.
5. **Interference is not re-evaluated at `t+k`.** `I_a+N` is the decision-time
   value; the oracle does not re-derive the interference field from the
   hypothetical future radiating set. This is what "frozen at its
   decision-time value" means in the work order.
6. **Source-closure re-check (operational, not scientific).** The five-arm
   runner passes `source_dir=` to `screen.authenticate_gate`, which re-verifies
   the sealed V0.4 **source-construction** closure manifest against the current
   tree. That check cannot pass in this checkout: 23 V0.5-V0.7 modules have
   been added since the seal and `src/mcrl/env/step.py`,
   `src/mcrl/runtime/trainer_env.py`, `src/mcrl/runtime/ee_axis_temporal_pairs.py`
   have changed (the `step.py` delta is additive — `step_without_user`,
   `evaluate_actions`, event-tagged fading, `commit=False` rewards; the
   segment/feasibility/rate/power physics this oracle mirrors is untouched).
   Because this screen constructs no C3 dataset, `--source-closure` defaults to
   `receipt-only`: `authenticate_gate` is still run **with** `source_dir` and
   the outcome is recorded verbatim in `source_closure_note`, but the receipt
   used is the `source_dir=None` one. Everything that binds this screen's
   inputs is still verified in both modes — gate `authority.json` /
   `authority-seal.json` / `result.json` / `result-seal.json` digests, the
   three selected hybrid checkpoint file SHAs, the Main checkpoint SHA against
   `five_arm.EXPECTED_MAIN_CHECKPOINT_SHA256`, and the PREREG-to-TLE binding
   through `assert_ephemeris_matches_record`. Pass `--source-closure require`
   to demand the full closure instead; it will currently fail. **The controller
   should decide this explicitly before the preregistered run.**
7. **`result.json` is overwritten, not write-once.** Unlike the sealed five-arm
   runner there is no `_write_once_json` refusal here; re-running into the same
   `--output-dir` replaces the file. Point each run at a fresh directory.

No environment API differed from the work order's description. Two naming
details worth recording: the frozen non-focal context is read from
`environment._last_outcome` (the public `environment.last_outcome` raises
before the first step), and the incumbent association is
`StepEnvironment._previous_association`, which `_rewards` commits at
`step.py:1084`.

---

## 8. Code binding

`physics_code_sha256` in `result.json` pins the 19 files the oracle mirrors or
depends on: `env/{step,link_budget,antenna,pointing,geometry,cells,candidates,
action_contract,service,scenario,keyed_fading}.py`,
`runtime/{trainer_env,ee_axis_state,ee_axis_v04_c3_state}.py`,
`algorithms/ee_axis_v04_hybrid.py`, and the four `.scratch/c3-v04` runners
(`run_v04_c3_500_update_screen.py`, `run_v04_c3_learnability_gate.py`,
`run_v04_c3_source.py`, `run_v04_five_arm_ablation.py`). This is a stronger
binding for *this* screen than the stale V0.4 source-construction manifest,
because it names the code that actually produced the episodes.

---

## 9. Smoke results (seed 2026090299, lineage 2026092101, all 8 arms)

Pooled ratio of sums, one episode per arm, 10 steps x 100 users.

| arm | EE (bit/J) | served | hold | infeasible user-steps |
|---|---|---|---|---|
| P1   | 1.11259e+08 | 0.9990 | 0.3990 | 1 |
| P2   | 1.11432e+08 | 1.0000 | 0.1370 | 0 |
| P3   | 6.37755e+07 | 0.9570 | 0.0730 | 43 |
| P12  | 1.10988e+08 | 1.0000 | 0.1580 | 0 |
| P13  | 9.82310e+07 | 1.0000 | 0.2050 | 0 |
| P23  | 1.09597e+08 | 1.0000 | 0.1320 | 0 |
| P123 | 1.10870e+08 | 1.0000 | 0.1540 | 0 |
| MAIN | 9.03555e+07 | 0.9990 | 0.6350 | 1 |

Named contrasts (pooled; one world, so these are illustrative only):

```
P123 - P13   +1.26392e+07  (+12.87 %)   primary_c2_direction
P123 - P12   -1.17369e+05  ( -0.11 %)   primary_c3_direction
P123 - P23   +1.27343e+06  ( +1.16 %)   primary_c1_direction
P123 - MAIN  +2.05147e+07  (+22.70 %)
P13  - P1    -1.30284e+07  (-11.71 %)
P12  - P1    -2.71789e+05  ( -0.24 %)
P1   - MAIN  +2.09038e+07  (+23.14 %)
P13  - MAIN  +7.87544e+06  ( +8.72 %)
```

One-step surface statistics (step index 1, over legal actions):

```
Q2*     min/median/max = -4.37913 / 0.0114262 / 4.81984
Q1+Q3   min/median/max = -0.741221 / -0.198056 / 0.571145
ZETA2*  median         = 1.15371e+08 bits
argmax flip fraction when Q2* is added to Q1+Q3 = 0.6300
```

Q2* has roughly 7x the dynamic range of the summed learned heads, so it
dominates the argmax: 63 % of users change action when it is added. That is the
single most important thing the controller should look at before freezing a
contract — the oracle is not a tie-breaker on this scale.

Oracle diagnostics for the P123 episode: 26 572 legal actions, 891 continuing a
segment, 1 164 / 1 173 / 1 173 legal actions censored by infeasibility at
k = 1 / 2 / 3 (4.4 %), 0 non-positive `candidate_sinr` entries, 1 step with
step-0 context.

---

## 10. Self-checks

| check | result |
|---|---|
| (i) `G_a(0)` from an independent geometry pass vs `transmit_gain_linear(candidates.off_axis_deg)` | max relative error **2.56e-11** over 26 572 legal slots; max angle error 4.30e-11 deg |
| (ii) realised `link_power_w(t+1)` vs predicted `p_a(1)` on genuinely continued segments, origin `t >= 1` | n = 138, median **0.42 %**, p95 **1.35 %**, max 1.70 % |
| (ii, step-0 origin, reported separately) | n = 16, median 8.0 %, p95 41.3 % — the warm start of §7.4 |
| (iii) P13 selection vs `five_arm.route_actions(..., "DROP_C2")` on identical surfaces and mask | **True**, and still True when the middle surface is replaced by a deliberately different array |

Check (ii) only compares users who were *served* on the pair at the origin step
and served on the same pair at the next step, so the segment genuinely
continued (`_check_predictions`, L1191-L1226).

Check (iii) cannot byte-match the five-arm runner's episodes because the field
component differs by design, so it compares the selection functions directly:
a stub trainer returns fixed `(Q1, Q2, Q3)` from `q_values_by_route` and the
real `five_arm.route_actions` is called on it (`_route_actions_parity`,
L1239-L1283).

---

## 11. Timing and projection

Measured on this machine, single process. The smoke was run twice and produced
**bit-identical** EE, served, hold, contrast and self-check numbers both times;
only the wall clock moved, because other agents are working on the same box.

First smoke run (quiet machine):

* one-time authentication + Main + 3 hybrids load: ~60-70 s
* MAIN episode: 5.0 s
* route arm without the oracle (P1, P3, P13): 6.9-8.1 s
* route arm with the oracle (P2, P12, P23, P123): 7.9-8.7 s
* mean over the 8 episodes: **7.56 s/episode**; 117.6 s wall including load

Second smoke run (contended machine): mean **12.15 s/episode**, 163.4 s wall.
The two-world five-arm `run` check: mean **6.95 s/episode**, 10 episodes in
127.5 s wall including load.

So budget **7.0-12.2 s/episode** depending on load. The oracle itself costs
roughly **+0.6-0.9 s per 10-step episode** (compare the oracle and non-oracle
route arms within one run), i.e. ~60-90 ms per decision step for three
`satellite_ecef_at` SGP4 propagations plus the vectorised `(100, 28)` geometry
and gain evaluations. That matches the work order's "small" expectation.

**Projection for the full screen** — 6 seeds x 3 lineages x 7 arms + 6 MAIN =
132 episodes:

* quiet machine, 7.0-7.6 s/episode: **~15-17 min** of episode time
* contended machine, 12.15 s/episode: **~27 min** of episode time
* plus one load of ~1 min -> **~16-28 min wall**; budget **30 min**.

The bootstrap itself is negligible: 2000 replicates x 3 contrasts over 6 worlds
is well under a second.

This is comfortably a foreground run; it does not need the Ubuntu server.

---

## 12. Stage 1b preregistered block (2026-09-02)

Executed under the two frozen contracts in `../contracts/` (both sha256-verified
against their `.sha256` files before launch).

| block | contract sha256 | arms | episodes | output |
|---|---|---|---|---|
| H-A | `2ac39ce557ed23596728d9a83619ce585c9c30e308559bd20f48d08c0e6d1545` | P1 P2 P3 P12 P13 P23 P123 MAIN | 132 | `stage1b-HA-20260902/` |
| OPS-3 | `b538932006f7e597ee199fb0701a4473587afa81b4580ca76e1dff13f9ea7046` | O2 O12 O23 O123 | 72 | `stage1b-OPS3-20260902/` |

Seeds 2026090221..2026090226, lineages 2026092101/02/03, `--source-closure
receipt-only`. Wall: 1149.4 s (8.27 s/episode) and 969.5 s (12.65 s/episode).
Per-episode progress lines are in `stage1b-HA-20260902.log` and
`stage1b-OPS3-20260902.log` (Python buffered them to the end of the run;
`PYTHONUNBUFFERED=1` would stream them live next time).

Joined analysis: `make_stage1b_report.py` -> `stage1b-report.md`. World identity
between the two blocks: PASS on all five fields for all six seeds. Decision
strings (contract section 4, applied literally): `C3_CONTEXT_FAIL` for both
routes. The OPS-3/H-A ratio self-check passed in both blocks
(max rel error 2.61e-16 over ~1.32M legal actions each).
