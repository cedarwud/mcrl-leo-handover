# V025 physics-successor engine — stage-2 fresh-context audit (Claude Opus 5, 2026-09-08)

Read-only; nothing on `sat` was modified and no simulation was launched. Executed only
`pytest -q tests/physics_v025` (102 passed) and read-only `python -c` probes inside
`sat:/home/sat/mcrl-v025-stage2-snapshot-20260908/`: engine `…/src/mcrl/physics_v025/*.py`,
runner `…/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py` (bare
`:NNN` refs below are this file), tests `…/tests/physics_v025/`. Declarations v1.0–v1.3,
controller decisions and engine reports read from
`sat:/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/`.

## S1 — BLOCKERS (before any unit outcome is opened)

**B1. Treatment H and SH are silent no-ops; 10 of the 31 sealed settings are exact duplicates.**
VERIFIED. `StepEvaluator.evaluate` calls `score_setting(shared, self.setting)` with no
`interruptions=` argument (`run_v025_matrix_probe.py:273`); the parameter defaults to `()`
(`src/mcrl/physics_v025/adapter.py:156`). A repo-wide grep finds **no construction of
`InterruptionEvent` anywhere outside `integration.py` and test fixtures** — the runner never
builds one. Empirical confirmation (world 1, 1 step, FULL arm): `a-γ0` and `a-γH` both give
bits = 7245627378, J = 530.6904439; `a-γS` and `a-γSH` both give bits = 7245627378,
J = 614.7471712 — bit-identical pairs, with `useful_availability == decoding_availability` in
every cell, i.e. no blackout is ever removed. The 62/142 ms interruption sensitivity carries
zero information; 10 cells and 40 unit receipts would be duplicates presented as a sensitivity.

**B2. The FULL/DROP arms cannot measure the C1/C2/C3 marginals; C1's contrast is structurally
identically zero and C3's is confounded with selector class.** VERIFIED. `_set_select`
(`:585-595`) scores every configuration as `core + κ·bonus`, where `core = _objective(...)` is
the **exact realised whole-network objective** `F = B − η_ref·E` of that configuration. For a
unilateral configuration the C1 bonus is `C1.normalized_total = (F(cfg) − F(base))/κ + Φ`
(`targets.py:170`), so `κ·bonus_C1 = F(cfg) − F(base) + κΦ` — an order-preserving affine
function of the very `F` the selector already maximises; removing it cannot change the argmax.
Empirically, over `a-r0`, `a-γ0`, `b0` × 3 steps, `UNION_CATALOGUE_OPTIMUM`, `FULL`, `DROP_C1`,
`DROP_C2` and `DROP_C3` select the **identical configuration at every step**, and all three
reported marginals are `delta_ee = 0.0, failed=True`.
Separately, `DROP_C3` alone uses a different selector class — `_independent_proposal`
(`:546-571`), a per-user greedy on (C1+C2) with **no `F` term and no joint search** — while
FULL/DROP_C1/DROP_C2 are oracle set optimisers. `FULL − DROP_C3` therefore measures
"set-oracle vs per-user decoder", not "with C3 vs without C3". This is the same estimator-
mismatch class that produced the V0.23 C3 false readings.

**B3. The catalogue is the complete Cartesian product over all users, with no size guard.**
VERIFIED. `_catalogue` (`:200`) enumerates `itertools.product` over every user's legal
options; `_factor_scores` then runs `O(|U|²·|opts|²)` LC-SRS pairs and a 3-offset forecast per
unilateral config. At the declared 100-user provider this cannot terminate. Controller
stage-2 decision item 4 already CHANGES this for stage 4 — until it lands, `--unit` with the
real provider is unrunnable, and the sealed `no_catalogue_or_world_truncation: True` claim
(`:1046`) cannot be honoured.

**B4. A single user with no legal candidate silently collapses the whole catalogue to `{BASE}`.**
VERIFIED (code + Python semantics). `itertools.product` over an empty factor yields nothing, so
`rows` stays `[base]` (`:199-208`); all 12 arms then evaluate BASE, every marginal is exactly 0,
and nothing raises. Near-certain over 100 users × 30 steps, and indistinguishable from a real
"no effect" result.

## S2 — HIGH

**H1. Interference cross-gain is keyed by aggressor NORAD only — the aggressor's transmit
off-axis gain cannot depend on which beam radiates.** VERIFIED.
`PrimitiveCandidate.nominal_cross_gain_by_norad` (`tapes.py:118-120`) and
`geometry_for` (`tapes.py:329-334`, `nominal_map.get(aggressor.identity[0], 0.0)`) mean every
beam-chain of a satellite illuminates a given victim identically. The wanted signal uses a
per-(user, serving identity) `nominal_gain`; the interference uses a per-(victim, aggressor
NORAD) scalar. **Answering audit question 1 directly: the interference term does NOT use the
same radiation as the wanted signal at beam granularity.** Nothing in the engine ties the
cross-gain to `G^T(θ)·L·G^R` — in `TinySyntheticProvider` the two are independent formulas
(`tapes.py:496` vs `:516`), differing by ~5 dB, so no KAT ever checks their consistency.

**H2. `color` is a per-user attribute with no "colour is a function of beam identity"
invariant — and the bundled provider violates it.** VERIFIED. `_masked_coupling`
(`architectures.py:312`) masks on the victim's and aggressor's *candidate-row* colours. A
direct probe of `TinySyntheticProvider(users=3)` finds **3 physical beams carrying two
different colours depending on which user's row is read**. The rehearsal, dry-run and runner
KATs therefore ran under a user-dependent, non-reciprocal reuse-3 mask, and the same defect
from the real provider would pass unnoticed.

**H3. Five declared producers are on no execution path.** VERIFIED by grep:
`project_three_offsets`, `encode_c2_state`, `assert_reward_core_identity`,
`assert_calibration_world_separation` and `resolve_configuration` are called only from tests.
So (a) the sealed 21-value C2 state schema SHA `54ab6a82…` is stamped into every receipt
(`:1020`) although **no state row is ever produced**; (b) `_forecast_rows` (`:373`) bypasses
`project_three_offsets`' price gate and rate-field check; (c) the calibration/probe
world-separation assertion is dead code, so nothing checks that a CAL and a PROBE world do not
land on the same TLE-date × seed cluster; (d) the `R = B − η_ref E` telescoping identity is
asserted only on hand-built endpoints, never on a real trajectory.

**H4. Receipt `served_PHY` is "decoded for a nonzero measure of the step", not complete
service.** VERIFIED. `adapter.py:179-182` sets `served_phy = decoding_time_s > 0`; the strict
all-slot `complete_service` in `resolution.py:238-242` is never computed by the runner, so the
stage-2 QoS guard (decision item 6, "complete-service availability") has no producer — the merge
non-inferiority gate uses `decoding_availability` instead (`:1273`).

**H5. n = 4 clusters per cell makes the +0.5 pp lower bound near-degenerate; and
`ALL_NEUTRAL_CONTROL` is byte-identical to `NULL`.** VERIFIED. `_merged_uncertainty` builds one
cluster per probe world (4), so the 2.5 % quantile over resamples of 4 values is essentially the
minimum cluster — no meaningful 95 % coverage. `selections[ALL_NEUTRAL_CONTROL] = base` and
`selections["NULL"] = base` (`:749-751`), with `test_stage2_runner.py:292-294` asserting their
equality, so the sealed "FULL − ALL_NEUTRAL supporting comparison" is the same statistic as
`FULL − NULL`. (The bonus-free set selector does exist and is reported, as
`UNION_CATALOGUE_OPTIMUM`.)

## S3 — MODERATE

- **M1 (Φ has an undeclared price).** `C1.normalized_total = core/κ + Φ` (`targets.py:170`),
  and `_set_select` multiplies the bonus by κ (`:594`), so one satellite handover is priced at
  κ bits ≈ one user-second of reference throughput. No sealed document prices Φ. Units also
  mix: `core/κ` is user-seconds, Φ is a dimensionless event count.
- **M2 (κ magnitude).** `_calibrate` passes `time_s = DECISION_INTERVAL_S` per world (`:336`),
  summed over two worlds ⇒ `T_ref = 60.16 s`, so κ is *bits per user-second*. C2's declared
  "one −κ per lost offset" therefore charges 1/30.08 of a user-step's bits for losing an entire
  30.08 s offset.
- **M3 (e_i, and its separability).** The runner's e_i (`:513-530`) is
  `ΔF_network − Δbits_focal`; it still contains the focal user's own `−η·ΔE`, so it is not a
  clean externality, and under whole-network C1 it double-counts (exactly what stage-2 decision
  item 5 CHANGES). **Separability answer: YES, clean.** Ψ is computed independently at
  `targets.py:333` and e_i enters only the final sum at `:334`; the stage-4 change is (a) delete
  the inline dict at the call site and (b) drop `externality_e_by_user` from the signature/guard
  (`targets.py:314, 322`). Nothing else reads e_i. The ≥3-user equal-share (Shapley) split named
  in decision item 5 is not implemented — `c3_lcsrs_interaction` accepts pairs only.
- **M4 (inert re-key ledger).** `cell_rekey=False` is hardwired in `_phi_for` (`:370`) and
  `_arm_row` (`:670`) and `corrected_boundary_rekey_rate` is called with `rekeys=0` (`:858`), so
  the "explicit cell-rekey flag" the stage-2 report describes never fires.
- **M5 (two availability denominators).** `EvaluatedProfile.outcome()` divides by *assigned*
  users (`:153`); `_arm_row` divides by *all base* users (`:662`). They coincide only because the
  catalogue always assigns everyone — see B4.
- **M6 (catalogue digest is not a seal).** `catalogue_definition.sha256` digests only
  `{top:2, evacuation:"complete", version:1}` (`:1018`) — not the construction rule it freezes.
- **M7 (receipts attest constants the engine never applies).** `constant_manifest()` binds
  `ZENITH_GASEOUS_LOSS_DB`, `D2_THRESHOLD_KM/HYSTERESIS_KM/TTT_S`, `MINIMUM_ALTITUDE_KM`,
  `ASSOCIATION_ACTIONS`, `CACHED_SATELLITES`, `LOCAL_CELLS`, `REFERENCE_AGGREGATE_RF_W`,
  `HOBS_REFERENCE_MAX_RF_W`, `PERSISTENCE_LOSS_UNITS` — none referenced anywhere in
  `physics_v025` outside `constants_v025.py`. Gaseous absorption and D2 gating are entirely
  provider-owned.
- **M8 (`--dry-run` scope).** `main()` runs the dry-run for `a-r0` only (`:1381`); the stage-2
  report's "one-step smoke of every arm in all 31 settings" is not what the CLI does.

**S4 — LOW / NITS.** L1 `calibration.py:258` annotates `Sequence` without importing it (lazy under PEP 563; breaks
`typing.get_type_hints`). L2 `test_integration_matrix.py:181` labels `0.7174947934871672` as
Γ_r(1); the true value is `0.71749479356584789` (the literal is the raw QPSK 1/4 threshold,
1.1e-10 low) — the same quantity is written with a *different* literal in
`test_architectures.py:340`. L3 dead `zero_score = fallback.score` (`:396`). L4
`c2_persistence_forecast`'s docstring says only *later* offsets are absorbing losses, but the
failing offset is also charged κ (KAT asserts `lost_offsets == 3`). L5 `_energy_fields`
hardcodes `0.640` instead of `D2_MEASUREMENT_STEP_S`. L6 the S.465 −10 dBi floor takes over at
47.86° via `np.clip`, not the prescribed 48°. L7 `RadiationConfig()` is a reachable default for
W, cap, γ*, r* through `build_shared_tape` / `track_b_regeneration_adapter` (physics constants,
not prices, but unsealed at the call site).

## Question-by-question

**Q1 — physics faithfulness to `V025-ANGLE-RATE-TPC-TDM-ACM`: VERIFIED except H1.**
Re-derived numerically: `r* = 50e6` (`constants_v025.py:47`);
`Γ_r(n_b) = min{γ_m : W·SE_m/n_b ≥ r*}` implemented as `required_se = r*·n_b/W` then
`min(eligible, key=threshold_linear)` (`acm.py:95-101`) — correctly a **minimum over
thresholds**, not table position, which matters because the profile is non-monotone (8PSK 3/5
at 5.50 dB has lower SE than QPSK 9/10 at 6.42 dB). 28 modes; `SE = e/(1+α)`, α = 0.20;
`γ_m = EsN0 + 1.7 − 10log10(1.2)` (`acm.py:32-33`) ⇒ SE_max = 3.710855833 and
SINR_min = −1.441812460 dB, both matching the seal exactly. Measured Γ_r(n) = −1.44 / 0.61 /
3.14 / 4.94 / **7.528** / 8.82 / 9.88 / 11.12 / 12.52 / 13.64 / 15.19 dB for n = 1..11,
infeasible at n = 13 (SE 3.9 > 3.7109) — monotone, and n = 5 lands exactly on the old constant-γ
target. `p_u = min(1.65, Γ·(N₀W+Î)/ĥ)` is the capped standard-interference iteration
`updated = min(caps, targets·(noise + coupling@power)/direct)` from `power = 0`
(`architectures.py:345-348`), tol 1e-10 W, cap 4096, `INVALID` on non-convergence (`:364-372`),
plus a target-clearance certificate for rate cells. Equal-airtime TDM: boundaries are the union
`{k/n_b}` and user *k* of an *n*-user beam owns `[k/n,(k+1)/n]` (`:278-294`).
Served ⇔ SINR ≥ SINR_min after joint resolution (`acm.py:47-52`). **Units:** noise is `k·T_sys·W`
in watts, T_sys = 242.294 K, N₀W = 5.5754e-13 W; TDM uses the **full** 500/3 MHz
(`architectures.py:660`), FDM uses `W/n` per sub-band (`:749`) and scales interference by
`overlap_hz / aggressor_bandwidth` — a uniform-PSD aggressor's power in the victim's band
(`:737-744`), correct. dB↔linear conversions appear exactly once per quantity, and PA draw,
wanted signal and interference all use the same solved `power` vector. **Gap:** H1 —
interference radiation is per-satellite, not per-beam. The construction of `ĥ` and of the
cross-gains themselves is **UNKNOWN**: the provider is absent (VERIFY_SOURCE #1).

**Q2 — energy: VERIFIED. No double counting, no missing declared term.**
`pa_supply_power_w(p) = sqrt(p·p_sat)/0.35` with `p_sat = 1.65·10^0.5 = 5.2178 W`
(`energy.py:38`, `constants_v025.py:36`). `schedule_energy` calls `interval_energy` once per TDM
slot with `duration_s·fraction` (`energy.py:146-153`), so PA is the **airtime-weighted average of
PA(p)**, never `PA(max)` or `PA(Σp)` — pinned by two independent KATs:
`0.5·PA(0.825)+0.5·PA(1.65) = 7.155608836 ≠ PA(1.2375) = 7.260165679`
(`test_energy_endpoint.py:127-138`) and TDM `(PA(.2)+PA(.8))/2` vs FDM `PA(.5)`
(`test_architectures.py:318-319`). Circuit 0.338 W is charged per active chain per slot and,
since every beam is active in every slot, integrates to 0.338·T (`:116`); baseband 0.200 W once
per active satellite via a set (`:119`); `P_bus = 0` hard-enforced (`:100`); `P_idle = 0` primary
and `SENSITIVITY_IDLE_POWER_W = (1/12)·PA(1.65) = 0.698609768 W` (`:41-42`).
`EnergyReceipt.verify()` asserts the five components sum to `joules` at 1e-12, and
`StepEvaluator.evaluate` independently re-derives them and cross-checks against `score.joules`
(`:277-278`) — a genuine consistency gate. 47-sub-interval integration is enforced (48 samples on
the 0.640 s clock spanning 30.08 s, `integration.py:175-182`); treatment T is the **left**
endpoint (`snapshot_left`; `build_shared_tape` sets `snapshot = boundaries[0]`,
`adapter.py:115`; `_energy_fields` uses `boundary[0]`, `:226`) — matching decision item 3. Only
nuance: an active chain at tiny RF is floored at `max(idle, PA(p))`, booked to `pa_j`.

**Q3 — reward/target core: VERIFIED; e_i separable YES; DEFAULT_PRICE_PATHS = 0.**
`R = B − η_ref·E` (`endpoint.py:124`), telescoping proved exactly over `Fraction`
(`targets.py:352-356`). C1 = whole-network `(ΔB) − η(ΔE)` with Φ separate (`targets.py:168-170`);
C2 = three offsets with `−κ` per absorbing lost offset (`:275-294`); C3 =
`Ψ = F11 − F10 − F01 + F00` on `F = B − η_ref E` with `z₃,ᵢ = eᵢ + Ψ/2` (`:333-334`). **No
default λ/η/κ is reachable on any producer**: all seven take the prices keyword-only with
`Parameter.empty` defaults (signature test, `test_stage2_tapes_targets_state.py:205-221`) and
route through `assert_calibration_prices`, which fails closed on λ ≠ η or κ ≤ 0. Two *ungated*
(not defaulted) paths exist: `reward_core(endpoint, *, eta_ref)` takes η alone with no λ/κ
cross-check (`endpoint.py:112`), and `_forecast_rows` builds `OffsetProjection`s without
`project_three_offsets`' gate (H3b). See M1–M3 for Φ pricing, κ magnitude and e_i.

**Q4 — calibration: VERIFIED on formulas and seed rule; leak channel open (UNKNOWN).**
`nominal_greedy_reference` is lexicographic on (served ↓, bits ↓, energy ↑, id) with **no price**
(`calibration.py:50-57`) — no circularity; matches decision item 7. `η_ref = λ = B/E` and
`κ = B/(U·T)` are exact rationals (`endpoint.py:143-149`), re-validated in
`CalibrationValues.__post_init__` (`:120-125`). Exactly the two disjoint `V025_CAL/world/{1,2}`
domains are required at three sites (`:81`, `:124`, `:211-214`); one immutable value per setting
via `CalibrationRegistry` + a write-once 0444 manifest, and `--unit` refuses a calibration whose
`setting_sha256` differs (`:981`). The seed rule is exactly
`int.from_bytes(sha256(domain).digest()[:8],'big') & ((1<<63)-1)` (`tapes.py:47-49`), applied to
`V025_PROBE/world/{1..4}` and `V025_CAL/world/{1..2}` (`:36-37`), independently re-derived in
`test_stage2_tapes_targets_state.py:86-92`; the six seeds are distinct. **Leak: domain strings
cannot collide, but nothing checks that the provider maps a CAL seed and a PROBE seed to
different TLE dates / layouts** — the only guard that would notice,
`assert_calibration_world_separation`, is dead code (H3c), and `_merged_uncertainty` checks
cluster uniqueness only *within* a cell's four probe worlds (`:1258`). Required pre-launch seal.

**Q5 — matrix and receipts: VERIFIED except the dry-run scope and B1.**
`MATRIX_SETTINGS` is exactly the sealed order, 31 settings — `a-r0, a′-r0, a-γ0, b0, a′-γ0`,
then S, H, SH, T each in `a-r, a′-r, a-γ, b, a′-γ`, then U-cap and U-margin for `a-γ, b, a′-γ`
(`matrix.py:331-339`; confirmed by execution). Split-U is refused for rate architectures
(`:290-291`) and the undeclared T+standby corner is refused (`:286-289`). 12 arms as listed
(`:94-107`). `write_immutable` refuses any existing path, writes `open("xb")` + `fsync`, chmods
**0444** and emits a `X.sha256` sidecar (`:1216-1234`); `merge` re-verifies mode, sidecar,
embedded self-digest, cell/world identity, world-manifest commonality and calibration
non-drift across all 124 receipts (`:1305-1336`). The merge estimator is a **paired cluster
bootstrap recomputing ΣB/ΣE inside every draw** (`:898-903`), clusters = TLE date × training
seed (`:1251-1257`), gate `ee_lower > 0.5` (`:930`), with paired per-world log-EE explicitly
supplementary (`:939-944`). **No TEST split path exists**: `ExogenousWorldTape` hard-requires
`split == "TRAIN"` (`tapes.py:247`) and every receipt carries `test_split_opened: False`.
`--dry-run` does execute one real step of every one of the 12 arms — but for `a-r0` only (M8).
δ = 0.5 is a *relative* percent change (`100·(EE_full/EE_comp − 1)`) labelled "pp"; consistent
with prior project usage, worth stating once in the paper.

**Q6 — see next section. Q7 — see S1–S4.** Sign conventions, dB/linear handling, per-user vs
per-beam power, bandwidth split and time base all check out; the two genuine physics-modelling
problems are H1 and H2. Off-axis direction: the transmit pattern is even in θ (`sin θ` inside
`μ`, squared bracket) and the receive envelope takes `|θ| ≥ 0` behind a nonnegativity guard — no
sign hazard. Shannon and ACM are never mixed inside a cell: the U models are separate
`RateModel`s and are barred from the rate architectures.

## Q6 — test classification: 14 tautological / 102

**Tautological (compare code or Python to itself; 7 call no engine function at all).** In
`test_architectures.py`: `test_anchor_free_invariance_for_association_outage_and_dwell_histories`
(same call twice; the docstring concedes "there is deliberately no history argument"). In
`test_constants_acm.py`: `test_table_has_28_rows_and_frozen_hash` (re-hashes the same literal —
it does **not** check the transcription against EN 302 307-1),
`test_all_explicit_round3_verify_source_flags_are_live`,
`test_every_manifest_constant_has_value_and_provenance` (the manifest is *built from*
`PROVENANCE`). In `test_energy_endpoint.py`: `test_fixed_overhead_scales_absolute_ee_…`,
`test_common_floor_can_reverse_ranking`, `test_capacity_and_delivery_endpoints_remain_distinct`
(tests Python's `min`). In `test_contract_discriminators.py`:
`test_initialisation_and_common_prefix_are_horizon_independent`,
`test_c1_and_c2_arithmetic_fixtures_without_claiming_stage2_schema`,
`test_null_base_identity_is_structural_not_scalar_only` (contains `assert actions == actions`),
`test_all_false_mask_executes_no_op_and_dark_opportunity_is_retained` (re-implements the mapping
then asserts it), `test_tiny_positive_below_certified_error_is_not_a_pass`,
`test_deadline_fallback_is_frozen_base` (asserts a 30.08 s decision-deadline fallback the engine
does **not** implement — `decision_time_s` is only reported),
`test_legacy_r3_load_arithmetic_is_characterized_not_energy`.

**Genuinely independent known-answer tests (the strong core, 88):** mpmath J₁/J₃ at μ = 34;
S.465 re-derived from `32 − 25log10θ` clipped to [−10, 35] at 1 / 2.043298703 / 5°; FSPL `d^-2`;
`G_T(0)=2000` and half-power at 1.66°; Rician unit mean and `exp((σ ln10/10)²/2) = 1.269452`;
closed-form trapezoid oracles `∫(2+3t)`, `∫(5+0.25t)` over 48 boundaries; coupled fixed point
`p* = 5/9` from `p = 0.5+0.1p`; cap saturation and the iteration-cap `INVALID` certificate; TDM
union boundaries `{0,⅓,½,⅔,1}`; interference partition 2 / 3 / (4 excluded) and slot-consistent
1.65 / 3.30; FDM caps 0.825+0.825 = 1.65; PA/circuit/baseband anchors (268.353221940 J,
194.4942857 J, 0.876 / 1.076, 8.721 / 8.921, 7.155608836) and the PA-concavity test; exact
pooling 2 vs 50/9; λ/η parity and TypeError-on-omission; hand-computed C1 = −9 / φ = −½ / −19/2,
C2 = −16/3, Ψ = 5 with z₃ = {4.5, 1.5}; the seed-rule re-derivation; and the Γ_r known answers
(0.30 / 0.60 / 1.20 → QPSK 1/4, 2/5, 3/4; monotone; infeasible at n = 13).

**Physics quantities with NO independent oracle:** (1) the 28 EN 302 307-1 Table 13 rows
(self-hash only; the controller's manual comparison lives in a ledger, not a test; VERIFY_SOURCE
open); (2) the interference cross-gain **values** — `nominal/realised_cross_gain_by_norad` is
never tied to `G^T·L·G^R` by any test (H1); (3) the composed link budget `ĥ = G^T(θ)·L·G^R` —
the three factors are tested separately, never composed against a hand-computed dB budget, and
`Link.nominal_gain` is always injected; (4) geometry — off-axis angle θ, elevation, slant range,
and the D2 entry elevations 19.7 / 23.4 / 27.7° (provider-owned; VERIFY_SOURCE #4);
(5) `scintillation_loss_db` interpolation (only `shadow_sigma_db` is asserted); (6) gaseous
absorption (M7); (7) `keyed_fading_gain` composition (only "differs by elevation" and a std
ordering); (8) the Φ→bits rate and the κ magnitude (M1, M2); (9) the e_i externality definition
(the KAT passes arbitrary values); (10) the interruption→blackout mapping end to end
(unreachable at runner level, B1); (11) cluster-bootstrap coverage at n = 4 (H5); (12)
rate-target attainment under FDM.

**Confirmed-good (no action):** sealed-order matrix (31, exact order and digests); write-once
0444 receipts with sidecars and self-digests; `--unit` refusing a rebuilt tape whose digest
differs from the sealed manifest; `--calibrate`/`--manifest`/`--unit` all requiring an explicit
`--provider`; exact-rational endpoint arithmetic; the nominal/realised power split; no pruning
or repacking of failed attempts; the v1.3 erratum's 25 + 6 = 31 matching the code; and
`SCHEMA_SHA256 = 54ab6a82…`, `p_sat = 5.2178 W`, `SE_max = 3.710855833`,
`SINR_min = −1.441812460 dB` all reproducing the sealed values.

VERDICT: ENGINE_FAITHFUL=NO:{H_SH_treatment_is_a_no_op; FULL/DROP_arms_cannot_measure_C1/C2/C3_marginals; interference_radiation_is_per_satellite_not_per_beam; colour_not_bound_to_beam_identity} | DEFAULT_PRICE_PATHS=0 (2 ungated-but-explicit paths: `reward_core`, `_forecast_rows`) | TAUTOLOGICAL_TESTS=14/102 | BLOCKERS={B1 interruption never fired → 10 duplicate cells; B2 oracle-anchored `_set_select` makes C1 marginal identically zero and confounds C3; B3 Cartesian catalogue unrunnable at 100 users; B4 one option-less user silently collapses the catalogue to BASE}
