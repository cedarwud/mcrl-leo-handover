# Harness audit — C3-S closed-loop kill screen v1 (`c3s-20260908-r1`)

Independent auditor: Claude Opus 5, fresh context, 2026-09-08. Read-only; no tracked file modified, no git
state changed. The target is the **test harness**, not the scientific claim.

## Scope caveat governing every code-level finding

The terminal receipt binds the as-run code by SHA-256 (`producer_common_binding.code_files`, 182 entries).
The contract `.md` matches (`1b19e0f4c6c5f159…`), but all three C3-S source files present locally **do not
match** the digests that produced the numbers: `run_v023_c3s_screen.py` receipt `4f62e7608b114b2c…` vs local
`425225c555238324…`; `c3s_policy.py` `f50aa3047870c096…` vs `b5f1e788c2ce7c3c…`; `test_c3s_screen.py`
`ed71950ce11843a0…` vs `8fe6a2849bbc55c4…`.

Corroboration that the local tree is *newer*: local `execute_merge` sets `coordinator_timing["BASE"] =
base_q_timing_summary(receipts)` (`run_v023_c3s_screen.py:1622`), but the published receipt's
`coordinator_timing` has keys `['FULL','LITE']` only. A hash sweep of `.scratch/` finds no copy of the
as-run digests; the as-run tree is on the server (`/home/sat/mcrl-v023-c3s-run`, `c3s/run-v1`, `4abe9da`).
**Checks 2, 5, 6, 8 audit the current tree, not the binary that produced the receipts.** Check 1 is
code-independent and stands regardless.

Finally, `e1_estimands.py` does **not** participate in this screen's endpoints: zero references from
`c3s_policy.py` and `run_v023_c3s_screen.py`; imported only by `run_v023_c3_existence_e1.py`, it appears in
the 182-file census as transitive provenance only. Scoring runs through `_step_metric` (realised) and
`_profile_metrics` (nominal); U₁/J₁ estimator machinery is not in this causal chain.

| # | Check | Verdict |
|---|---|---|
| 1 | Independent recomputation from unit receipts | **PASS** (bit-exact) |
| 2 | Kill rule vs contract text | **PASS** |
| 3 | BASE authenticity, matched initial state, matched fading | **PASS** (one CANNOT_VERIFY) |
| 4 | Service tie: construction or coincidence | **PASS** — near-certain **by construction**; the clause is vacuous here |
| 5 | Accounting units symmetric across arms | **PASS** on symmetry; **CANNOT_VERIFY** on exploitability |
| 6 | Tests-of-the-tests | **FAIL** — three named failure modes uncovered |
| 7 | Placebo / negative controls | **FAIL** — none exist |
| 8 | Timing attribution | **FAIL** — 51 %/70 % of reported latency is instrumentation BASE never pays |

## 1. Independent recomputation — PASS

Recomputed from the 360 per-step rows in each of the 12 unit receipts with `Fraction(float.fromhex(...))`,
importing no runner code; `η = Σbits / Σjoules`.
| arm | η (bits/J) | float_hex | served | vs BASE |
|---|---:|---|---:|---:|
| BASE | 117 419 389.186097383 | `0x1.bfeb5f4be9050p+26` | 35 971 / 36 000 | — |
| FULL | 120 804 786.830936819 | `0x1.ccd56cb52e11ap+26` | 35 971 / 36 000 | **+2.883167 %** |
| LITE | 120 850 121.095358536 | `0x1.cd01b2461a5abp+26` | 35 971 / 36 000 | **+2.921776 %** |

Relative error against `pooled_exact` numerator/denominator strings: **0.000e+00** for `total_bits`,
`total_energy_j`, `eta`, `service`, all three arms — the recomputed `Fraction`s are *equal*, not close.
Per-world and per-lineage `eta`/`service`/`served`: **0 mismatches**. 360 steps and 36 000 opportunities per
arm. All 12 unit receipt hashes and `.sha256` sidecars verify; terminal receipt `a66b481303a28c31…` matches
the result record. Not in the receipt: FULL is **+1.6092 % bits, −1.2383 % joules**; LITE +1.5514 % /
−1.3315 %; mean system power 260.528 → 257.302 W (−3.226 W); mean sum-rate 30.591 → 31.083 Gbps. Pooling
sensitivity: mean-of-unit-ratios gives +2.885448 % / +2.927080 % — same sign and magnitude, so the headline
is not an artefact of the pooling choice.

## 2. Kill rule vs contract — PASS

`run_v023_c3s_screen.py:1063-1076` (`pool_unit_receipts`) is the only site emitting SUPPORT/NO_SUPPORT.
- `if _fraction_from_payload(exact[arm]["eta"]) <= eta_base: reasons.append("EE_NOT_STRICTLY_ABOVE_BASE")`
  → strict `>` required, correct direction, tie ⇒ NO_SUPPORT. Matches contract §5 / Addendum A §C.
- `if _fraction_from_payload(exact[arm]["service"]) < service_base - SERVICE_MARGIN:` with
  `SERVICE_MARGIN = Fraction(1, 1000)` (`:77`). `service` is the **per-opportunity fraction**
  `served/36000`, so the clause is `served_arm ≥ served_BASE − 36`, exactly the contract's gloss
  "Service margin 等於最多少 36 served user-steps" (contract line 105). Boundary inclusive (`≥`), correct.
  Comparisons are exact `Fraction`; no epsilon, no float.
- No third condition participates. `descriptive_breakdowns`, `full_vs_lite_comparison`, `progression_rule`
  are inert (`:1637-1651`); the coverage assertion (`:1628-1636`) raises → INVALID_RUN, which contract §5
  requires to suppress both dispositions.

## 3. BASE authenticity and matching — PASS (one CANNOT_VERIFY)

- BASE = frozen learned policy: `execute_physical_unit:918` loads `f2._load_frozen_heads(lineage)`; the
  selector is `e1._q12_surface_base_only(...)[2]` (`:936`), `argmax` over masked `float32(Q1)+float32(Q2)`
  with lowest-legal-slot ties (`run_v023_c3_existence_e1.py:1010-1014`). No coordinator path reaches it.
- Checkpoint bytes digest-checked at load by `_validate_lineage_authority`
  (`run_v023_c3_contingency_f2.py:297-308`), which also re-derives the authority body seal. Receipts bind
  `d40a0f30…` / `bb45bed3…` / `32b5accf…` for lineages `2026092101/02/03`, all `rung-003000`, Q2 inits
  `2026108101/02/03` — matching contract §2. Weights cannot drift mid-unit: `_parameter_sha256` compared
  before and after all three arms (`run_v023_c3s_screen.py:912, 962-964`).
- **Identical initial state:** all 12 units have one `initial_state_sha256` shared by all three arms
  (verified from receipts; runner asserts it at `:959-960`). Only 4 distinct values, one per world.
- **Identical exogenous fading:** each arm installs
  `KeyedFadingField.from_components("MCRL_V023_LCSRS_C3_OBSERVABILITY_V1", world)` (`:923`) — arm not in
  the key — and `draw` seeds PCG64 from `sha256([version, root_key, event, step_index, norad])`
  (`src/mcrl/env/keyed_fading.py:137-149`), a pure function of world and slot, independent of actions and
  of RNG consumption. Common random numbers hold exactly; `field_root_digest` matches the panel.
- **CANNOT_VERIFY:** `C3S-PREFLIGHT-MANIFEST.json`, the 12 `C3S-LAUNCH-AUTHORITY-*.json` and
  `C3S-LAUNCH-AUTHORITY-MERGE.json` are **absent locally** (only builder scripts present). Local receipts
  are mode `0644`, not the contract's `0444` — rsync copies, not the immutable originals.

## 4. Service tie — near-certain by construction; the clause is vacuous here

"Service" counts a **per-opportunity served indicator**: `_step_metric` (`:801-819`) records
`served = outcome.resolution.served_count` and `opportunities = USERS = 100` unconditionally, so a user
with an empty mask still counts as an opportunity. Three facts make 35 971 = 35 971 = 35 971 structural:
1. **Hard per-decision floor.** `select_candidate` (`c3s_policy.py:277, 293`) sets `threshold = BASE nominal
   served` and admits a row only `if int(parsed["served"]) >= threshold` — the coordinator can never
   *choose* a profile that loses nominal service.
2. **The panel is at the ceiling.** 352 of 360 BASE steps serve 100/100. All 29 unserved user-steps in the
   BASE arm occur at `step_index == 0`, in 8 of 12 units (93, 94, 95, 97, 97, 97, 99, 99).
3. **Nominal predicted realised perfectly.** In all 720 coordinator decisions the selected candidate's
   `selected_nominal.served` equals that arm's realised `served`, including all 8 step-0 cases.

Consequence: the `s_arm ≥ s_BASE − 0.001` clause was satisfied with all 36 user-steps of slack unused and
**carried no discriminating power**; it must not be reported as independent evidence that the coordinator
preserves service. The coordinator did deviate from BASE at **360/360 decisions in both arms** (census:
FULL 194 unilateral / 166 evacuation; LITE 55 / 305), so the tie is not because it sat on BASE.

## 5. Accounting units — PASS on symmetry; CANNOT_VERIFY on exploitability

**Symmetry: clean.** One function, `_step_metric` (`:801-819`), scores every arm from
`environment.last_outcome`: `bits = interval_s · math.fsum(link_rate_bps[0..99])`,
`energy = interval_s · system_power_w`, `interval_s` from the driver config (30.08 s). Same code, same
100-user vector, same whole-system scalar, same 30 steps — **no per-arm branch anywhere in the scoring
path**. The coordinator's model uses the same formulas (`run_v023_c3_existence_e1.py:751-764`) on
`system_power_w` from the same `StepEnvironment._resolve_physics`, and
`test_detached_evaluator_matches_native_nominal_physics_and_is_pure` asserts bit-equality of `link_rate_bps`,
`link_power_w`, `system_power_w` between detached evaluator and live environment.

**Where the hole would be.** `system_power_w` (`src/mcrl/env/link_budget.py:548-587`) =
`Σ_beams P_supply + Σ_sat N_act·P_cir + P_BB·#{sat: N_act>0}`, over **radiating beams only**
(`step.py:986-993`; `beam_keys` exist only where a beam has ≥1 served user). There is **no idle-PA floor,
no bus power for a satellite whose beams are all empty, no activation/switching transient, no minimum
on-time.** Emptying a beam instantly saves `P_cir = 0.338 W` plus its PA supply; emptying a satellite also
saves `P_BB = 0.200 W`. With `supply ∝ √P_RF` (`pa_efficiency:468-493`), beam power a max over users and
bandwidth shared, consolidation removes whole √-terms — exactly the lever an evacuation catalog pulls, and
the class of modelled saving least realisable in hardware.

**CANNOT_VERIFY:** the receipts store only `bits_hex`, `energy_j_hex`, `served`, `opportunities` per step —
no radiating-beam count, no `fixed_power_w`, no supply/fixed split. The saving is **3.226 W of 260.5 W**;
the whole fixed-power envelope is at most `100×0.338 + n_sat×0.200 ≈ 34-40 W` (≈13 %), so 3.2 W is fully
consistent with *either* ~9-10 beams switched off *or* PA consolidation, and the receipts cannot
distinguish them. Both arms are scored by the same simulator, so this is not a harness asymmetry — but it
is an unfalsified model-privilege risk sitting directly under the headline number.

## 6. Tests-of-the-tests — FAIL

33 tests; locally **31 pass, 2 fail**, both only because the module hard-binds server absolute paths
(`pin_single_thread_runtime` demands `/home/sat/mcrl-leo-handover/.venv/bin/python`; `estimate` hashes
`/home/sat/mcrl-v023-c3-probe-s0-20260908-r1/probe-s0-result.json`) — no independent reviewer can run the
suite to completion off the server, an auditability defect in itself.

Classification. **(a) real behavioural, known-answer — 11**: `default_eta_ref…`,
`selection_service_guard_and_base_first_ties`, `exact_pooling_and_disposition_reasons`,
`detached_evaluator_matches_native_nominal_physics_and_is_pure` (strongest — cross-checks the coordinator's
model against the real simulator), `candidate_catalog_order_is_deterministic`, `lite_catalog_order_top2…`,
`actual_evacuation_membership…`, `actual_catalog_retains_aliases…`, `actual_catalog_rejects_duplicate…`,
`timing_summaries_are_separate_for_all_arms`, `closed_loop_arms_advance_independently`. **(a′) negative
/guard with known answer — 9** (neutrality, RNG spawning, geometry mutation, unsealed contract, bogus
authority, import-graph census, world census, write-once, invalid/incomplete). **(b) self-consistency — 2**
(`merge_reports_two_decisions…` monkeypatches every summary it then asserts; `estimate_covers_three_arms…`
asserts the 10× ratio the function hard-codes). **(c) smoke / plumbing — 11** (resume, atomicity, competing
merge, re-entry — real, but about I/O). The four named failure modes:

- **Wrong sign in the kill rule — CAUGHT.** `test_exact_pooling_and_disposition_reasons` pins both
  directions with distinct known answers, including FULL failing on *both* reasons in fixed order while
  LITE simultaneously passes.
- **Arms sharing state — PARTIALLY CAUGHT, at the wrong seam.**
  `test_closed_loop_arms_advance_independently` drives a `SyntheticEnvironment`, never the real one.
  `execute_physical_unit` — which builds one environment *per arm*, installs the keyed field and asserts
  matched initial state — is **monkeypatched out in every test that touches it** (lines 911, 928, 942,
  1075) and is therefore **untested**. Its `initial_state_sha256` assertion only detects arms that fail to
  *share* a start, never arms that fail to *diverge*.
- **Double-counted bits — NOT CAUGHT.** `_step_metric`'s `bits = interval_s · Σ_u rate_u` has no
  known-answer test. `test_closed_loop_arms_advance_independently` drives it (synthetic `rate = position`
  for all 100 users, `power = position+1`, `interval = 1.0`, so `bits = 100·position`) but asserts only on
  `history`/`position`, never on `bits_hex`/`energy_j_hex`. A sum over served users only, or a doubled
  interval, would pass the whole suite.
- **Wrong η pooling (mean-of-ratios vs ratio-of-sums) — NOT CAUGHT.** In
  `test_exact_pooling_and_disposition_reasons` **every synthetic unit has energy 0.3 (or 1.0)**. With equal
  denominators the two estimators are algebraically identical (BASE: 0.3/0.6 = 0.5 = mean(1/3, 2/3)), so
  refactoring `pool_unit_receipts` to average per-unit η would pass unchanged.

## 7. Placebo / negative controls — FAIL (none exist)

`ARMS = ("BASE", "FULL", "LITE")` (`:75`). Grep of runner, policy and tests finds no null arm, no sham
coordinator, no random-feasible arm, no shuffled-catalog control. Nothing in the design would detect a
harness that credits the coordinator arm with a benefit it did not cause. **Specification for the hardened
runner (engineering lane; harness-validity arms reported separately from the sealed two-arm adjudication,
so no contract change):**

- **NULL arm.** Add `"NULL"` to `ARMS`, using the *full* `C3SPolicyAdapter` (same snapshot construction,
  same neutrality fingerprints, same receipt path) with
  `decision_function = lambda snapshot, evaluator: DecisionResult(actions=snapshot.base_actions.copy(),
  base_actions=snapshot.base_actions, profile_id="BASE", …)`. **Expected outcome, asserted as a hard gate:**
  `action_trace_sha256(NULL) == action_trace_sha256(BASE)` in all 12 units; `bits_hex`/`energy_j_hex`
  **byte-identical** across all 360 steps; pooled η, bits, joules, served **exactly equal** to BASE as
  `Fraction`s; kill rule ⇒ `NO_SUPPORT` with `EE_NOT_STRICTLY_ABOVE_BASE` (equality is not strictly above).
  Any deviation proves the coordinator arm differs from BASE for a reason other than its decisions —
  environment construction, RNG consumption, snapshot side-effects, accounting drift.
- **RANDOM-FEASIBLE arm.** Same adapter, `decision_function` choosing uniformly among catalog rows passing
  the nominal service guard, seeded from a dedicated stream
  `SeedSequence(["C3S_RANDOM_CONTROL", world, lineage])` — never the environment RNG, so it survives
  `_assert_no_prohibited_capabilities`. **Expected outcome:** service ties BASE (same guard) and pooled η
  lands **at or below BASE**, certainly far below +2.88 %. If a random feasible profile also gains ~+2.9 %,
  the gain belongs to the catalog and the accounting, not to the S0 objective, and the screen means nothing.
  Cost: ≈1 worker-hour for NULL (BASE-priced), ≈10 for RANDOM-full or ≈1.5 for RANDOM-lite.

## 8. Timing — FAIL (misattributed, in the conservative direction)

The decision clock is `run_arm_trajectory:846-848`: `perf_counter()` around the `selector(...)` call only.
`environment.step(...)` — the physical step both arms pay — is **outside** it. That part is correct. The
defect is asymmetric instrumentation. For coordinator arms `selector` is
`C3SPolicyAdapter.select_actions`, which computes `_live_neutrality_fingerprint(step_env, rng)` — a
`_structural_sha256` walk of the whole step environment — **before and after** every decision
(`c3s_policy.py:838, 869`); BASE's selector is a bare Q-inference lambda with no fingerprint.
`decision_records["wall_seconds_hex"]` correctly excludes both; `per_arm_decision_wall_timing` includes them
for FULL/LITE and not for BASE:

| arm | reported per-arm mean | true decision mean | instrumentation inside the reported figure |
|---|---:|---:|---:|
| BASE | 1.885 s | 1.885 s | 0 % |
| FULL | 66.792 s | **32.497 s** | 34.30 s (**51.3 %**) |
| LITE | 49.431 s | **14.882 s** | 34.55 s (**69.9 %**) |

The result record quotes the instrumented column and concludes "the 30.08 s control interval is exceeded by
both arms". On the comparable measure **LITE's mean decision cost (14.88 s) is below the 30.08 s interval**;
its median is 7.33 s. The error direction is conservative — the coordinator looks slower, so no scientific
claim is inflated — but the deployability sentence being written on this number is wrong as stated, and the
same asymmetry would flatter a future "we sped it up" claim by ~34 s/decision of pure harness overhead.
