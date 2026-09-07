# Workstream A — C1/C3 early health audit

Date: 2026-09-02
Scope: read-only static audit of the frozen C1 and C3 routes (formula, state, source,
gauge, evaluator, leakage, notation), plus the nonlinearity limitation test and a
proposed fresh matched factorial integration screen.
Auditor stance: **no efficacy claim is created or upgraded here.** Every "+X%" quoted
below is a development/frozen-policy screen figure taken verbatim from a sealed artifact.

Repo: `/home/u24/papers/mcrl-leo-handover`
Tests run (all green, 24 passed): `tests/test_w85_…`, `tests/test_w88_…`,
`tests/test_w89_…`, `tests/test_w94_…`.

**Evaluator located.** The evaluator that `w88`/`w89`/`w94` exercise is **not** in
`src/`. It is:

- `/home/u24/papers/mcrl-leo-handover/.scratch/c3-v04/run_v04_five_arm_ablation.py` (2418 lines) — five-arm;
- `/home/u24/papers/mcrl-leo-handover/.scratch/c3-v04/run_v04_c3_confirmatory.py` (1632 lines) — C3 confirmatory;
- `/home/u24/papers/mcrl-leo-handover/.scratch/c3-v04/run_v04_route_interaction_diagnostic.py` (413 lines) — route interaction, which imports the five-arm module as a physics adapter.

`/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_evaluation.py` is a *different*,
V0.3-era evaluator bound to `EEAxisPairwiseTrainer`
(`src/mcrl/runtime/ee_axis_evaluation.py:134-137`). It is used only by the VOID 10EP
ablation and the bounded pilot in `.scratch/ee-axis-redesign/`, plus
`tests/test_w55_ee_axis_evaluation.py`. It is **not** on the V0.4 C1/C3 evidence path.

---

## (a) Findings table

| # | Item | Finding | Classification | Evidence (file:line) |
|---|---|---|---|---|
| 1a | C1 target formula: paper vs code | Identical expression and sign. Paper: `ζ₁,ᵤ = Δt[Rᵤᶜ(0)−RᵤᴹM(0)] − λ₀Δt[P_Cᴺ(0)−P_Mᴺ(0)]`. Code computes `z1 = interval*Δrate[0,focal] − multiplier*Δenergy[0]` where `Δenergy = interval*(P_C−P_M)`. Same units (native bits). | CONFIRMED | `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md:118`; `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md:86`; `src/mcrl/runtime/ee_surplus_targets.py:262-265` |
| 1b | C3 target formula: paper vs code | Identical. Paper: `ζ₃,ᵤ = Δt Σ_{i≠u}[Rᵢᶜ(0)−Rᵢᴹ(0)]`, rate-only, no energy term, λ-invariant. Code masks out the focal user and sums the opening-offset rate delta only. | CONFIRMED | `…AUTHORING-DELTA…:177`; `src/mcrl/runtime/ee_surplus_targets.py:267-275` |
| 1c | Route→target routing | `source_route == "C1"` takes `z1_focal_surplus_bits`; otherwise `z3_nonfocal_externality_bits`. An opening row that carries a nonzero `ζ₂` is rejected. | CONFIRMED | `src/mcrl/runtime/ee_axis_opening_pairs.py:405-411` |
| 1d | Accounting identity enforced | `ζ₁+ζ₃+ζ₂` is re-checked against `Σ_k g_k` with a magnitude-scaled tolerance; a break raises `MCRLContractError`. | CONFIRMED | `src/mcrl/runtime/ee_surplus_targets.py:277-292` |
| 1e | Canonical EE is ratio of sums | Per-episode `EE = total_bits/total_energy` with `total_bits = Σ_t Σ_u R_u·Δt`; pooling across rows sums bits and energy separately (`fsum`) then divides once. No mean of ratios anywhere on the endpoint path. | CONFIRMED | `.scratch/c3-v04/run_v04_five_arm_ablation.py:1264-1287` (`aggregate_rows`), `:679-686`; confirmatory `:727-731`; `src/mcrl/runtime/ee_axis_evaluation.py:84-92` |
| 1f | **λ₀ provenance is not the frozen Main policy** | Contract/delta say `λ₀ = 𝓑₀ᴹ/𝓔₀ᴹ` with `M` = frozen Main reference. The frozen value `λ₀ = 0x1.443a8f481639ap+26` (84 994 621.13 bit/J) was produced by `_freeze_lambda`, which rolls out the Main **network** greedily on `objective_weights=(1.0, 0.0, 0.0)` — the legacy `r1` head alone. The deployed/reference Main policy uses the preregistered `(0.5, 0.3, 0.2)` scalarization. So λ₀ is `B/E` of an *r1-greedy variant* of Main, not of Main. | IMPLEMENTATION_DEFECT (low severity) + DOCUMENTATION_DRIFT | `.scratch/ee-axis-redesign/run_c3_unilateral_oracle_pilot.py:125` vs `.scratch/c3-v04/run_v04_c3_source.py:508-531, 566-570`; `src/mcrl/runtime/trainer_spec.py:52`; `artifacts/PREREG-FROZEN-2026-08-25-R2.json` `sections/training/objective_weights = [0.5,0.3,0.2]`; frozen constant at `.scratch/c3-v04/run_v04_c3_source.py:101-102` |
| 1g | λ₀ is TRAIN-only, single-valued, frozen before outcomes | The calibration environment is built with `EpisodeStartSampler.for_archive(archive, split, TRAIN)`; the same hex constant is asserted equal in the C3 source runner and refuses to proceed otherwise. The name `useful_bits` is legacy — the quantity is literally `Σ_u R_u·Δt`, i.e. canonical delivered bits, not a filtered subset. | CONFIRMED | `scripts/run_head_pivotality_probe.py:89-96`; `.scratch/ee-axis-redesign/run_c3_unilateral_oracle_pilot.py:129-147`; `.scratch/c3-v04/run_v04_c3_source.py:2158-2169` |
| 1h | λ₀ window is one 10-step episode | `steps = 10`, `users = 100`, `calibration_seed = 2026082401`. The contract calls this a "TRAIN-only scale-calibration window" without a size floor, so this is within contract but is a thin base for a constant that fixes the bits↔energy exchange rate for every C1 target. | DOCUMENTATION_DRIFT | `artifacts/multi-catfish-v03-three-route-real-smoke-20260831/receipt.json` (`temporal_source_receipt.calibration`) |
| 2a | Q1/Q2 state (`s^v03`) causality | Every appended block is derived from `_previous_association`, `_previous_radiating`, `_previous_link_power_w`, `_segments` — all committed-previous-slot. The encoder refuses if `observation.candidates is not environment._candidates`, i.e. it must be the current predecision anchor. No `evaluate_actions` call, no outcome read. | CONFIRMED | `src/mcrl/runtime/ee_axis_state.py:164-181, 217-268, 20-22` |
| 2b | Q1/Q2 state action-alignment | The four context blocks are `(U, NUM_ACTIONS)` and are filled per legal action slot using that slot's `(norad_id, cell_id)` from the user's own `SlotTable`. Masks are cross-checked against slot-table masks. | CONFIRMED | `src/mcrl/runtime/ee_axis_state.py:214-215, 270-280` |
| 2c | Q3 state (`s^v04`) causality & alignment | Victim burdens use only `_previous_served_rate_bps` and `_previous_association`, aggregated by physical key and re-indexed onto each legal current action slot; focal user's own committed rate is subtracted exactly. Module docstring states it never calls `evaluate_actions`; verified by inspection. | CONFIRMED | `src/mcrl/runtime/ee_axis_v04_c3_state.py:8-12, 196-240, 282-285` |
| 2d | Q3 state matches the paper formula | Paper: `b^b_{u,a}(t) = (Δt/κ)Σ_{i≠u, b_i(a_i(t−1),t−1)=b_u(a,t)} R_i(t−1)`. Code: `scale = interval_s/kappa_bits`, beam/satellite dicts keyed on `(norad,cell)` / `norad`, focal subtraction, then `*scale`. Same expression. | CONFIRMED | `…AUTHORING-DELTA…:191-201`; `src/mcrl/runtime/ee_axis_v04_c3_state.py:208-235` |
| 2e | Deployment availability | The evaluator builds both views from the *same* live predecision anchor every step and refuses if the two masks differ; state width 228 and Q3 scorer `12→100→50→50→1` both match the delta. | CONFIRMED | `.scratch/c3-v04/run_v04_five_arm_ablation.py:657-669, 556-573`; `src/mcrl/runtime/ee_axis_state.py:55-59`; `src/mcrl/algorithms/ee_axis_action_shared.py:33-34, 80-90` |
| 3a | C1 source selection outcome-blind | Module is a pure pre-decision selector; explicitly holds no rate/power/reward/ζ field and never runs the simulator or evaluates a branch. | CONFIRMED | `src/mcrl/runtime/ee_axis_c1_selector.py:9-18, 249-252, 379-381, 825-826` |
| 3b | C3 (V0.4) source selection outcome-blind | Ranking keys are `burden_delta`, `victim_pressure`, `satellite_burden_delta`, `satellite_victim_pressure` — all derived from the *lagged* burden blocks and the frozen Main reference action. `ζ₃` is never read. | CONFIRMED | `src/mcrl/runtime/ee_axis_v04_c3_selector.py:1-12, 380-424, 466-546` |
| 3c | No sign filtering / clipping of targets | `build_opening_route_batch` stacks `route_target_surplus_bits` verbatim; no `abs`, `clip`, or sign predicate exists anywhere in the C3 dataset module. Contract and delta both require retaining every sign. | CONFIRMED | `src/mcrl/runtime/ee_axis_opening_pairs.py:479-481`; `src/mcrl/runtime/ee_axis_v04_c3_dataset.py` (no clip/sign filter present); `…AUTHORING-DELTA…:226` |
| 4a | Shared native-bits gauge | All three routes normalize by one shared `κ` (`target/κ`), never a per-head scale; `κ = 𝓑₀/n₀ = 0x1.2cea89d260f2ap+33`, asserted identical in source and hybrid. | CONFIRMED | `src/mcrl/algorithms/ee_axis_pairwise.py:215-220`; `src/mcrl/algorithms/ee_axis_v04_hybrid.py:573-578`; `src/mcrl/runtime/ee_axis_calibration.py:71-76`; `.scratch/c3-v04/run_v04_c3_source.py:101` |
| 4b | No softmax / rank-only / per-head normalization | Each head is a raw scalar MLP head with a linear output layer; there is no softmax, temperature, layer-norm on output, or ranking transform. Deployment adds raw outputs. | CONFIRMED | `src/mcrl/algorithms/ee_axis_action_shared.py:80-92`; `src/mcrl/algorithms/ee_axis_action_shared_meanmax.py:88-148` |
| 4c | Gauge term pins the reference action | `loss = w_j·(pair_mse + β·mean(Q_j(s,a^M)²))`. The additive per-state gauge freedom that remains is harmless for the summed argmax (a constant added across all actions cancels), but the gauge is only anchored *on sampled states*. | CONFIRMED (with caveat, see §b) | `src/mcrl/algorithms/ee_axis_pairwise.py:227-232`; `src/mcrl/algorithms/ee_axis_v04_hybrid.py:586-591` |
| 4d | Deployment score in `ee_axis_v04_hybrid.py` | `q_values_by_route` evaluates `Q1(s^v03, mask)`, `Q2(s^v03, mask)`, `Q3(s^v04)` — note **Q1/Q2 take the legal mask as an input** (masked mean/max context pooling), Q3 does not. `deployment_scores` returns `q1+q2(+q3)` with `drop_c3` as literal head omission; `select_greedy_actions` does one masked argmax with `-inf` on illegal slots. | CONFIRMED | `src/mcrl/algorithms/ee_axis_v04_hybrid.py:483-544`; mask-dependence at `src/mcrl/algorithms/ee_axis_action_shared_meanmax.py:125-146` |
| 5a | Five-arm route masking is literal head omission | `ACTIVE_ROUTES = {FULL:(C1,C2,C3), DROP_C1:(C2,C3), DROP_C2:(C1,C3), DROP_C3:(C1,C2)}`; the runner sums only the active surfaces from **one** `q_values_by_route` call and comments "No route count normalization is allowed: a drop arm is a literal head omission." | CONFIRMED | `.scratch/c3-v04/run_v04_five_arm_ablation.py:73-79, 337-370` |
| 5b | Other heads / env / seeds held fixed | Same hybrid object per initialization across all arms; `_prepare_hybrid` forces `eval()` and asserts Q1/Q2 frozen; `_snapshot_hybrid`/`_assert_hybrid_unchanged` compare weights, optimizer state, update count, training flags **and gradients** before/after every episode. | CONFIRMED | `.scratch/c3-v04/run_v04_five_arm_ablation.py:408-462, 612, 677` |
| 5c | Worlds paired (common randomness) | Fading field root = `(FIELD_COMPONENT, c3_confirm_result_sha256, evaluation_seed)` with `initialization_seed` and `policy_label` explicitly excluded; RNGs are `SeedSequence(evaluation_seed).spawn(4)`; keyed fading is addressed by `(event, step, NORAD)` so it is branch-size independent; mobility advances via `_users.step(rng)` *before* `_resolve(incumbent_norads)`, so mobility draws are action-independent. | CONFIRMED | `.scratch/c3-v04/run_v04_five_arm_ablation.py:311-326`; `src/mcrl/runtime/training_pipeline.py:868-872`; `src/mcrl/env/keyed_fading.py:1-14`; `src/mcrl/env/step.py:1349-1355`; `src/mcrl/env/scenario.py:208-219` |
| 5d | Pairing is verified, not assumed | `_validate_common_world_identity` requires `start_epoch`, `initial_world_sha256`, `initial_state_sha256`, `initial_mask_sha256`, `fading_field_sha256`, `fading_field_components` to be identical across all five arms for each of the 30 worlds, and requires exactly `4×3+1 = 13` rows per world. | CONFIRMED | `.scratch/c3-v04/run_v04_five_arm_ablation.py:1236-1262` |
| 5e | Confirmatory (w88) matching | `ARMS = ("FULL","DROP_C3")`; the only difference between arms is `drop_c3=policy_label=="DROP_C3"`; field root excludes initialization seed and policy label; same seeds `2026092501–2026092530`. | CONFIRMED | `.scratch/c3-v04/run_v04_c3_confirmatory.py:83-96, 481-500, 724` |
| 5f | Route-interaction diagnostic (w94) matching | Reuses `five.evaluate_route_episode` and `five._field_for_seed(evaluation_seed)` on the identical 30 worlds and 3 hybrids; monkeypatches `five.ROUTE_ARMS`/`ACTIVE_ROUTES` only inside a `try/finally` that restores them; asserts the hybrids unchanged. Single-route rows are therefore genuinely paired with the sealed five-arm rows. | CONFIRMED | `.scratch/c3-v04/run_v04_route_interaction_diagnostic.py:223-266` |
| 5g | **Diagnostic reports C1's conditional margins but never C3's** | The runner computes only `with_Q2 = (Q1+Q2)−Q2`, `with_Q3 = (Q1+Q3)−Q3`, `with_Q2_Q3 = FULL−(Q2+Q3)` and then writes `all_three_c1_contexts_positive: true`. The symmetric C3 question — `(Q1+Q3) − Q1` — is derivable from the same artifact but is neither computed nor reported, and the work-order doc does not state it. | DOCUMENTATION_DRIFT | `.scratch/c3-v04/run_v04_route_interaction_diagnostic.py:286-292`; `artifacts/multi-catfish-v04-route-interaction-diagnostic-20260901-r1/result.json` (`diagnostic_interpretation`); `docs/MULTI-CATFISH-MCRL-V04-ROUTE-INTERACTION-DIAGNOSTIC-2026-09-01.md:31-49` |
| 5h | **Q1 alone dominates every summed arm in the sealed block** | Recomputed from the sealed artifacts: `C1_ONLY = 117 049 799.51` bit/J, served 0.99784; `MAIN = 93 206 395.06`, served 0.99810; `FULL = 73 090 604.82`, served 0.97157; `DROP_C2 (Q1+Q3) = 105 010 574.08`, served 0.99812. Hence `(Q1+Q3) vs Q1 = −10.286 %` pooled, and per initialization `−11.93 %`, `−8.48 %`, `−10.53 %` (3/3 negative). The higher `C1_ONLY` EE is **not** a coverage artifact — its served fraction is also higher than FULL. | LIMITED_TO_OLD_Q2_CONTEXT | `artifacts/multi-catfish-v04-route-interaction-diagnostic-20260901-r1/result.json` (`single_route_summaries`, `existing_five_arm_summaries`); `artifacts/multi-catfish-v04-five-arm-ablation-20260901-r1/result.json` (`comparisons.C2.per_initialization`) |
| 5i | C1 `+254.596 %` is a *conditional* marginal | The number is exactly `FULL / DROP_C1 − 1` with `DROP_C1 = Q2+Q3 = 20 612 362.03` bit/J — the weakest arm in the block. The same head's margin is `+169.668 %` against `Q2` and `+49.247 %` against `Q3`. The magnitude is dominated by how bad the denominator context is. | LIMITED_TO_OLD_Q2_CONTEXT | `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md` arm table; diagnostic `result.json` `c1_conditional_margins` |
| 5j | C3 `+21.970 %` / `+21.216 %` are marginal in the old-Q2 context | Both are `FULL − DROP_C3` with `Q2` present in both arms. Neither block contains a `Q2`-free contrast for C3. Since `Q2` is being replaced, the confirmed direction has no automatic carry-over; the `(Q1+Q3) vs Q1 = −10.286 %` figure is the closest available Q2-free evidence and points the other way. | LIMITED_TO_OLD_Q2_CONTEXT / NEEDS_NEW_C2_INTEGRATION | `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md`; `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` (post-R14 notice) |
| 6a | Old reward semantics `r1/r2/r3` | Present in `src/mcrl/env/step.py:1052-1095`, `src/mcrl/runtime/outage_gate.py:14-15`, `probe_p3.py`, `head_pivotality.py`, `collapse_metrics.py`. **Not on the V0.4 endpoint path**: the evaluators read only `outcome.link_rate_bps` and `outcome.system_power_w`, never `outcome.rewards`. They *are* on the frozen-Main-baseline path by design (Main is the legacy MODQN policy). | CONFIRMED (no leakage into the EE endpoint) | `.scratch/c3-v04/run_v04_five_arm_ablation.py:464-481`; `src/mcrl/env/step.py:1052` |
| 6b | Scalar handover penalty in the deployed score | None. `grep` for `handover_penalty` in `src/` returns nothing; the deployed score is exactly `Q1+Q2+Q3`. | CONFIRMED | (empty grep); `src/mcrl/algorithms/ee_axis_v04_hybrid.py:511-517` |
| 6c | "Six-Q" interpretation | No code implements it. It appears only as an explicit prohibition in `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md:57`. The hybrid actively asserts exactly three networks with disjoint parameter ids and frozen Q1/Q2. | CONFIRMED | `src/mcrl/algorithms/ee_axis_v04_hybrid.py:439-449` |
| 6d | Coordinator / auction / vote / joint decoder / second argmax | None in any active path. The only textual hit is a docstring saying "without a coordinator". | CONFIRMED | `src/mcrl/algorithms/ee_axis_action_shared.py:206` |
| 6e | Selector-only deployment path | None. Selectors (`ee_axis_c1_selector.py`, `ee_axis_v04_c3_selector.py`, `ee_axis_source_selectors.py`) are source-construction only; no evaluator or deployment call imports them. Deployment goes through `select_greedy_actions` / `route_actions` only. | CONFIRMED | `src/mcrl/runtime/ee_axis_source_selectors.py:6-20`; `.scratch/c3-v04/run_v04_five_arm_ablation.py:329-370` |
| 6f | Stale legacy target module still importable | `src/mcrl/runtime/ee_axis_targets.py` computes a **mean-of-ratios** partition (`rates[0]/power[0]` summed per user, `z2 = Δhorizon_EE − Δimmediate_EE`), i.e. it is a *different* estimand from the canonical ratio-of-sums surplus in `ee_surplus_targets.py`. It is documented as "deliberately not wired into the trainer", and no active module imports it, but a reader could mistake it for the current C1/C3 target. | DOCUMENTATION_DRIFT (retired-but-live file) | `src/mcrl/runtime/ee_axis_targets.py:1-14, 98-124` |
| 6g | Retired V0.2 isolated-world function still exported | `ee_surplus_axis_targets` (V0.2, isolated-single-user) sits beside the V0.3 function in the same module; the docstring says it is retained only so old receipts stay interpretable. Not called by any V0.4 path. | DOCUMENTATION_DRIFT (benign) | `src/mcrl/runtime/ee_surplus_targets.py:4-8, 100` |
| 6h | Public documents still carry the retired V0.7 C2 | `docs/MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md:114-148` still describes `motion-one` as a "provisional post-R13 amendment"; the current authority retires it. The presentation layer carries a hold banner at line 9, so it self-flags. | DOCUMENTATION_DRIFT | `docs/MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md:4-9, 114-148` vs `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` (post-R14 supersession notice) |
| 7a | Delta notation follows the active symbol table | Every displayed base symbol in the authoring delta is single-letter: `𝓑, 𝓔, η, λ, ζ, κ, ν, w, β, ℓ, Φ, D, ρ, R, P, H, Q, s, a, b, M, C, U, S, V`. Indices/superscripts are single letters or short roman marks. No multi-letter base symbol appears in delta display math. | CONFIRMED | `…AUTHORING-DELTA…:38-71, 82-96, 118, 177, 191-201, 276, 300-305, 317-320` |
| 7b | `b` is overloaded in the delta | `b_u(a,t)` (the physical satellite-beam **pair** named by an action) and `b^b_{u,a}(t)` / `b^s_{u,a}(t)` (scalar **burdens**) share the base letter `b`, with `b` also appearing as the roman superscript. Legal under a single-letter-base rule, but a reader must disambiguate by index shape alone. | DOCUMENTATION_DRIFT (minor) | `…AUTHORING-DELTA…:53, 66-67, 191-201` |
| 7c | Multi-letter base symbols in *neighbouring* authorities | Two sources the delta cites do use non-conforming display math: `A_i(t-1)` for a beam association (collides with `A_u(t)` = legal action set) and `\mathcal A_u^{\mathrm{safe}}(t)` in the victim-burden decision; `B^{\mathrm{FULL}}` / `E^{\mathrm{DROP\text{-}C3}}` arm-label superscripts in the confirmatory prereg. The delta explicitly notices and re-expresses the first one. | DOCUMENTATION_DRIFT | `docs/MULTI-CATFISH-MCRL-V04-C3-VICTIM-BURDEN-DECISION-2026-09-01.md:61, 66, 92`; `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-PREREG-2026-09-01.md:69`; reconciliation at `…AUTHORING-DELTA…:187-191` |

---

## (b) Why the deployed argmax is nonlinear in each head — and why replacing Q2 can flip C1's or C3's sign

### The mechanism, from the code

The deployed action is

```
Φ_u(t,a) = Q1(s¹,a) + Q2(s²,a) + Q3(s³,a)          (linear in each head)
a*_u(t)  = argmax_{a ∈ A_u(t)} Φ_u(t,a)             (NOT linear in each head)
```

`src/mcrl/algorithms/ee_axis_v04_hybrid.py:511-517` (the sum) and `:538-543` (the argmax).
The score is linear; **the policy is a piecewise-constant function of the score**, and the
endpoint is a functional of the *trajectory the policy produces*, not of the score. Three
compounding nonlinearities:

1. **argmax is a step function of head differences.** For a fixed state, the chosen action
   flips exactly when the *ordering* of `Φ_u(t,·)` changes. Whether adding `Q3` moves the
   argmax depends entirely on how close the top-two `Q1+Q2` values already were. Formally,
   `∂(EE)/∂Q3` does not exist; the marginal effect of a head is a sum of discrete flips
   whose *set* is determined by the other heads. Replacing `Q2` re-draws every decision
   boundary, so the set of states where `Q3` is pivotal is a different set.

2. **Two of the three heads are themselves functions of the legal set.** `Q1` and `Q2` are
   `MaskedMeanMaxQNetwork`s: their per-action score depends on masked mean and max pooling
   over the *whole legal candidate set*
   (`src/mcrl/algorithms/ee_axis_action_shared_meanmax.py:125-146`). `Q3` is a plain
   action-shared scorer with no mask input (`ee_axis_v04_hybrid.py:500`). So the three
   summands are not even on the same functional footing.

3. **The endpoint is a closed-loop ratio of sums over a 10-step rollout.** Each executed
   action changes `_previous_association`, `_previous_served_rate_bps`,
   `_previous_link_power_w`, `_segments` and the incumbent set fed back into
   `driver.step(..., incumbent_norads=...)` (`src/mcrl/env/step.py:602-613`,
   `src/mcrl/env/scenario.py:208-219`). Those are exactly the fields the next step's
   `s^v03` and `s^v04` are built from. A single flip at `t=0` therefore changes the state
   distribution every head is evaluated on for `t=1..9`, and it changes the *denominator*
   `𝓔` as well as the numerator `𝓑` — and `𝓑/𝓔` is nonlinear in both.

Points 1–3 together mean the "marginal effect of C3" is defined only relative to a fixed
partner pair. It is a **conditional** quantity, not a property of `Q3`.

### The empirical fingerprint already in the sealed artifacts

The same `Q1` head has these three measured conditional margins in one frozen block:

| Context | Comparison | Pooled EE contrast |
|---|---|---|
| with `Q2` | `(Q1+Q2) − Q2` | **+169.668 %** |
| with `Q3` | `(Q1+Q3) − Q3` | **+49.247 %** |
| with `Q2+Q3` | `FULL − (Q2+Q3)` | **+254.596 %** |

A 5× spread in the *same head's* marginal effect across three partner sets is a direct
measurement of the nonlinearity. The same block gives, for `Q3`:

| Context | Comparison | Pooled EE contrast |
|---|---|---|
| with `Q1+Q2` (sealed) | `FULL − (Q1+Q2)` | **+21.970 %** (confirmatory: +21.216 %) |
| with `Q1` only (recomputed) | `(Q1+Q3) − Q1` | **−10.286 %**, 3/3 initializations negative |

**The sign of C3's marginal effect already flips when Q2 is removed.** Since the whole
point of the current programme is that `Q2` will be *replaced*, the sealed `CONFIRM_C3`
decision is valid exactly as written — as a marginal comparison against the frozen old-Q2
partner — and carries no entitlement in a new-Q2 context.

The most uncomfortable, and load-bearing, fact: in the sealed 30-world block
`C1_ONLY` (`Q1` alone) reaches **117 049 799.51 bit/J at 0.99784 served**, beating
`FULL` (73 090 604.82 at 0.97157) *and* frozen `MAIN` (93 206 395.06 at 0.99810). Adding
`Q2`, `Q3`, or both to `Q1` reduced EE **and** service in this block. This does not refute
C1 or C3 — it is a development screen, not an efficacy test, and `Q3` was selected by a
gate that never saw a `Q2`-free context — but it does mean the headline `+254.596 %` must
never be read as "C1 contributes 254 % of EE". It is `FULL/(Q2+Q3) − 1`, and its size is
mostly a statement about how poor `Q2+Q3` is.

### Consequence for the audit's classification

`CONFIRM_C1` and `CONFIRM_C3` are internally valid, correctly matched, correctly
preregistered decisions about *marginal deployment contribution in the frozen old-Q2
context*. They are **LIMITED_TO_OLD_Q2_CONTEXT** as scientific carry-over, and rechecking
them requires a fresh joint screen — **NEEDS_NEW_C2_INTEGRATION**. No implementation defect
produced the `−10.286 %`; it is a genuine interaction.

---

## (c) Proposed fresh matched factorial integration screen (specification only — do not run)

**Name.** `V0.8 three-route factorial integration screen`
**Claim ceiling.** `JOINT_INTEGRATION_SCREEN_ONLY__NO_ROUTE_EFFICACY_CONFIRMATION`.
Preregister before the new `Q2` is selected, or at latest before any new-`Q2` outcome is
inspected; otherwise it is post-hoc.

### Arms

Full `2³` route mask over `{Q1, Q2, Q3}` plus the frozen Main baseline — 9 policies:

```
FULL     = Q1+Q2+Q3        DROP_C1  = Q2+Q3
DROP_C2  = Q1+Q3           DROP_C3  = Q1+Q2
C1_ONLY  = Q1              C2_ONLY  = Q2        C3_ONLY = Q3
NONE     = masked reference (no head; deterministic tie-break)   [optional, see below]
MAIN     = frozen legacy MODQN scalarization, one row per world
```

`DROP_Cj` is already the complement of `Cj_ONLY` in this lattice, so the 2³ mask is only
**one extra arm** (`NONE`) beyond `{FULL, DROP_C1, DROP_C2, DROP_C3, C1_ONLY, C2_ONLY,
C3_ONLY}` — which the existing machinery already produces. **The full factorial is
affordable.** Recommend including `NONE` only if a well-defined head-free tie-break exists;
otherwise drop it and run the 7-policy lattice, which is what identifies every main effect
and every two-way interaction.

Primary preregistered comparisons (all on pooled ratio-of-sums EE):

```
main effects (in FULL context) :  FULL − DROP_C1, FULL − DROP_C2, FULL − DROP_C3
main effects (in solo context) :  (Q1+Q3) − Q3,  (Q1+Q2) − Q2,  (Q2+Q3) − Q3, ...
                                  i.e. every  (Ci+Cj) − Cj  pair
sign-stability gate            :  for each route j, the sign of its marginal effect must
                                  agree across ALL contexts in which it is observable
whole-method gate              :  FULL > MAIN
```

The **sign-stability gate is the new item** and is the direct fix for the defect this audit
found: a route passes only if its marginal EE effect is positive in *every* partner context,
not in one hand-picked one.

### Machinery to reuse (exact entry points)

| Purpose | Reuse |
|---|---|
| Episode physics + row schema | `.scratch/c3-v04/run_v04_five_arm_ablation.py:597` `evaluate_route_episode` — already generic over `ACTIVE_ROUTES`; extend the dict, do not fork the function |
| Route-mask sum + masked argmax | same file `:329` `route_actions` (already reads `ACTIVE_ROUTES[policy_label]`) |
| Main baseline arm | same file `:699` `evaluate_main_episode` with `runtime.main_actions` from `.scratch/c3-v04/run_v04_c3_source.py:534` `_main_decision` |
| Common keyed world | same file `:311` `_field_for_seed` / `:320` `common_field_receipt` — **change `FIELD_COMPONENT` to a new `V08_FACTORIAL_V1` and re-root on the new C2 selection authority SHA-256**; keep `initialization_seed` and `policy_label` excluded |
| Paired-world identity assertion | same file `:1236` `_validate_common_world_identity` — generalize `expected_count` to `len(ARMS_WITH_INIT)*len(INITIALIZATION_SEEDS) + 1` |
| Pooling (ratio of sums) | same file `:1264` `aggregate_rows`; per-init `:1307`; per-world `:1331` |
| Deterministic paired bootstrap | same file `:1439` `paired_world_bootstrap`, 10 000 replicates, one frozen bootstrap seed per comparison |
| Frozen-model guards | same file `:408` `_snapshot_hybrid`, `:438` `_assert_hybrid_unchanged`, `:445` `_prepare_hybrid` |
| Deployment container | `src/mcrl/algorithms/ee_axis_v04_hybrid.py` — **needs one change**: `deployment_scores` currently exposes only `drop_c3`; add a general `active_routes: tuple[str,...]` parameter, or (preferred, zero-risk) keep the hybrid untouched and let the runner sum `q_values_by_route()` outputs exactly as `route_actions` already does |
| State encoders | `src/mcrl/runtime/ee_axis_state.py:184` and `src/mcrl/runtime/ee_axis_v04_c3_state.py:243` unchanged; the new `Q2` supplies its own `s²` view and must be encoded from the same predecision anchor with the same mask-equality assertion (`run_v04_five_arm_ablation.py:568-572`) |
| Consumer contract tests | pattern from `tests/test_w89_ee_axis_v04_five_arm_ablation.py` (synthetic rows only, no TLE/simulator/checkpoint) |

### World count and seed structure

- **Physical worlds:** 30 **fresh** TRAIN-only evaluation seeds, non-overlapping with
  `2026092501–2026092530` (confirmatory) and `2026092601–2026092630` (five-arm). Suggested
  `2026100101–2026100130`. Fresh seeds are mandatory: the existing worlds have now been
  read by two sealed blocks plus a post-outcome diagnostic.
- **Initializations:** the same 3 frozen `Q3` initialization seeds
  (`2026092101–2026092103`) so `Q3` is bit-identical to the confirmed head, **plus** the
  new `Q2` lineages. If the new `Q2` has its own `k` lineages, cross them: rows =
  `30 worlds × 3 inits × 7 route arms` = 630 episodes, `+30` Main = **660 ten-step
  episodes**. At the sealed five-arm rate (390 episodes in 890.92 s) this is ≈ 25 minutes.
  With a second `Q2` lineage axis it doubles to ≈ 50 minutes. **Heavy but not a training
  run — still comfortably a server job, not a local WSL job.**
- **Keyed field:** one root per `(V08_FACTORIAL_V1, new_c2_authority_sha256,
  evaluation_seed)`; initialization seed and policy label excluded, so every arm and every
  initialization sees the identical physical world.
- **Split:** TRAIN only. **No TEST opening.** No gradient, no replay write.
- **Bootstrap:** deterministic paired-world resample of the 30 seeds, retaining all
  initializations per sampled world, 10 000 replicates, one frozen seed per comparison
  (extend `BOOTSTRAP_SEEDS` at `run_v04_five_arm_ablation.py:92`).
- **Service guard:** pooled served-fraction non-inferiority plus per-initialization
  non-inferiority, same shape as the confirmatory rule
  (`docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-PREREG-2026-09-01.md`, decision rule §5).

### What must be preregistered before the run

1. The 7 (or 8) arm labels and their exact route masks.
2. The sign-stability gate wording, including what happens on a split sign
   (recommendation: `ROUTE_j_CONTEXT_DEPENDENT`, which blocks promotion of that route but
   does not retro-invalidate the sealed V0.4 blocks).
3. That `C1_ONLY` may beat `FULL`, and that this outcome is a *reportable result*, not a
   run failure. The existing five-arm decision rule has no branch for it.
4. That no route may be retrained, reselected, or rescaled in response to this screen.

---

## (d) IMPLEMENTATION_DEFECT items, with severity

| Severity | Item | Detail | Effect on the sealed C1/C3 numbers |
|---|---|---|---|
| **LOW–MEDIUM** | **λ₀ is not `𝓑₀ᴹ/𝓔₀ᴹ` of the frozen Main policy** (finding 1f) | `_freeze_lambda` (`.scratch/ee-axis-redesign/run_c3_unilateral_oracle_pilot.py:125`) rolls out the Main network greedily on `objective_weights=(1.0, 0.0, 0.0)`. The frozen Main reference policy uses `(0.5, 0.3, 0.2)` (`artifacts/PREREG-FROZEN-2026-08-25-R2.json`; `src/mcrl/runtime/trainer_spec.py:52`; `.scratch/c3-v04/run_v04_c3_source.py:508-531`). λ₀ is therefore `B/E` of an r1-greedy *variant*, not of Main. | **None on C3** — `ζ₃` is λ-invariant by construction (`ee_surplus_targets.py:267-275`), so the entire C3 evidence chain is untouched. **Bounded on C1** — it shifts the bits↔energy exchange rate inside `ζ₁` only, uniformly across every row, arm, and head, so it cannot break matching or the accounting identity. It does mean the paper sentence `λ₀ = 𝓑₀ᴹ/𝓔₀ᴹ` is not literally true of the implementation. **Recommended fix: amend the paper text to state the actual calibration policy, rather than recomputing λ₀** — recomputing would invalidate every sealed source manifest and receipt for no scientific gain. Do not silently change the constant. |
| **LOW** | λ₀/κ estimated from a single 10-step, 100-user episode (finding 1h) | `steps=10`, `users=100`, one seed. Within contract (no size floor is specified) but thin for a constant that fixes the exchange rate for all C1 targets. | No effect on matching or on any sealed comparison. Recommendation: state the window size explicitly in the paper; specify a floor in the next contract revision. |
| **LOW** | Route-interaction diagnostic reports C1's conditional margins but not C3's (finding 5g) | `.scratch/c3-v04/run_v04_route_interaction_diagnostic.py:286-292` computes `c1_conditional_margins` only, and the result records `all_three_c1_contexts_positive: true` with no symmetric C3 field. The `(Q1+Q3) − Q1 = −10.286 %` fact is recoverable from the same artifact but is not surfaced. | Reporting asymmetry, not an arithmetic error. The published diagnostic reads more favourably than the data it contains. Recommendation: add `c3_conditional_margins` (and `c2_conditional_margins`) to a **new versioned** diagnostic — the current evaluator is byte-frozen by `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` and must not be edited. |
| **INFORMATIONAL** | Two retired estimand modules remain importable in `src/` (findings 6f, 6g) | `src/mcrl/runtime/ee_axis_targets.py` implements a **mean-of-ratios** partition — a different estimand from the canonical target — and is not imported by any active path. `ee_surplus_axis_targets` (V0.2 isolated-world) sits in the same module as the live V0.3 function. | No active-path effect; both are correctly docstring-flagged. Risk is a future author or reviewer reading the wrong formula. Recommendation: add a one-line `DEPRECATED — not the current C1/C3 target` banner; do not delete (frozen receipts reference them). |

**No arithmetic, matching, pairing, leakage, or sign-filtering defect was found in the C1
or C3 evidence chain.** The formulas, units, causality, action-alignment, outcome-blindness,
shared-κ gauge, literal head omission, common-randomness pairing, and ratio-of-sums pooling
all check out against the paper text.

---

## Distinguishing verified fact / inference / recommendation

**Verified fact (file:line or artifact-recomputed):** everything in the findings table
marked CONFIRMED; the λ₀ objective-weight mismatch; the recomputed
`(Q1+Q3) vs Q1 = −10.285558 %` pooled and `−11.93 / −8.48 / −10.53 %` per initialization;
`C1_ONLY = 117 049 799.51` bit/J at 0.99784 served vs `FULL = 73 090 604.82` at 0.97157 and
`MAIN = 93 206 395.06` at 0.99810.

**Inference (mine, not measured):** that replacing `Q2` is *likely* to change the sign or
magnitude of C1's and C3's marginal effects. The mechanism is verified from code; the
specific outcome under a not-yet-existing `Q2` is not. Also inference: that `C1_ONLY`
outperforming `FULL` is an interaction effect rather than evidence that `Q2`/`Q3` are
intrinsically harmful — this block cannot separate the two.

**Recommendation (not a finding):** the factorial screen in §(c); the sign-stability gate;
amending the paper's λ₀ sentence rather than recomputing the constant; adding a
`c3_conditional_margins` block in a new versioned diagnostic; deprecation banners on the two
retired estimand modules.

**Explicitly NOT claimed:** none of the development-screen signs above is an efficacy
result. `C1_ONLY > FULL` is a development-screen observation in one 30-world TRAIN block; it
does not establish that `Q1` alone is a better policy, and it must not be reported as one.
